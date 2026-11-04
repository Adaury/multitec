import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Eye } from 'lucide-react'
import { api } from '../lib/api'
import type { Project, ProjectDetail, Quote, QuoteStatus } from '../lib/types'
import { QuoteViewer } from '../components/QuoteViewer'
import { QUOTE_STATUS_LABELS } from '../lib/types'
import { formatDOP } from '../lib/format'
import { Badge, Card, SegmentedTabs } from '../components/ui'
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

function QuotesList() {
  const [filter, setFilter] = useState<QuoteStatus | 'todas'>('todas')
  const [open, setOpen] = useState<Quote | null>(null)

  const { data: quotes, isLoading } = useQuery({
    queryKey: ['all-quotes', filter],
    queryFn: async () =>
      (
        await api.get<Quote[]>('/quotes', {
          params: filter === 'todas' ? undefined : { status_filter: filter },
        })
      ).data,
  })

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => (await api.get<Project[]>('/projects')).data,
  })

  function projectCode(projectId: number) {
    return projects?.find((p) => p.id === projectId)?.code ?? `#${projectId}`
  }

  return (
    <div className="space-y-4 md:space-y-6">
      <div className="flex gap-2 overflow-x-auto rounded-2xl bg-brand-gray p-1 md:max-w-fit dark:bg-gray-800">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`shrink-0 whitespace-nowrap rounded-xl px-4 py-2 text-sm font-medium ${
              filter === f.key
                ? 'bg-white text-brand-blue shadow-sm dark:bg-gray-700 dark:text-blue-300'
                : 'text-gray-500 dark:text-gray-400'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {quotes?.map((quote) => (
          <Card key={quote.id}>
            <Link to={`/proyectos/${quote.project_id}?tab=cotizacion`} className="block">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900 dark:text-gray-100">{quote.code}</p>
                  <p className="text-xs text-gray-400">Proyecto {projectCode(quote.project_id)}</p>
                </div>
                <Badge tone={STATUS_TONE[quote.status]}>{QUOTE_STATUS_LABELS[quote.status]}</Badge>
              </div>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{formatDOP(quote.total)}</p>
            </Link>
            <button
              type="button"
              onClick={() => setOpen(quote)}
              className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-brand-gray py-2 text-sm font-medium text-brand-blue hover:bg-gray-200 dark:bg-gray-800 dark:text-blue-300 dark:hover:bg-gray-700"
            >
              <Eye size={16} /> Ver y enviar
            </button>
          </Card>
        ))}
        {quotes?.length === 0 && <p className="text-sm text-gray-500">No hay cotizaciones en este filtro.</p>}
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
      onEdit={quote.status === 'pendiente' ? () => navigate(`/proyectos/${quote.project_id}?tab=cotizacion`) : undefined}
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
      <h1 className="text-xl font-semibold text-gray-900 md:text-3xl md:font-bold md:tracking-tight dark:text-gray-100">Cotizaciones</h1>
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
