import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api, downloadFile } from '../lib/api'
import { Card } from '../components/ui'
import { useAuthStore } from '../lib/authStore'
import { formatDOP } from '../lib/format'
import { PROJECT_STATUS_LABELS, type DashboardSummary } from '../lib/types'

const quickActions = [
  { label: 'Nuevo Proyecto', icon: '➕', to: '/proyectos?nuevo=1' },
  { label: 'Nuevo Levantamiento', icon: '📋', to: '/proyectos' },
  { label: 'Nueva Cotización', icon: '🧾', to: '/proyectos' },
]

const baseMenu = [
  { label: 'Clientes', icon: '👤', to: '/clientes' },
  { label: 'Proyectos', icon: '📁', to: '/proyectos' },
  { label: 'Catálogo', icon: '📦', to: '/catalogo' },
  { label: 'Presupuestos', icon: '💰', to: '/presupuestos' },
  { label: 'Cotizaciones', icon: '🧾', to: '/cotizaciones' },
  { label: 'Compras', icon: '🛒', to: '/proyectos' },
  { label: 'Prefacturas', icon: '📄', to: '/proyectos' },
  { label: 'Facturas', icon: '🧮', to: '/proyectos' },
  { label: 'Bitácora', icon: '📓', to: '/proyectos' },
  { label: 'Tickets', icon: '🎫', to: '/proyectos' },
  { label: 'Preguntar IA', icon: '🤖', to: '/preguntar' },
]

function MonthlyInvoicingChart({ data }: { data: DashboardSummary['monthly_invoicing'] }) {
  const max = Math.max(1, ...data.map((row) => row.total))
  return (
    <div className="flex items-end justify-between gap-2" style={{ height: 100 }}>
      {data.map((row) => {
        const [year, month] = row.month.split('-')
        const label = new Date(Number(year), Number(month) - 1, 1).toLocaleDateString('es-DO', { month: 'short' })
        return (
          <div key={row.month} className="flex flex-1 flex-col items-center gap-1">
            <div className="flex h-16 w-full items-end">
              <div
                className="w-full rounded-t-md bg-brand-blue"
                style={{ height: `${Math.max(4, (row.total / max) * 100)}%` }}
                title={formatDOP(row.total)}
              />
            </div>
            <span className="text-[10px] capitalize text-gray-400">{label}</span>
          </div>
        )
      })}
    </div>
  )
}

function DashboardKpis() {
  const { data } = useQuery({
    queryKey: ['reports', 'dashboard'],
    queryFn: async () => (await api.get<DashboardSummary>('/reports/dashboard')).data,
  })

  if (!data) return null

  return (
    <div>
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Resumen</h2>
        <div className="flex gap-2">
          <button
            onClick={() => downloadFile('/reports/dashboard/export', 'dashboard.csv')}
            className="rounded-full bg-brand-gray px-3 py-1.5 text-xs font-medium text-gray-700"
          >
            Exportar resumen
          </button>
          <button
            onClick={() => downloadFile('/invoices/export', 'facturas.csv')}
            className="rounded-full bg-brand-gray px-3 py-1.5 text-xs font-medium text-gray-700"
          >
            Exportar facturas
          </button>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <Card>
          <p className="text-xs font-medium text-gray-500">Cotizaciones pendientes</p>
          <p className="mt-1 text-2xl font-semibold text-gray-900">{data.quotes_pending}</p>
        </Card>
        <Card>
          <p className="text-xs font-medium text-gray-500">Tickets abiertos</p>
          <p className="mt-1 text-2xl font-semibold text-gray-900">{data.open_tickets_total}</p>
        </Card>
      </div>

      <Card className="mt-3">
        <p className="text-xs font-medium text-gray-500">Facturación (últimos 6 meses)</p>
        <div className="mt-3">
          <MonthlyInvoicingChart data={data.monthly_invoicing} />
        </div>
      </Card>

      <Card className="mt-3 space-y-2">
        <p className="text-xs font-medium text-gray-500">Proyectos por estado</p>
        {data.projects_by_status.map((row) => (
          <div key={row.status} className="flex items-center justify-between text-sm">
            <span className="text-gray-700">{PROJECT_STATUS_LABELS[row.status] ?? row.status}</span>
            <span className="font-medium text-gray-900">{row.count}</span>
          </div>
        ))}
        {data.projects_by_status.length === 0 && <p className="text-sm text-gray-400">Sin proyectos aún.</p>}
      </Card>

      {data.open_tickets_total > 0 && (
        <Card className="mt-3 space-y-2">
          <p className="text-xs font-medium text-gray-500">Tickets abiertos por técnico</p>
          {data.open_tickets_by_technician.map((row) => (
            <div key={row.technician} className="flex items-center justify-between text-sm">
              <span className="text-gray-700">{row.technician}</span>
              <span className="font-medium text-gray-900">{row.count}</span>
            </div>
          ))}
        </Card>
      )}
    </div>
  )
}

export function Dashboard() {
  const navigate = useNavigate()
  const role = useAuthStore((s) => s.user?.role)
  const isAdmin = role === 'admin'
  const canSeeReports = role === 'admin' || role === 'oficina'
  const menu = isAdmin
    ? [...baseMenu, { label: 'Usuarios', icon: '⚙️', to: '/usuarios' }, { label: 'NCF', icon: '🧾', to: '/ncf' }]
    : baseMenu

  return (
    <div className="space-y-6 py-4">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Acciones rápidas</h1>
        <div className="mt-3 grid grid-cols-3 gap-3">
          {quickActions.map((action) => (
            <button
              key={action.label}
              disabled={!action.to}
              onClick={() => action.to && navigate(action.to)}
              className="flex flex-col items-center gap-2 rounded-2xl bg-white p-4 text-center shadow-sm ring-1 ring-black/5 disabled:opacity-40"
            >
              <span className="text-2xl">{action.icon}</span>
              <span className="text-xs font-medium text-gray-700">{action.label}</span>
            </button>
          ))}
        </div>
      </div>

      {canSeeReports && <DashboardKpis />}

      <div>
        <h2 className="text-lg font-semibold text-gray-900">Menú</h2>
        <div className="mt-3 grid grid-cols-2 gap-3">
          {menu.map((item) => (
            <Card
              key={item.label}
              className={`flex items-center gap-3 ${!item.to ? 'opacity-40' : 'cursor-pointer active:scale-[0.98]'}`}
            >
              <button
                disabled={!item.to}
                onClick={() => item.to && navigate(item.to)}
                className="flex w-full items-center gap-3 text-left disabled:cursor-default"
              >
                <span className="text-xl">{item.icon}</span>
                <span className="text-sm font-medium text-gray-800">
                  {item.label}
                  {!item.to && <span className="block text-[10px] font-normal text-gray-400">próximamente</span>}
                </span>
              </button>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}
