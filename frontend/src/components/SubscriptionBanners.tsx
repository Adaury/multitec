import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, LifeBuoy, LogOut } from 'lucide-react'
import { api } from '../lib/api'
import { useAuthStore } from '../lib/authStore'
import { exitSupport } from '../lib/support'
import type { MySubscription } from '../lib/types'

/** Franja fija mientras el dueño de la plataforma está dentro de otra empresa dando soporte. */
export function SupportBanner() {
  const user = useAuthStore((s) => s.user)
  if (!user?.support_mode) return null
  const until = user.support_expires_at
    ? new Date(user.support_expires_at).toLocaleTimeString('es-DO', { hour: 'numeric', minute: '2-digit' })
    : null
  return (
    <div
      role="status"
      data-testid="support-banner"
      className="sticky top-0 z-40 flex flex-wrap items-center gap-x-3 gap-y-1 bg-amber-500 px-4 py-2 text-sm font-medium text-amber-950"
    >
      <LifeBuoy className="h-5 w-5 shrink-0" aria-hidden="true" />
      <span className="min-w-0 flex-1">
        Modo soporte — {user.company_name} · {user.support_write ? 'se permiten cambios' : 'solo lectura'}
        {until && ` · hasta las ${until}`}
      </span>
      <button
        type="button"
        onClick={exitSupport}
        className="inline-flex items-center gap-1.5 rounded-full bg-amber-950 px-3 py-1 text-xs font-semibold text-white hover:bg-amber-900"
      >
        <LogOut className="h-3.5 w-3.5" aria-hidden="true" /> Salir del soporte
      </button>
    </div>
  )
}

/** Aviso al administrador de la empresa cuando su prueba o su mensualidad están por vencer (o ya vencieron). */
export function SubscriptionNotice() {
  const user = useAuthStore((s) => s.user)
  const enabled = user?.role === 'admin' && !user.support_mode
  const { data } = useQuery({
    queryKey: ['my-subscription'],
    queryFn: async () => (await api.get<MySubscription>('/subscription')).data,
    enabled,
    staleTime: 60 * 60 * 1000,
  })
  if (!enabled || !data?.notice) return null
  return (
    <div className="mx-5 mt-3 flex flex-wrap items-center gap-2 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900 ring-1 ring-amber-200 md:mx-10 dark:bg-amber-950/40 dark:text-amber-200 dark:ring-amber-900">
      <AlertTriangle className="h-5 w-5 shrink-0" aria-hidden="true" />
      <span className="min-w-0 flex-1">{data.notice}</span>
      <Link to="/suscripcion" className="font-semibold underline">
        Ver mi suscripción
      </Link>
    </div>
  )
}
