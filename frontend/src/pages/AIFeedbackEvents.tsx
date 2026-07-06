import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { AIFeedbackEvent, AIFeedbackOrigin, Product, Project } from '../lib/types'
import { useAuthStore } from '../lib/authStore'
import { Badge, Card, Field } from '../components/ui'

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

export function AIFeedbackEvents() {
  const currentUser = useAuthStore((s) => s.user)
  const isAdmin = currentUser?.role === 'admin'
  const [projectId, setProjectId] = useState('')

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
        todavía. Es información cruda: nada la analiza ni propone reglas automáticamente
        todavía, eso espera a tener volumen suficiente de proyectos.
      </p>

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
