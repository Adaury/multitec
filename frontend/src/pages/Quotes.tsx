import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import type { Project, Quote, QuoteStatus } from '../lib/types'
import { QUOTE_STATUS_LABELS } from '../lib/types'
import { formatDOP } from '../lib/format'
import { Badge, Card } from '../components/ui'

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

export function Quotes() {
  const [filter, setFilter] = useState<QuoteStatus | 'todas'>('todas')

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
    <div className="space-y-4 py-4">
      <h1 className="text-xl font-semibold text-gray-900">Cotizaciones</h1>

      <div className="flex gap-2 overflow-x-auto rounded-2xl bg-brand-gray p-1">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`shrink-0 whitespace-nowrap rounded-xl px-4 py-2 text-sm font-medium ${
              filter === f.key ? 'bg-white text-brand-blue shadow-sm' : 'text-gray-500'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}

      <div className="space-y-3">
        {quotes?.map((quote) => (
          <Link key={quote.id} to={`/proyectos/${quote.project_id}`}>
            <Card className="active:scale-[0.98]">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">{quote.code}</p>
                  <p className="text-xs text-gray-400">Proyecto {projectCode(quote.project_id)}</p>
                </div>
                <Badge tone={STATUS_TONE[quote.status]}>{QUOTE_STATUS_LABELS[quote.status]}</Badge>
              </div>
              <p className="mt-1 text-sm text-gray-500">{formatDOP(quote.total)}</p>
            </Card>
          </Link>
        ))}
        {quotes?.length === 0 && <p className="text-sm text-gray-500">No hay cotizaciones en este filtro.</p>}
      </div>
    </div>
  )
}
