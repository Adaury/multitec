import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ChevronRight, User, Wrench } from 'lucide-react'
import { api } from '../lib/api'
import type { Ticket, TicketStatus } from '../lib/types'
import { TICKET_STATUS_LABELS } from '../lib/types'
import { Badge, Card, SegmentedTabs } from '../components/ui'

interface TicketListItem extends Ticket {
  project_code: string
  client_name: string
  technician_name: string | null
}

const STATUS_TONE: Record<TicketStatus, 'red' | 'amber' | 'green' | 'gray'> = {
  abierto: 'red',
  en_proceso: 'amber',
  resuelto: 'green',
  cerrado: 'gray',
}

type View = 'abiertos' | 'todos'

/** Todos los tickets de la empresa en un solo lugar. Cada uno lleva a su proyecto, donde se trabaja
 * (asignar técnico, fotos, solución, cerrar). */
export function Tickets() {
  const [view, setView] = useState<View>('abiertos')
  const { data: tickets, isLoading, isError } = useQuery({
    queryKey: ['all-tickets', view],
    queryFn: async () =>
      (await api.get<TicketListItem[]>('/tickets', { params: { open_only: view === 'abiertos' } })).data,
  })

  return (
    <div className="space-y-4 py-4 md:space-y-6 md:py-8">
      <h1 className="text-xl font-semibold text-gray-900 sr-only dark:text-gray-100">Tickets</h1>
      <SegmentedTabs<View>
        value={view}
        onChange={setView}
        options={[
          { key: 'abiertos', label: 'Abiertos' },
          { key: 'todos', label: 'Todos' },
        ]}
      />

      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}
      {isError && <p className="text-sm text-red-600">No se pudieron cargar los tickets.</p>}
      {tickets?.length === 0 && (
        <Card className="text-center">
          <Wrench className="mx-auto h-8 w-8 text-gray-300 dark:text-gray-600" aria-hidden="true" />
          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
            {view === 'abiertos' ? 'No hay tickets abiertos.' : 'Aún no hay tickets.'}
          </p>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 md:gap-4 xl:grid-cols-3">
        {tickets?.map((ticket) => (
          <Link
            key={ticket.id}
            to={`/proyectos/${ticket.project_id}?tab=tickets&ticket=${ticket.id}`}
            className="group block rounded-3xl bg-white p-4 shadow-sm ring-1 ring-black/5 transition hover:shadow-md md:p-5 dark:bg-gray-900 dark:ring-white/10"
          >
            <div className="flex items-center justify-between gap-2">
              <p className="font-semibold text-gray-900 dark:text-gray-100">{ticket.client_name}</p>
              <Badge tone={STATUS_TONE[ticket.status]}>{TICKET_STATUS_LABELS[ticket.status]}</Badge>
            </div>
            <p className="text-xs text-gray-400">
              {ticket.code} · Proyecto {ticket.project_code} ·{' '}
              {new Date(ticket.created_at).toLocaleDateString('es-DO', { day: 'numeric', month: 'short' })}
            </p>
            <p className="mt-2 line-clamp-2 text-sm text-gray-700 dark:text-gray-300">{ticket.problem}</p>
            <div className="mt-3 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
              <span className="flex items-center gap-1">
                <User className="h-3.5 w-3.5" aria-hidden="true" />
                {ticket.technician_name ?? 'Sin técnico asignado'}
              </span>
              <ChevronRight className="h-4 w-4 transition group-hover:translate-x-0.5" aria-hidden="true" />
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
