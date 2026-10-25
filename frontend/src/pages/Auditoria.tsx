import { useState } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { AuditEntry } from '../lib/types'
import { Button, Card } from '../components/ui'

const PAGE = 100

// Nombres en español de las acciones que registra el servidor (backend/app/services/audit.py).
const ACTIONS: Record<string, string> = {
  login: 'Inició sesión',
  login_failed: 'Intento de acceso fallido',
  login_blocked: 'Acceso bloqueado por intentos',
  login_inactive: 'Intento con cuenta desactivada',
  logout_all: 'Cerró todas sus sesiones',
  password_changed: 'Cambió su contraseña',
  password_reset_by_admin: 'Contraseña restablecida por un admin',
  user_created: 'Usuario creado',
  user_updated: 'Usuario modificado',
  session_revoked: 'Sesión cerrada por un admin',
  sessions_revoked_all: 'Sesiones cerradas por un admin',
  product_price_changed: 'Cambió un precio',
  catalog_prices_changed: 'Cambió precios en bloque',
  invoice_voided: 'Anuló una factura',
  ncf_sequence_created: 'Creó una secuencia de NCF',
  ncf_sequence_toggled: 'Activó o desactivó una secuencia de NCF',
  company_updated: 'Modificó los datos de la empresa',
  portal_link_created: 'Creó un enlace de portal',
  portal_link_rotated: 'Renovó un enlace de portal',
  portal_link_revoked: 'Quitó un enlace de portal',
}

const WARN = new Set(['login_failed', 'login_blocked', 'login_inactive', 'invoice_voided'])

function readableDetail(detail: string | null): string {
  if (!detail) return ''
  try {
    const parsed = JSON.parse(detail) as Record<string, unknown>
    return Object.entries(parsed)
      .map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : String(v)}`)
      .join(' · ')
  } catch {
    return detail
  }
}

/** Bitácora de auditoría: quién hizo qué y cuándo. Solo la ve el administrador. */
export function Auditoria() {
  const [action, setAction] = useState('')
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, isLoading } = useInfiniteQuery({
    queryKey: ['audit', action],
    initialPageParam: undefined as number | undefined,
    queryFn: async ({ pageParam }) =>
      (
        await api.get<AuditEntry[]>('/audit', {
          params: { limit: PAGE, action: action || undefined, before_id: pageParam },
        })
      ).data,
    getNextPageParam: (last) => (last.length === PAGE ? last[last.length - 1].id : undefined),
  })
  const rows = data?.pages.flat() ?? []

  return (
    <div className="space-y-4 py-4 md:space-y-6 md:py-8">
      <div>
        <h1 className="text-xl font-semibold text-gray-900 md:text-2xl dark:text-gray-100">Auditoría</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Quién hizo qué y cuándo: accesos, usuarios, precios, facturas anuladas y datos de la empresa. Los registros no
          se pueden editar ni borrar desde la aplicación.
        </p>
      </div>

      <select
        aria-label="Filtrar por acción"
        className="rounded-xl border border-gray-200 bg-white px-4 py-2 text-base text-gray-900 md:max-w-xs dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
        value={action}
        onChange={(e) => setAction(e.target.value)}
      >
        <option value="">Todas las acciones</option>
        {Object.entries(ACTIONS).map(([key, label]) => (
          <option key={key} value={key}>
            {label}
          </option>
        ))}
      </select>

      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}
      {!isLoading && rows.length === 0 && <p className="text-sm text-gray-500">Todavía no hay registros.</p>}

      <div className="space-y-2">
        {rows.map((row) => (
          <Card key={row.id} className="space-y-1 !p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p
                className={`text-sm font-medium ${
                  WARN.has(row.action) ? 'text-amber-700 dark:text-amber-400' : 'text-gray-900 dark:text-gray-100'
                }`}
              >
                {ACTIONS[row.action] ?? row.action}
              </p>
              <p className="text-xs text-gray-400">
                {new Date(row.created_at).toLocaleString('es-DO', { dateStyle: 'medium', timeStyle: 'short' })}
              </p>
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {row.user_email ?? 'Anónimo'}
              {row.ip ? ` · ${row.ip}` : ''}
            </p>
            {row.detail && (
              <p className="break-words text-xs text-gray-600 dark:text-gray-300">{readableDetail(row.detail)}</p>
            )}
          </Card>
        ))}
      </div>

      {hasNextPage && (
        <Button variant="secondary" className="!w-auto px-4" onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
          {isFetchingNextPage ? 'Cargando…' : 'Ver registros anteriores'}
        </Button>
      )}
    </div>
  )
}
