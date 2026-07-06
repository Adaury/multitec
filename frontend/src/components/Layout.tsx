import { useEffect } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { api, logout } from '../lib/api'
import { useAuthStore } from '../lib/authStore'
import type { CurrentUser } from '../lib/types'
import { GlobalSearch } from './GlobalSearch'
import { NotificationBell } from './NotificationBell'
import { ThemeToggle } from './ThemeToggle'

interface NavItem {
  to: string
  label: string
  icon: string
  end?: boolean
}

const mobileNavItems: NavItem[] = [
  { to: '/', label: 'Inicio', icon: '🏠', end: true },
  { to: '/proyectos', label: 'Proyectos', icon: '📁' },
  { to: '/clientes', label: 'Clientes', icon: '👤' },
  { to: '/catalogo', label: 'Catálogo', icon: '📦' },
]

const sidebarBaseItems: NavItem[] = [
  { to: '/', label: 'Inicio', icon: '🏠', end: true },
  { to: '/clientes', label: 'Clientes', icon: '👤' },
  { to: '/proyectos', label: 'Proyectos', icon: '📁' },
  { to: '/calendario', label: 'Calendario', icon: '📅' },
  { to: '/catalogo', label: 'Catálogo', icon: '📦' },
  { to: '/presupuestos', label: 'Presupuestos', icon: '💰' },
  { to: '/cotizaciones', label: 'Cotizaciones', icon: '🧾' },
  { to: '/preguntar', label: 'Preguntar IA', icon: '🤖' },
]

const adminSidebarItems: NavItem[] = [
  { to: '/usuarios', label: 'Usuarios', icon: '⚙️' },
  { to: '/ncf', label: 'NCF', icon: '🧾' },
  { to: '/clasificaciones', label: 'Clasificaciones', icon: '🗂️' },
  { to: '/parametros-calculo', label: 'Parámetros IA', icon: '🎛️' },
]

export function Layout() {
  const { user, setUser } = useAuthStore()

  useEffect(() => {
    if (!user) {
      api
        .get<CurrentUser>('/auth/me')
        .then((res) => setUser(res.data))
        .catch(() => {})
    }
  }, [user, setUser])

  const sidebarItems = user?.role === 'admin' ? [...sidebarBaseItems, ...adminSidebarItems] : sidebarBaseItems

  return (
    <div className="min-h-screen bg-brand-bg md:flex dark:bg-gray-950">
      <aside className="hidden md:flex md:w-64 md:shrink-0 md:flex-col md:border-r md:border-gray-200 md:bg-white dark:md:border-gray-800 dark:md:bg-gray-900">
        <div className="flex items-center gap-2.5 px-6 py-6">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-blue text-lg font-bold text-white">
            M
          </span>
          <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">Multitec</p>
        </div>
        <nav className="flex-1 space-y-1 px-3">
          {sidebarItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                  isActive
                    ? 'bg-blue-50 text-brand-blue dark:bg-blue-950 dark:text-blue-300'
                    : 'text-gray-600 hover:bg-brand-gray dark:text-gray-400 dark:hover:bg-gray-800'
                }`
              }
            >
              <span className="text-lg">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-gray-100 px-6 py-4 dark:border-gray-800">
          <div className="mb-3 flex items-center justify-between">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-gray-900 dark:text-gray-100">{user?.name}</p>
              <p className="truncate text-xs text-gray-400">{user?.email}</p>
            </div>
            <ThemeToggle className="shrink-0" />
          </div>
          <button
            onClick={() => logout()}
            className="w-full rounded-xl bg-brand-gray px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
          >
            Salir
          </button>
        </div>
      </aside>

      <div className="mx-auto flex min-h-screen max-w-lg flex-1 flex-col pb-24 md:mx-0 md:max-w-none md:pb-0">
        <header className="sticky top-0 z-10 flex items-center gap-4 bg-brand-bg/80 px-5 py-4 backdrop-blur md:px-10 md:py-6 dark:bg-gray-950/80">
          <div className="md:hidden">
            <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">Multitec</p>
            <p className="text-xs text-gray-500">{user?.name}</p>
          </div>
          <div className="flex-1" />
          <div className="flex items-center gap-2">
            <ThemeToggle className="md:hidden" />
            <NotificationBell />
            <GlobalSearch />
            <button
              onClick={() => logout()}
              className="rounded-full bg-white px-4 py-2 text-sm font-medium text-gray-600 shadow-sm ring-1 ring-black/5 md:hidden dark:bg-gray-900 dark:text-gray-300 dark:ring-white/10"
            >
              Salir
            </button>
          </div>
        </header>

        <main className="flex-1 px-5 md:px-10 md:pb-10">
          <Outlet />
        </main>

        <nav className="fixed inset-x-0 bottom-0 z-10 mx-auto max-w-lg border-t border-gray-200 bg-white/95 backdrop-blur md:hidden dark:border-gray-800 dark:bg-gray-900/95">
          <div
            className="flex justify-around px-2 py-2"
            style={{ paddingBottom: 'max(0.5rem, env(safe-area-inset-bottom))' }}
          >
            {mobileNavItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `flex flex-col items-center gap-1 rounded-2xl px-4 py-2 text-xs font-medium ${
                    isActive ? 'text-brand-blue' : 'text-gray-400'
                  }`
                }
              >
                <span className="text-xl">{item.icon}</span>
                {item.label}
              </NavLink>
            ))}
          </div>
        </nav>
      </div>
    </div>
  )
}
