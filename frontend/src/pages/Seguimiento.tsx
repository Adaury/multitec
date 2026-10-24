import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, apiErrorMessage } from '../lib/api'
import { formatDOP } from '../lib/format'
import { Badge, Button, Card } from '../components/ui'

interface FollowupInvoice {
  invoice_id: number
  project_id: number
  code: string
  ncf: string | null
  client_name: string
  client_phone: string | null
  total: number
  issued_on: string
  due_on: string
  days_overdue: number
  overdue: boolean
  message: string
  whatsapp_url: string | null
}

interface FollowupQuote {
  quote_id: number
  project_id: number
  code: string
  client_name: string
  client_phone: string | null
  total: number
  sent_on: string
  days_waiting: number
  stale: boolean
  message: string
  whatsapp_url: string | null
}

interface Followups {
  receivables_total: number
  overdue_total: number
  overdue_count: number
  receivables: FollowupInvoice[]
  quotes: FollowupQuote[]
}

function shortDate(iso: string): string {
  const [year, month, day] = iso.split('-')
  return `${day}/${month}/${year}`
}

function plural(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`
}

function dueBadge(row: FollowupInvoice) {
  if (row.days_overdue > 0) return <Badge tone="red">Vencida hace {plural(row.days_overdue, 'día', 'días')}</Badge>
  if (row.days_overdue === 0) return <Badge tone="amber">Vence hoy</Badge>
  return <Badge tone="gray">Vence en {plural(-row.days_overdue, 'día', 'días')}</Badge>
}

/** Mensaje de seguimiento: abrir WhatsApp con el texto ya escrito o copiarlo. Nada se envía solo. */
function MessageActions({ message, whatsappUrl }: { message: string; whatsappUrl: string | null }) {
  const [copied, setCopied] = useState<'ok' | 'error' | null>(null)

  async function copy() {
    try {
      await navigator.clipboard.writeText(message)
      setCopied('ok')
    } catch {
      setCopied('error')
    }
    window.setTimeout(() => setCopied(null), 2500)
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {whatsappUrl ? (
        <a
          href={whatsappUrl}
          target="_blank"
          rel="noreferrer"
          className="rounded-full bg-green-600 px-4 py-2 text-sm font-medium text-white"
        >
          💬 WhatsApp
        </a>
      ) : (
        <span className="text-xs text-gray-400">Sin teléfono válido</span>
      )}
      <button
        type="button"
        onClick={copy}
        className="rounded-full bg-brand-gray px-4 py-2 text-sm font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300"
      >
        {copied === 'ok' ? '✓ Copiado' : copied === 'error' ? 'No se pudo copiar' : 'Copiar mensaje'}
      </button>
    </div>
  )
}

export function Seguimiento() {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['followups'],
    queryFn: async () => (await api.get<Followups>('/followups')).data,
  })

  const markPaid = useMutation({
    mutationFn: async (invoiceId: number) => (await api.put(`/invoices/${invoiceId}/paid`, { paid: true })).data,
    onSuccess: () => {
      setError(null)
      queryClient.invalidateQueries({ queryKey: ['followups'] })
    },
    onError: (err) => setError(apiErrorMessage(err, 'No se pudo marcar la factura como cobrada')),
  })

  if (isLoading || !data) return <p className="text-sm text-gray-500">Cargando…</p>

  return (
    <div className="space-y-5 md:space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Seguimiento</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Lo que tienes por cobrar y las cotizaciones que siguen sin respuesta, con el mensaje ya escrito para
          el cliente. Tú decides si lo envías.
        </p>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <Card className="space-y-1">
          <p className="text-xs text-gray-400">Por cobrar</p>
          <p className="text-base font-bold text-gray-900 dark:text-gray-100 md:text-xl">{formatDOP(data.receivables_total)}</p>
        </Card>
        <Card className="space-y-1">
          <p className="text-xs text-gray-400">Vencido ({data.overdue_count})</p>
          <p className="text-base font-bold text-red-600 dark:text-red-400 md:text-xl">{formatDOP(data.overdue_total)}</p>
        </Card>
        <Card className="space-y-1">
          <p className="text-xs text-gray-400">Cotizaciones</p>
          <p className="text-base font-bold text-gray-900 dark:text-gray-100 md:text-xl">{data.quotes.length}</p>
        </Card>
      </div>

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Facturas por cobrar</h2>
        {data.receivables.length === 0 && (
          <p className="text-sm text-gray-500">No tienes facturas por cobrar. 🎉</p>
        )}
        <div className="grid gap-3 md:grid-cols-2">
          {data.receivables.map((row) => (
            <Card key={row.invoice_id} testId={`factura-${row.code}`} className="space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate font-medium text-gray-900 dark:text-gray-100">{row.client_name}</p>
                  <p className="text-xs text-gray-400">
                    <Link to={`/proyectos/${row.project_id}`} className="underline">
                      {row.code}
                    </Link>
                    {row.ncf && ` · NCF ${row.ncf}`} · vence {shortDate(row.due_on)}
                  </p>
                </div>
                <div className="space-y-1 text-right">
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{formatDOP(row.total)}</p>
                  {dueBadge(row)}
                </div>
              </div>
              <MessageActions message={row.message} whatsappUrl={row.whatsapp_url} />
              <button
                type="button"
                onClick={() => setPreview(preview === `i${row.invoice_id}` ? null : `i${row.invoice_id}`)}
                className="text-xs text-brand-blue underline"
              >
                {preview === `i${row.invoice_id}` ? 'Ocultar mensaje' : 'Ver el mensaje'}
              </button>
              {preview === `i${row.invoice_id}` && (
                <p className="rounded-xl bg-brand-gray p-3 text-sm text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                  {row.message}
                </p>
              )}
              <Button
                variant="secondary"
                disabled={markPaid.isPending}
                onClick={() => {
                  if (window.confirm(`¿Marcar la factura ${row.code} como cobrada?`)) markPaid.mutate(row.invoice_id)
                }}
              >
                ✔ Marcar como cobrada
              </Button>
            </Card>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Cotizaciones sin respuesta</h2>
        {data.quotes.length === 0 && (
          <p className="text-sm text-gray-500">No hay cotizaciones esperando respuesta hace más de 3 días.</p>
        )}
        <div className="grid gap-3 md:grid-cols-2">
          {data.quotes.map((row) => (
            <Card key={row.quote_id} testId={`cotizacion-${row.code}`} className="space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate font-medium text-gray-900 dark:text-gray-100">{row.client_name}</p>
                  <p className="text-xs text-gray-400">
                    {row.code} · enviada el {shortDate(row.sent_on)}
                  </p>
                </div>
                <div className="space-y-1 text-right">
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{formatDOP(row.total)}</p>
                  <Badge tone={row.stale ? 'red' : 'amber'}>
                    {plural(row.days_waiting, 'día', 'días')} sin respuesta
                  </Badge>
                </div>
              </div>
              {row.stale && (
                <p className="text-xs text-red-600 dark:text-red-400">
                  Pasó el plazo: si nadie responde, la cotización se archiva sola.
                </p>
              )}
              <MessageActions message={row.message} whatsappUrl={row.whatsapp_url} />
              <Link
                to={`/proyectos/${row.project_id}?tab=cotizacion`}
                className="inline-block text-sm font-medium text-brand-blue underline"
              >
                Ver la cotización
              </Link>
            </Card>
          ))}
        </div>
      </section>
    </div>
  )
}
