import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  CalendarClock,
  ClipboardList,
  FileText,
  FolderOpen,
  FolderPlus,
  Hourglass,
  MapPin,
  Mic,
  PencilLine,
  Wrench,
  type LucideIcon,
} from 'lucide-react'
import { api } from '../lib/api'
import { assistantCallName } from '../lib/assistantName'
import { useAuthStore } from '../lib/authStore'
import { PROJECT_STATUS_LABELS, type TodaySummary } from '../lib/types'
import { AssistantTalk } from './AssistantTalk'
import { NavigateMenu } from './NavigateMenu'
import { AliasPrompt, greeting, plural, summarize } from './TodayAssistant'

type Action = { label: string; hint: string; icon: LucideIcon; to: string; staffOnly?: boolean }

const ACTIONS: Action[] = [
  { label: 'Dictar levantamiento', hint: 'Lo cuentas hablando', icon: Mic, to: '/nuevo?modo=voz' },
  { label: 'Escribir levantamiento', hint: 'Paso a paso', icon: PencilLine, to: '/nuevo' },
  { label: 'Nuevo proyecto', hint: 'Cliente y obra', icon: FolderPlus, to: '/proyectos?nuevo=1' },
  { label: 'Cotizaciones', hint: 'Ver y enviar', icon: FileText, to: '/cotizaciones', staffOnly: true },
  { label: 'Calendario', hint: 'Visitas de la semana', icon: CalendarClock, to: '/calendario' },
]

type Tone = 'blue' | 'amber' | 'green' | 'violet'
const TONES: Record<Tone, string> = {
  blue: 'bg-blue-50 text-brand-blue dark:bg-blue-950 dark:text-blue-300',
  amber: 'bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
  green: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
  violet: 'bg-violet-50 text-violet-700 dark:bg-violet-950 dark:text-violet-300',
}

/** Una línea de la agenda: solo el cliente y qué toca, sin montos ni códigos (el detalle está al entrar). */
function AgendaRow({
  to,
  icon: Icon,
  tone,
  client,
  tag,
  extra,
}: {
  to: string
  icon: LucideIcon
  tone: Tone
  client: string
  tag: string
  extra?: ReactNode
}) {
  return (
    <li className="flex items-center gap-3 rounded-2xl px-3 py-2.5 transition hover:bg-brand-gray dark:hover:bg-gray-800">
      <Link to={to} className="flex min-w-0 flex-1 items-center gap-3">
        <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${TONES[tone]}`}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
        <span className="min-w-0 flex-1 truncate text-base font-medium text-gray-900 dark:text-gray-100">{client}</span>
        <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${TONES[tone]}`}>{tag}</span>
      </Link>
      {extra}
    </li>
  )
}

function Panel({ title, count, children, empty }: { title: string; count: number; children: ReactNode; empty: string }) {
  return (
    <section className="flex min-w-0 flex-col rounded-3xl bg-white p-5 shadow-sm ring-1 ring-black/5 dark:bg-gray-900 dark:ring-white/10">
      <header className="mb-2 flex items-center justify-between px-1">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h2>
        {count > 0 && (
          <span className="rounded-full bg-brand-gray px-2.5 py-0.5 text-sm font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-300">
            {count}
          </span>
        )}
      </header>
      {count === 0 ? <p className="px-1 py-6 text-center text-sm text-gray-400">{empty}</p> : <ul className="space-y-1">{children}</ul>}
    </section>
  )
}

/** Inicio en la computadora: saludo grande y centrado, acciones rápidas en una fila y la agenda en dos columnas
 * (lo de hoy y lo que quedó a medias), con solo el nombre del cliente. El teléfono usa TodayAssistant. */
export function DesktopHome({ canSeeReports }: { canSeeReports: boolean }) {
  const user = useAuthStore((s) => s.user)
  const { data, isLoading, isError } = useQuery({
    queryKey: ['assistant', 'today'],
    queryFn: async () => (await api.get<TodaySummary>('/assistant/today')).data,
    staleTime: 60_000,
    refetchOnWindowFocus: true,
  })

  const name = assistantCallName(user)
  const summary = isLoading
    ? 'Revisando tu agenda…'
    : isError
      ? 'No pude revisar tu agenda ahora, pero podemos trabajar igual.'
      : data
        ? summarize(data)
        : ''
  // "Continuar" no repite proyectos que ya salen en "Para hoy".
  const pendingIds = new Set([
    ...(data?.ready_to_quote.map((p) => p.project_id) ?? []),
    ...(data?.visits.map((v) => v.project_id) ?? []),
    ...(data?.quotes_waiting.map((q) => q.project_id) ?? []),
    ...(data?.tickets.map((t) => t.project_id) ?? []),
  ])
  const toContinue = (data?.continue_projects ?? []).filter((p) => !pendingIds.has(p.project_id))
  const todayCount = data ? data.visits.length + data.ready_to_quote.length + data.quotes_waiting.length + data.tickets.length : 0
  const actions = ACTIONS.filter((a) => !a.staffOnly || canSeeReports)

  return (
    <div className="mx-auto w-full max-w-7xl space-y-8">
      {/* Saludo: centrado y grande, con la conversación con el asistente como acción principal. */}
      <section className="rounded-[2rem] bg-gradient-to-br from-brand-blue to-blue-800 px-8 py-10 text-center text-white shadow-lg">
        <p className="text-sm font-medium uppercase tracking-widest text-blue-100">
          {new Date().toLocaleDateString('es-DO', { weekday: 'long', day: 'numeric', month: 'long' })}
        </p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight">
          {greeting()}, {name}.
        </h1>
        <p className="mx-auto mt-3 max-w-2xl text-lg text-blue-50">{summary}</p>
        <div className="mx-auto mt-6 max-w-md text-left [&_button]:ring-2 [&_button]:ring-white/30">
          <AssistantTalk opening={`${greeting()}, ${name}. ${data ? summarize(data) : ''}`.trim()} />
        </div>
      </section>

      {user && !user.assistant_alias && (
        <div className="mx-auto max-w-xl">
          <AliasPrompt user={user} />
        </div>
      )}

      <section aria-labelledby="acciones-rapidas">
        <h2 id="acciones-rapidas" className="sr-only">
          Acciones rápidas
        </h2>
        <div className="grid grid-cols-[repeat(auto-fit,minmax(11rem,1fr))] gap-4">
          {actions.map((action) => (
            <Link
              key={action.label}
              to={action.to}
              className="group flex flex-col items-center gap-3 rounded-3xl bg-white px-4 py-6 text-center shadow-sm ring-1 ring-black/5 transition hover:-translate-y-0.5 hover:shadow-md hover:ring-brand-blue/30 dark:bg-gray-900 dark:ring-white/10"
            >
              <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50 text-brand-blue transition group-hover:bg-brand-blue group-hover:text-white dark:bg-blue-950 dark:text-blue-300">
                <action.icon className="h-7 w-7" strokeWidth={1.75} aria-hidden="true" />
              </span>
              <span>
                <span className="block text-base font-semibold text-gray-900 dark:text-gray-100">{action.label}</span>
                <span className="block text-sm text-gray-500 dark:text-gray-400">{action.hint}</span>
              </span>
            </Link>
          ))}
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Para hoy" count={todayCount} empty="Nada urgente para hoy.">
          {data?.visits.map((visit) => (
            <AgendaRow
              key={`v-${visit.id}`}
              to={`/proyectos/${visit.project_id}?tab=levantamiento`}
              icon={MapPin}
              tone="blue"
              client={visit.client_name}
              tag={visit.scheduled_time ? `Visita ${visit.scheduled_time.slice(0, 5)}` : 'Visita'}
              extra={
                (visit.address || visit.location_url) && (
                  <NavigateMenu
                    place={{ address: visit.address, location_url: visit.location_url }}
                    wrapperClassName="shrink-0"
                    className="rounded-full bg-brand-blue px-3 py-1.5 text-xs font-medium text-white"
                  >
                    Cómo llegar
                  </NavigateMenu>
                )
              }
            />
          ))}
          {data?.ready_to_quote.map((p) => (
            <AgendaRow
              key={`r-${p.project_id}`}
              to={`/proyectos/${p.project_id}?tab=levantamiento`}
              icon={ClipboardList}
              tone="violet"
              client={p.client_name}
              tag="Cotizar"
            />
          ))}
          {data?.quotes_waiting.map((q) => (
            <AgendaRow
              key={`q-${q.quote_id}`}
              to={`/proyectos/${q.project_id}?tab=cotizacion&cotizacion=${q.quote_id}`}
              icon={Hourglass}
              tone="amber"
              client={q.client_name}
              tag={q.days_pending === 0 ? 'Espera respuesta' : `Espera · ${plural(q.days_pending, 'día', 'días')}`}
            />
          ))}
          {data?.tickets.map((t) => (
            <AgendaRow
              key={`t-${t.id}`}
              to={`/proyectos/${t.project_id}?tab=tickets`}
              icon={Wrench}
              tone="green"
              client={t.client_name}
              tag="Ticket"
            />
          ))}
        </Panel>

        <Panel title="Continuar" count={toContinue.length} empty="No hay proyectos a medias.">
          {toContinue.map((p) => (
            <AgendaRow
              key={`c-${p.project_id}`}
              to={`/proyectos/${p.project_id}`}
              icon={FolderOpen}
              tone="blue"
              client={p.client_name}
              tag={p.status ? (PROJECT_STATUS_LABELS[p.status] ?? p.status) : 'Abrir'}
            />
          ))}
        </Panel>
      </div>
    </div>
  )
}
