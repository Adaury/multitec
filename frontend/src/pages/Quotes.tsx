import { useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Archive, CircleCheck, CircleX, Eye, FileText, Hourglass, type LucideIcon } from 'lucide-react'
import { api } from '../lib/api'
import type { Client, Project, ProjectDetail, Quote, QuoteStatus } from '../lib/types'
import { QuoteViewer } from '../components/QuoteViewer'
import { QUOTE_STATUS_LABELS } from '../lib/types'
import { formatDOP } from '../lib/format'
import { Badge, SegmentedTabs } from '../components/ui'
import { EmptyState, FilterChips, SearchBox, StatTile, normalize } from '../components/ListTools'
import { Budgets } from './Budgets'

const STATUS_TONE: Record<string, 'blue' | 'green' | 'red' | 'gray'> = {
  pendiente: 'blue',
  aprobada: 'green',
  no_aprobada: 'red',
  archivada: 'gray',
}

const FILTERS: { key: QuoteStatus | 'todas'; label: string }[] = [
  { key: 'todas', label: 'Todas' },
  { key: 'pendiente', label: 'Pendientes' },
  { key: 'aprobada', label: 'Aprobadas' },
  { key: 'no_aprobada', label: 'No aprobadas' },
  { key: 'archivada', label: 'Archivadas' },
]

const STATUS_ICON: Record<QuoteStatus, { icon: LucideIcon; tone: string }> = {
  pendiente: { icon: Hourglass, tone: 'bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300' },
  aprobada: { icon: CircleCheck, tone: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300' },
  no_aprobada: { icon: CircleX, tone: 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300' },
  archivada: { icon: Archive, tone: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400' },
}

function QuotesList() {
  const [filter, setFilter] = useState<QuoteStatus | 'todas'>('todas')
  const [search, setSearch] = useState('')
  const [open, setOpen] = useState<Quote | null>(null)

  // Todas de una vez: los filtros cuentan cuántas hay de cada estado sin otra consulta.
  const { data: quotes, isLoading } = useQuery({
    queryKey: ['all-quotes'],
    queryFn: async () => (await api.get<Quote[]>('/quotes')).data,
  })
  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => (await api.get<Project[]>('/projects')).data,
  })
  const { data: clients } = useQuery({
    queryKey: ['clients'],
    queryFn: async () => (await api.get<Client[]>('/clients')).data,
  })
  const projectById = useMemo(() => new Map((projects ?? []).map((p) => [p.id, p])), [projects])
  const clientNames = useMemo(() => new Map((clients ?? []).map((c) => [c.id, c.name])), [clients])
  const clientOf = (quote: Quote) => {
    const project = projectById.get(quote.project_id)
    return project ? clientNames.get(project.client_id) : undefined
  }

  const all = quotes ?? []
  const count = (status: QuoteStatus) => all.filter((q) => q.status === status).length
  const sum = (status: QuoteStatus) => all.filter((q) => q.status === status).reduce((total, q) => total + q.total, 0)
  const query = normalize(search.trim())
  const visible = all.filter(
    (q) =>
      (filter === 'todas' || q.status === filter) &&
      (!query || [q.code, clientOf(q), projectById.get(q.project_id)?.code].some((f) => normalize(f).includes(query))),
  )

  return (
    <div className="space-y-4 md:space-y-6">
      {all.length > 0 && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4">
          <StatTile
            icon={Hourglass}
            label={`Pendientes · ${formatDOP(sum('pendiente'))}`}
            value={count('pendiente')}
            tone={STATUS_ICON.pendiente.tone}
          />
          <StatTile
            icon={CircleCheck}
            label={`Aprobadas · ${formatDOP(sum('aprobada'))}`}
            value={count('aprobada')}
            tone={STATUS_ICON.aprobada.tone}
          />
          <StatTile icon={CircleX} label="No aprobadas" value={count('no_aprobada')} tone={STATUS_ICON.no_aprobada.tone} />
          <StatTile icon={Archive} label="Archivadas" value={count('archivada')} tone={STATUS_ICON.archivada.tone} />
        </div>
      )}

      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <FilterChips<QuoteStatus | 'todas'>
          value={filter}
          onChange={setFilter}
          label="Filtrar por estado"
          options={FILTERS.map((f) => ({ ...f, count: f.key === 'todas' ? all.length : count(f.key) }))}
        />
        <SearchBox value={search} onChange={setSearch} placeholder="Buscar por cliente o código…" label="Buscar cotización" />
      </div>

      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 md:gap-4 xl:grid-cols-3">
        {visible.map((quote) => {
          const style = STATUS_ICON[quote.status]
          const Icon = style.icon
          return (
            <div
              key={quote.id}
              className="flex flex-col rounded-3xl bg-white p-5 shadow-sm ring-1 ring-black/5 transition hover:shadow-md dark:bg-gray-900 dark:ring-white/10"
            >
              <Link to={`/proyectos/${quote.project_id}?tab=cotizacion&cotizacion=${quote.id}`} className="group block flex-1">
                <div className="flex items-start gap-3">
                  <span className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl ${style.tone}`}>
                    <Icon className="h-6 w-6" aria-hidden="true" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-base font-semibold text-gray-900 group-hover:text-brand-blue dark:text-gray-100">
                      {clientOf(quote) ?? quote.code}
                    </p>
                    <p className="text-xs text-gray-400">
                      {quote.code} · Proyecto {projectById.get(quote.project_id)?.code ?? `#${quote.project_id}`}
                    </p>
                  </div>
                  <Badge tone={STATUS_TONE[quote.status]}>{QUOTE_STATUS_LABELS[quote.status]}</Badge>
                </div>
                <div className="mt-4 flex items-end justify-between gap-2">
                  <p className="text-2xl font-bold tracking-tight text-gray-900 dark:text-gray-100">{formatDOP(quote.total)}</p>
                  <p className="shrink-0 text-xs text-gray-400">
                    {quote.items.length} {quote.items.length === 1 ? 'partida' : 'partidas'} ·{' '}
                    {new Date(quote.created_at).toLocaleDateString('es-DO', { day: 'numeric', month: 'short' })}
                  </p>
                </div>
              </Link>
              <button
                type="button"
                onClick={() => setOpen(quote)}
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-brand-gray py-2.5 text-sm font-medium text-brand-blue hover:bg-gray-200 dark:bg-gray-800 dark:text-blue-300 dark:hover:bg-gray-700"
              >
                <Eye size={16} /> Ver y enviar
              </button>
            </div>
          )
        })}
        {all.length === 0 && !isLoading && <EmptyState icon={FileText}>Aún no hay cotizaciones.</EmptyState>}
        {all.length > 0 && visible.length === 0 && <EmptyState icon={FileText}>No hay cotizaciones en este filtro.</EmptyState>}
      </div>
      {open && <ViewerForQuote quote={open} onClose={() => setOpen(null)} />}
    </div>
  )
}

/** El listado no trae al cliente: se pide el proyecto al abrir el visor. Editar lleva a la cotización en su proyecto. */
function ViewerForQuote({ quote, onClose }: { quote: Quote; onClose: () => void }) {
  const navigate = useNavigate()
  const { data: project, isError } = useQuery({
    queryKey: ['project', quote.project_id],
    queryFn: async () => (await api.get<ProjectDetail>(`/projects/${quote.project_id}`)).data,
  })
  if (isError) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
        <p className="rounded-2xl bg-white p-4 text-sm text-red-600 dark:bg-gray-900">No se pudo abrir la cotización.</p>
      </div>
    )
  }
  if (!project) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/95">
        <p className="text-sm text-gray-300">Abriendo…</p>
      </div>
    )
  }
  return (
    <QuoteViewer
      quote={quote}
      client={project.client}
      projectId={project.id}
      publicToken={project.public_token}
      onClose={onClose}
      onEdit={() => navigate(`/proyectos/${quote.project_id}?tab=cotizacion&cotizacion=${quote.id}&editar=1`)}
    />
  )
}

type View = 'cotizaciones' | 'presupuestos'

/** Una sola entrada de menú para el dinero que se le propone al cliente: cotizaciones y,
 * en la otra vista, los presupuestos internos de los que salen. */
export function Quotes() {
  const [params, setParams] = useSearchParams()
  const view: View = params.get('vista') === 'presupuestos' ? 'presupuestos' : 'cotizaciones'

  return (
    <div className="space-y-4 py-4 md:space-y-6 md:py-8">
      <h1 className="text-xl font-semibold text-gray-900 md:sr-only dark:text-gray-100">Cotizaciones</h1>
      <SegmentedTabs<View>
        value={view}
        onChange={(next) => setParams(next === 'cotizaciones' ? {} : { vista: next }, { replace: true })}
        options={[
          { key: 'cotizaciones', label: 'Cotizaciones' },
          { key: 'presupuestos', label: 'Presupuestos' },
        ]}
      />
      {view === 'cotizaciones' ? <QuotesList /> : <Budgets embedded />}
    </div>
  )
}
