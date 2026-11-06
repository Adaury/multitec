import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CalendarClock, MessageCircle, Receipt, Wallet } from 'lucide-react'
import { api } from '../lib/api'
import type { CompanyState, MySubscription } from '../lib/types'
import { Card } from '../components/ui'

const STATE: Record<CompanyState, { label: string; tone: string }> = {
  prueba: { label: 'En prueba gratis', tone: 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300' },
  activa: { label: 'Al día', tone: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' },
  atrasada: { label: 'Pago atrasado', tone: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300' },
  vencida: { label: 'Prueba terminada', tone: 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300' },
  cortada: { label: 'Suspendida por falta de pago', tone: 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300' },
  suspendida: { label: 'Suspendida', tone: 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300' },
}

const money = (n: number) => `RD$${n.toLocaleString('es-DO', { minimumFractionDigits: 2 })}`
const day = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString('es-DO', { day: 'numeric', month: 'long', year: 'numeric' }) : '—')

/** «Mi suscripción»: el administrador ve su plan, hasta cuándo tiene servicio, cómo pagar y sus pagos. */
export function MiSuscripcion() {
  const { data, isLoading } = useQuery({
    queryKey: ['my-subscription'],
    queryFn: async () => (await api.get<MySubscription>('/subscription')).data,
  })
  if (isLoading || !data) return <p className="py-8 text-center text-gray-500">Cargando…</p>

  const state = STATE[data.state]
  const until = data.paid_until ?? data.trial_ends_at
  const whatsapp = data.contact_phone.replace(/\D/g, '')

  return (
    <div className="mx-auto max-w-4xl space-y-4 py-4 md:py-8">
      <h1 className="sr-only">Mi suscripción</h1>
      {data.notice && (
        <div className="flex gap-2 rounded-2xl bg-amber-50 p-4 text-sm text-amber-900 ring-1 ring-amber-200 dark:bg-amber-950/40 dark:text-amber-200 dark:ring-amber-900">
          <AlertTriangle className="h-5 w-5 shrink-0" aria-hidden="true" /> {data.notice}
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-3">
        <Card>
          <p className="flex items-center gap-1.5 text-xs font-medium text-gray-500">
            <CalendarClock className="h-4 w-4" aria-hidden="true" /> Estado
          </p>
          <span className={`mt-2 inline-block rounded-full px-3 py-1 text-sm font-semibold ${state.tone}`}>{state.label}</span>
          {until && (
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              {data.paid_until ? 'Pagado hasta' : 'La prueba termina'} el <b>{day(until)}</b>
              {data.days_left !== null && data.days_left >= 0 && ` (${data.days_left} días)`}
            </p>
          )}
          {!until && <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Sin vencimiento.</p>}
        </Card>
        <Card>
          <p className="flex items-center gap-1.5 text-xs font-medium text-gray-500">
            <Wallet className="h-4 w-4" aria-hidden="true" /> Mensualidad
          </p>
          <p className="mt-2 text-2xl font-extrabold text-gray-900 dark:text-gray-100">{money(data.monthly_fee)}</p>
          <p className="text-xs text-gray-500">soporte y uso de la plataforma</p>
        </Card>
        <Card>
          <p className="flex items-center gap-1.5 text-xs font-medium text-gray-500">
            <Receipt className="h-4 w-4" aria-hidden="true" /> Instalación y explicación
          </p>
          <p className="mt-2 text-2xl font-extrabold text-gray-900 dark:text-gray-100">{money(data.setup_fee)}</p>
          <p className="text-xs text-gray-500">{data.setup_paid ? '✓ Pagada' : 'Una sola vez, pendiente'}</p>
        </Card>
      </div>

      {(data.payment_info || whatsapp) && (
        <Card>
          <p className="font-semibold text-gray-900 dark:text-gray-100">Cómo pagar</p>
          {data.payment_info && (
            <p className="mt-2 whitespace-pre-line text-sm text-gray-700 dark:text-gray-300">{data.payment_info}</p>
          )}
          {whatsapp && (
            <a
              href={`https://wa.me/${whatsapp}?text=${encodeURIComponent(`Hola, soy de ${data.company_name}. Les escribo por mi suscripción de Multitec.`)}`}
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-flex items-center gap-2 rounded-full bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
            >
              <MessageCircle className="h-4 w-4" aria-hidden="true" /> Avisar mi pago por WhatsApp
            </a>
          )}
        </Card>
      )}

      <Card>
        <p className="mb-3 font-semibold text-gray-900 dark:text-gray-100">Mis pagos</p>
        {data.payments.length === 0 ? (
          <p className="text-sm text-gray-500">Todavía no hay pagos registrados.</p>
        ) : (
          <ul className="divide-y divide-gray-100 dark:divide-gray-800">
            {data.payments.map((p) => (
              <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
                <span className="text-gray-900 dark:text-gray-100">
                  {p.kind === 'instalacion' ? 'Instalación y explicación' : `Mensualidad${p.months > 1 ? ` (${p.months} meses)` : ''}`}
                  <span className="block text-xs text-gray-500">
                    {day(p.paid_at)} · {p.method}
                    {p.reference ? ` · ${p.reference}` : ''}
                  </span>
                </span>
                <span className="font-semibold text-gray-900 dark:text-gray-100">{money(p.amount)}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
