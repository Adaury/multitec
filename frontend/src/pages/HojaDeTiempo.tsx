import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, downloadFile } from '../lib/api'
import { localISODate } from '../lib/format'
import { formatMinutes } from '../lib/geoPunch'
import { Button, Card, Field, Input } from '../components/ui'

interface TimesheetRow {
  visit_id: number
  date: string
  technician: string
  project_code: string
  client_name: string
  checkin_at: string
  checkout_at: string | null
  minutes: number | null
}

interface TimesheetTotal {
  technician_id: number | null
  technician: string
  visits: number
  minutes: number
  open: number
}

interface Timesheet {
  start: string
  end: string
  rows: TimesheetRow[]
  totals: TimesheetTotal[]
}

function mondayOfThisWeek(): string {
  const d = new Date()
  d.setDate(d.getDate() - ((d.getDay() + 6) % 7))
  return localISODate(d)
}

const clock = (iso: string) =>
  new Date(iso).toLocaleTimeString('es-DO', { hour: '2-digit', minute: '2-digit', hour12: false })

/** Horas en el sitio de cada técnico, sacadas de la entrada y salida que marca en cada visita. */
export function HojaDeTiempo() {
  const [start, setStart] = useState(mondayOfThisWeek())
  const [end, setEnd] = useState(localISODate())

  const { data, isLoading, isError } = useQuery({
    queryKey: ['timesheet', start, end],
    queryFn: async () => (await api.get<Timesheet>('/reports/timesheet', { params: { start, end } })).data,
    enabled: !!start && !!end && start <= end,
  })

  return (
    <div className="space-y-4 py-4 md:space-y-6 md:py-8">
      <div>
        <h1 className="text-xl font-semibold text-gray-900 md:text-2xl dark:text-gray-100">Hoja de tiempo</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Las horas salen de «Llegué al sitio» y «Terminé la visita» que marca cada técnico en el Calendario. Una visita
          sin salida queda abierta y no suma horas.
        </p>
      </div>

      <div className="grid gap-3 md:max-w-xl md:grid-cols-3 md:items-end">
        <Field label="Desde">
          <Input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        </Field>
        <Field label="Hasta">
          <Input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
        </Field>
        <Button
          variant="secondary"
          onClick={() => downloadFile(`/reports/timesheet/export?start=${start}&end=${end}`, `hoja-de-tiempo-${start}-${end}.csv`)}
          disabled={!data || data.rows.length === 0}
        >
          Descargar CSV
        </Button>
      </div>

      {start > end && <p className="text-sm text-red-600 dark:text-red-400">La fecha final no puede ser anterior a la inicial.</p>}
      {isError && <p className="text-sm text-red-600 dark:text-red-400">No se pudo cargar la hoja de tiempo.</p>}
      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}
      {data && data.rows.length === 0 && (
        <p className="text-sm text-gray-500">No hay visitas con entrada marcada en este rango.</p>
      )}

      {data && data.totals.length > 0 && (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {data.totals.map((t) => (
            <Card key={`${t.technician_id}-${t.technician}`} className="space-y-1">
              <p className="font-medium text-gray-900 dark:text-gray-100">{t.technician}</p>
              <p className="text-2xl font-semibold text-brand-blue">{formatMinutes(t.minutes)}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {t.visits} {t.visits === 1 ? 'visita' : 'visitas'}
                {t.open > 0 && ` · ${t.open} sin salida`}
              </p>
            </Card>
          ))}
        </div>
      )}

      {data && data.rows.length > 0 && (
        <div className="space-y-2">
          {data.rows.map((r) => (
            <Card key={r.visit_id} className="!p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {r.date} · {r.technician}
                </p>
                <p className="text-sm font-semibold text-brand-blue">
                  {r.minutes != null ? formatMinutes(r.minutes) : 'En curso / sin salida'}
                </p>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {r.project_code} · {r.client_name} · {clock(r.checkin_at)}
                {r.checkout_at ? ` a ${clock(r.checkout_at)}` : ''}
              </p>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
