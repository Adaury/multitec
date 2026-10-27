import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Bot, FileText, FolderOpen, Mic, PencilLine } from 'lucide-react'
import { api } from '../lib/api'
import { assistantCallName } from '../lib/assistantName'
import { useAuthStore } from '../lib/authStore'
import { formatDOP } from '../lib/format'
import { directionsUrl } from '../lib/maps'
import { NavigateMenu } from './NavigateMenu'
import { PROJECT_STATUS_LABELS, type CurrentUser, type TodaySummary } from '../lib/types'
import { AssistantTalk } from './AssistantTalk'
import { Card } from './ui'

function greeting(date = new Date()): string {
  const hour = date.getHours()
  if (hour < 12) return 'Buenos días'
  if (hour < 19) return 'Buenas tardes'
  return 'Buenas noches'
}

function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`
}

/** Frase que resume el día: solo lo que hay, sin rellenar con ceros. */
function summarize(data: TodaySummary): string {
  const parts: string[] = []
  if (data.visits.length) parts.push(plural(data.visits.length, 'visita', 'visitas'))
  if (data.ready_to_quote.length)
    parts.push(
      plural(data.ready_to_quote.length, 'levantamiento listo para cotizar', 'levantamientos listos para cotizar'),
    )
  if (data.quotes_waiting.length)
    parts.push(plural(data.quotes_waiting.length, 'cotización esperando respuesta', 'cotizaciones esperando respuesta'))
  if (data.tickets.length) parts.push(plural(data.tickets.length, 'ticket abierto', 'tickets abiertos'))
  if (parts.length === 0) return 'Hoy no tienes visitas ni pendientes urgentes.'
  const last = parts.pop()!
  return `Hoy tienes ${parts.length ? `${parts.join(', ')} y ${last}` : last}.`
}

const ROW_CLASS =
  'flex items-center gap-3 rounded-2xl bg-white px-4 py-3 text-left shadow-sm ring-1 ring-black/5 active:scale-[0.99] dark:bg-gray-900 dark:ring-white/10'
const ROW_TITLE = 'block truncate text-sm font-semibold text-gray-900 dark:text-gray-100'
const ROW_SUB = 'block truncate text-xs text-gray-500 dark:text-gray-400'

/** Primera vez: el asistente pregunta cómo llamar al usuario, ahí mismo, sin mandarlo al perfil. */
function AliasPrompt({ user }: { user: CurrentUser }) {
  const setUser = useAuthStore((s) => s.setUser)
  const [alias, setAlias] = useState('')
  const [dismissed, setDismissed] = useState(false)
  const save = useMutation({
    mutationFn: async () =>
      (await api.put<CurrentUser>('/auth/me', { name: user.name, assistant_alias: alias.trim() })).data,
    onSuccess: (data) => setUser(data),
  })
  if (dismissed) return null
  return (
    <form
      className="space-y-2 rounded-2xl bg-white p-3 ring-1 ring-black/5 dark:bg-gray-900 dark:ring-white/10"
      onSubmit={(e) => {
        e.preventDefault()
        if (alias.trim()) save.mutate()
      }}
    >
      <label htmlFor="assistant-alias" className="block text-sm font-medium text-gray-900 dark:text-gray-100">
        ¿Cómo quieres que te llame?
      </label>
      <div className="flex gap-2">
        <input
          id="assistant-alias"
          value={alias}
          maxLength={40}
          onChange={(e) => setAlias(e.target.value)}
          placeholder="Ej.: Ing. Pérez"
          className="min-w-0 flex-1 rounded-xl border border-gray-200 bg-white px-3 py-2 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
        />
        <button
          type="submit"
          disabled={!alias.trim() || save.isPending}
          className="shrink-0 rounded-xl bg-brand-blue px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {save.isPending ? '…' : 'Guardar'}
        </button>
      </div>
      <button type="button" className="text-xs text-gray-500 underline dark:text-gray-400" onClick={() => setDismissed(true)}>
        Ahora no
      </button>
      {save.isError && <p className="text-xs text-red-600 dark:text-red-400">No se pudo guardar. Intenta de nuevo.</p>}
    </form>
  )
}

/** El asistente del Inicio: saluda al usuario por su nombre, le dice qué hay para hoy y le pregunta
 * cómo quiere trabajar (dictar, escribir o continuar un proyecto). No usa el modelo de IA a
 * propósito: tiene que aparecer al instante y funcionar aunque Ollama no esté cargado. Si el
 * servidor no responde, el saludo y las formas de trabajar siguen ahí. */
export function TodayAssistant() {
  const user = useAuthStore((s) => s.user)
  const { data, isLoading, isError } = useQuery({
    queryKey: ['assistant', 'today'],
    queryFn: async () => (await api.get<TodaySummary>('/assistant/today')).data,
    // Una agenda del día no cambia cada segundo, pero conviene refrescarla al volver a la app.
    staleTime: 60_000,
    refetchOnWindowFocus: true,
  })

  const hasPending =
    !!data &&
    data.visits.length + data.ready_to_quote.length + data.quotes_waiting.length + data.tickets.length > 0
  // "Continuar" no repite lo que ya aparece arriba como pendiente de cotizar.
  const pendingIds = new Set(data?.ready_to_quote.map((p) => p.project_id) ?? [])
  const toContinue = (data?.continue_projects ?? []).filter((p) => !pendingIds.has(p.project_id))

  return (
    <Card className="space-y-4 bg-blue-50 ring-blue-100 dark:bg-blue-950 dark:ring-blue-900">
      <div>
        <p className="text-xl font-semibold text-gray-900 dark:text-gray-100">
          <Bot className="mr-1.5 inline h-6 w-6 -translate-y-0.5 text-brand-blue" aria-hidden="true" />
          {greeting()}, {assistantCallName(user)}.
        </p>
        <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">
          {isLoading && 'Revisando tu agenda…'}
          {isError && 'No pude revisar tu agenda ahora, pero podemos trabajar igual.'}
          {data && summarize(data)}
        </p>
      </div>

      {user && !user.assistant_alias && <AliasPrompt user={user} />}

      <div className="space-y-2">
        <p className="text-base font-semibold text-gray-900 dark:text-gray-100">¿Cómo quieres trabajar hoy?</p>
        {/* La conversación: el asistente saluda en voz alta, pregunta qué toca y escucha. */}
        <AssistantTalk
          opening={`${greeting()}, ${assistantCallName(user)}. ${data ? summarize(data) : ''}`.trim()}
        />
        <Link to="/nuevo?modo=voz" className={ROW_CLASS}>
          <Mic className="h-7 w-7 shrink-0 text-brand-blue" aria-hidden="true" />
          <span className="min-w-0">
            <span className={ROW_TITLE}>Dictar un levantamiento</span>
            <span className={ROW_SUB}>Me lo cuentas hablando y yo armo la cotización</span>
          </span>
        </Link>
        <Link to="/nuevo" className={ROW_CLASS}>
          <PencilLine className="h-7 w-7 shrink-0 text-brand-blue" aria-hidden="true" />
          <span className="min-w-0">
            <span className={ROW_TITLE}>Escribirlo paso a paso</span>
            <span className={ROW_SUB}>Busco o creo el cliente y te voy preguntando</span>
          </span>
        </Link>
      </div>

      {data && hasPending && (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Para hoy</p>
          {data.visits.map((visit) => {
            const route = directionsUrl({ address: visit.address, location_url: visit.location_url })
            return (
              <div key={`v-${visit.id}`} className={ROW_CLASS}>
                <Link to={`/proyectos/${visit.project_id}?tab=levantamiento`} className="flex min-w-0 flex-1 items-center gap-3">
                  <span className="text-2xl">📍</span>
                  <span className="min-w-0">
                    <span className={ROW_TITLE}>
                      {visit.scheduled_time ? `${visit.scheduled_time.slice(0, 5)} · ` : ''}
                      {visit.client_name}
                    </span>
                    <span className={ROW_SUB}>Visita de hoy{visit.address ? ` · ${visit.address}` : ''}</span>
                  </span>
                </Link>
                {route && (
                  <NavigateMenu
                    place={{ address: visit.address, location_url: visit.location_url }}
                    wrapperClassName="shrink-0"
                    className="rounded-full bg-brand-blue px-3 py-1.5 text-xs font-medium text-white"
                  >
                    Cómo llegar
                  </NavigateMenu>
                )}
              </div>
            )
          })}

          {data.ready_to_quote.slice(0, 3).map((project) => (
            <Link key={`r-${project.project_id}`} to={`/proyectos/${project.project_id}?tab=levantamiento`} className={ROW_CLASS}>
              <FileText className="h-7 w-7 shrink-0 text-brand-blue" aria-hidden="true" />
              <span className="min-w-0">
                <span className={ROW_TITLE}>Cotizar: {project.client_name}</span>
                <span className={ROW_SUB}>
                  {project.project_code}
                  {project.survey_type ? ` · ${project.survey_type}` : ''} · el levantamiento ya está listo
                </span>
              </span>
            </Link>
          ))}

          {data.quotes_waiting.slice(0, 3).map((quote) => (
            <Link key={`q-${quote.quote_id}`} to={`/proyectos/${quote.project_id}?tab=cotizacion`} className={ROW_CLASS}>
              <span className="text-2xl">⏳</span>
              <span className="min-w-0">
                <span className={ROW_TITLE}>
                  {quote.client_name} · {formatDOP(quote.total)}
                </span>
                <span className={ROW_SUB}>
                  {quote.code} espera respuesta{' '}
                  {quote.days_pending === 0 ? 'desde hoy' : `hace ${plural(quote.days_pending, 'día', 'días')}`}
                </span>
              </span>
            </Link>
          ))}

          {data.tickets.slice(0, 3).map((ticket) => (
            <Link key={`t-${ticket.id}`} to={`/proyectos/${ticket.project_id}?tab=tickets`} className={ROW_CLASS}>
              <span className="text-2xl">🛠</span>
              <span className="min-w-0">
                <span className={ROW_TITLE}>{ticket.client_name}</span>
                <span className={ROW_SUB}>
                  {ticket.code} · {ticket.problem}
                </span>
              </span>
            </Link>
          ))}
        </div>
      )}

      {toContinue.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Continuar</p>
          {toContinue.map((project) => (
            <Link key={`c-${project.project_id}`} to={`/proyectos/${project.project_id}`} className={ROW_CLASS}>
              <FolderOpen className="h-7 w-7 shrink-0 text-brand-blue" aria-hidden="true" />
              <span className="min-w-0">
                <span className={ROW_TITLE}>Continuar: {project.client_name}</span>
                <span className={ROW_SUB}>
                  {project.project_code}
                  {project.status ? ` · ${PROJECT_STATUS_LABELS[project.status] ?? project.status}` : ''}
                </span>
              </span>
            </Link>
          ))}
        </div>
      )}
    </Card>
  )
}
