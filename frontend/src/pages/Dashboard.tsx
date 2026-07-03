import { useNavigate } from 'react-router-dom'
import { Card } from '../components/ui'
import { useAuthStore } from '../lib/authStore'

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

export function Dashboard() {
  const navigate = useNavigate()
  const isAdmin = useAuthStore((s) => s.user?.role === 'admin')
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
