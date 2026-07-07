import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import type {
  AccessoryCandidate,
  AIFeedbackEvent,
  AIFeedbackOrigin,
  LearningAnalysisOut,
  Product,
  Project,
  StaleRuleCandidate,
} from '../lib/types'
import { useAuthStore } from '../lib/authStore'
import { Badge, Button, Card, Field, Input } from '../components/ui'

const ORIGIN_LABELS: Record<AIFeedbackOrigin, string> = {
  ai_suggested: 'Sugerido por IA',
  human_added: 'Agregado',
  human_removed: 'Quitado',
  human_modified: 'Modificado',
}

const ORIGIN_TONES: Record<AIFeedbackOrigin, 'green' | 'red' | 'amber' | 'gray'> = {
  ai_suggested: 'gray',
  human_added: 'green',
  human_removed: 'red',
  human_modified: 'amber',
}

function describeEvent(event: AIFeedbackEvent, productName: string | null): string {
  if (event.entity_type === 'engineering') {
    const field = event.field_changed ?? 'un campo'
    return `Ingeniería, "${field}": "${event.old_value ?? '-'}" → "${event.new_value ?? '-'}"`
  }
  const product = productName ?? (event.product_id ? `producto #${event.product_id}` : 'mano de obra / servicio')
  if (event.origin === 'human_added') return `Se agregó ${product} — cantidad ${event.new_value}`
  if (event.origin === 'human_removed') return `Se quitó ${product} — tenía cantidad ${event.old_value}`
  return `Se cambió la cantidad de ${product}: ${event.old_value} → ${event.new_value}`
}

function AccessoryCandidateCard({ candidate, onHandled }: { candidate: AccessoryCandidate; onHandled: () => void }) {
  const [targetTag, setTargetTag] = useState(candidate.suggested_target_tag ?? '')
  const [quantity, setQuantity] = useState(String(Math.round(candidate.example_quantity)))
  const [error, setError] = useState<string | null>(null)

  const createRule = useMutation({
    mutationFn: async () =>
      (
        await api.post(`/catalog/${candidate.source_product_id}/technical-rules`, {
          action_type: 'add_accessory',
          target_tag: targetTag,
          per_source_units: null,
          quantity: Number(quantity),
        })
      ).data,
    onSuccess: onHandled,
    onError: (err: any) => setError(err?.response?.data?.detail ?? 'No se pudo crear la regla'),
  })

  return (
    <Card className="space-y-2">
      <p className="text-sm text-gray-700 dark:text-gray-300">
        Cuando se usa <strong>{candidate.source_product_name}</strong>, se agregó a mano{' '}
        <strong>{candidate.added_product_name}</strong> en {candidate.project_count} de{' '}
        {candidate.total_projects_with_source} proyectos ({Math.round(candidate.ratio * 100)}%).
      </p>
      {candidate.example_project_codes.length > 0 && (
        <p className="text-xs text-gray-400">Ejemplos: {candidate.example_project_codes.join(', ')}</p>
      )}
      <form
        className="space-y-2"
        onSubmit={(e) => {
          e.preventDefault()
          createRule.mutate()
        }}
      >
        <div className="grid gap-2 sm:grid-cols-2">
          <Field label="Etiqueta del accesorio">
            <Input required value={targetTag} onChange={(e) => setTargetTag(e.target.value)} />
          </Field>
          <Field label="Cantidad fija">
            <Input type="number" min="1" step="1" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
          </Field>
        </div>
        <Button type="submit" disabled={createRule.isPending || !targetTag}>
          {createRule.isPending ? 'Creando…' : '+ Crear regla'}
        </Button>
      </form>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </Card>
  )
}

function StaleRuleCandidateCard({ candidate, onHandled }: { candidate: StaleRuleCandidate; onHandled: () => void }) {
  const [error, setError] = useState<string | null>(null)

  const deleteRule = useMutation({
    mutationFn: async () => (await api.delete(`/catalog/technical-rules/${candidate.rule_id}`)).data,
    onSuccess: onHandled,
    onError: (err: any) => setError(err?.response?.data?.detail ?? 'No se pudo eliminar la regla'),
  })

  return (
    <Card className="space-y-2">
      <p className="text-sm text-gray-700 dark:text-gray-300">
        La regla de <strong>{candidate.source_product_name}</strong> agrega{' '}
        <strong>{candidate.would_add_product_name ?? `tag "${candidate.target_tag}"`}</strong>, pero se quitó a mano
        en {candidate.removed_count} de {candidate.total_projects_with_source} proyectos (
        {Math.round(candidate.ratio * 100)}%).
      </p>
      {candidate.example_project_codes.length > 0 && (
        <p className="text-xs text-gray-400">Ejemplos: {candidate.example_project_codes.join(', ')}</p>
      )}
      <Button variant="secondary" onClick={() => deleteRule.mutate()} disabled={deleteRule.isPending}>
        {deleteRule.isPending ? 'Eliminando…' : 'Eliminar regla'}
      </Button>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </Card>
  )
}

export function AIFeedbackEvents() {
  const currentUser = useAuthStore((s) => s.user)
  const isAdmin = currentUser?.role === 'admin'
  const [projectId, setProjectId] = useState('')
  const [handledAccessoryKeys, setHandledAccessoryKeys] = useState<Set<string>>(new Set())
  const [handledRuleIds, setHandledRuleIds] = useState<Set<number>>(new Set())

  const analyze = useMutation({
    mutationFn: async () => (await api.post<LearningAnalysisOut>('/ai-feedback-events/analyze')).data,
    onSuccess: () => {
      setHandledAccessoryKeys(new Set())
      setHandledRuleIds(new Set())
    },
  })

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => (await api.get<Project[]>('/projects')).data,
    enabled: isAdmin,
  })

  // Mismo queryKey que usa el catálogo — reutiliza esa caché para mostrar el nombre del
  // producto en vez de solo su id.
  const { data: products } = useQuery({
    queryKey: ['catalog'],
    queryFn: async () => (await api.get<Product[]>('/catalog')).data,
    enabled: isAdmin,
  })
  const productNameById = new Map(products?.map((p) => [p.id, p.name]))
  const projectCodeById = new Map(projects?.map((p) => [p.id, p.code]))

  const { data: events, isLoading } = useQuery({
    queryKey: ['ai-feedback-events', projectId],
    queryFn: async () =>
      (
        await api.get<AIFeedbackEvent[]>('/ai-feedback-events', {
          params: projectId ? { project_id: projectId } : undefined,
        })
      ).data,
    enabled: isAdmin,
  })

  if (!isAdmin) {
    return (
      <div className="py-4">
        <Card>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Solo un administrador puede ver las correcciones registradas.
          </p>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-4 py-4 md:space-y-6 md:py-8">
      <h1 className="text-xl font-semibold text-gray-900 md:text-2xl dark:text-gray-100">Aprendizaje IA</h1>
      <p className="text-sm text-gray-500 dark:text-gray-400">
        Registro de qué corrigió un humano sobre un presupuesto o una ingeniería que generó
        la IA (Motor 7) — solo mientras seguían siendo la sugerencia original, sin editar
        todavía.
      </p>

      <Card className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <p className="font-medium text-gray-900 dark:text-gray-100">Análisis de patrones</p>
          <Button className="!w-auto shrink-0 px-4" onClick={() => analyze.mutate()} disabled={analyze.isPending}>
            {analyze.isPending ? 'Analizando…' : 'Analizar ahora'}
          </Button>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Busca accesorios agregados a mano de forma consistente (candidatos a regla nueva) y reglas existentes
          cuyo accesorio se quita a mano de forma consistente (candidatas a revisar). No crea ni borra nada por
          su cuenta — cada resultado enlaza a la acción que ya existe.
        </p>

        {analyze.isError && (
          <p className="text-sm text-red-600 dark:text-red-400">No se pudo completar el análisis.</p>
        )}

        {analyze.data && (
          <div className="space-y-4 border-t border-gray-100 pt-3 dark:border-gray-800">
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Accesorios candidatos a regla nueva
              </p>
              {analyze.data.accessory_candidates.filter(
                (c) => !handledAccessoryKeys.has(`${c.source_product_id}-${c.added_product_id}`),
              ).length === 0 && <p className="text-xs text-gray-400">Ningún candidato por ahora.</p>}
              {analyze.data.accessory_candidates
                .filter((c) => !handledAccessoryKeys.has(`${c.source_product_id}-${c.added_product_id}`))
                .map((c) => (
                  <AccessoryCandidateCard
                    key={`${c.source_product_id}-${c.added_product_id}`}
                    candidate={c}
                    onHandled={() =>
                      setHandledAccessoryKeys(
                        (prev) => new Set(prev).add(`${c.source_product_id}-${c.added_product_id}`),
                      )
                    }
                  />
                ))}
            </div>

            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Reglas a revisar</p>
              {analyze.data.stale_rule_candidates.filter((c) => !handledRuleIds.has(c.rule_id)).length === 0 && (
                <p className="text-xs text-gray-400">Ninguna regla señalada por ahora.</p>
              )}
              {analyze.data.stale_rule_candidates
                .filter((c) => !handledRuleIds.has(c.rule_id))
                .map((c) => (
                  <StaleRuleCandidateCard
                    key={c.rule_id}
                    candidate={c}
                    onHandled={() => setHandledRuleIds((prev) => new Set(prev).add(c.rule_id))}
                  />
                ))}
            </div>
          </div>
        )}
      </Card>

      <Card className="max-w-sm">
        <Field label="Filtrar por proyecto">
          <select
            className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
          >
            <option value="">Todos los proyectos</option>
            {projects?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.code}
              </option>
            ))}
          </select>
        </Field>
      </Card>

      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}
      {events && events.length === 0 && (
        <p className="text-sm text-gray-500 dark:text-gray-400">Aún no hay correcciones registradas.</p>
      )}

      <div className="space-y-2">
        {events?.map((event) => (
          <Card key={event.id} className="space-y-1">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Badge tone={ORIGIN_TONES[event.origin]}>{ORIGIN_LABELS[event.origin]}</Badge>
                <span className="text-xs text-gray-400">
                  {projectCodeById.get(event.project_id) ?? `Proyecto #${event.project_id}`}
                </span>
              </div>
              <span className="text-xs text-gray-400">{new Date(event.created_at).toLocaleString('es-DO')}</span>
            </div>
            <p className="text-sm text-gray-700 dark:text-gray-300">
              {describeEvent(event, event.product_id ? (productNameById.get(event.product_id) ?? null) : null)}
            </p>
          </Card>
        ))}
      </div>
    </div>
  )
}
