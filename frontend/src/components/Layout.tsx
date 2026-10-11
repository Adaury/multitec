import { Suspense, useEffect, useState } from 'react'
import { Navigate, NavLink, Outlet, useLocation } from 'react-router-dom'
import { api, logout } from '../lib/api'
import { useAuthStore } from '../lib/authStore'
import type { CurrentUser } from '../lib/types'
import { GlobalSearch } from './GlobalSearch'
import { NotificationBell } from './NotificationBell'
import { PageLoader } from './PageLoader'
import { ThemeToggle } from './ThemeToggle'

interface NavItem {
  to: string
  label: string
  icon: string
  end?: boolean
}

const sidebarBaseItems: NavItem[] = [
  { to: '/', label: 'Inicio', icon: '🏠', end: true },
  { to: '/clientes', label: 'Clientes', icon: '👤' },
  { to: '/proyectos', label: 'Proyectos', icon: '📁' },
  { to: '/calendario', label: 'Calendario', icon: '📅' },
  { to: '/catalogo', label: 'Catálogo', icon: '📦' },
  { to: '/proveedores', label: 'Proveedores', icon: '🏢' },
  { to: '/compras', label: 'Compras', icon: '🛒' },
  { to: '/presupuestos', label: 'Presupuestos', icon: '💰' },
  { to: '/cotizaciones', label: 'Cotizaciones', icon: '🧾' },
  { to: '/preguntar', label: 'Preguntar IA', icon: '🤖' },
]

const adminSidebarItems: NavItem[] = [
  { to: '/usuarios', label: 'Usuarios', icon: '⚙️' },
  { to: '/ncf', label: 'NCF', icon: '🧾' },
  { to: '/clasificaciones', label: 'Clasificaciones', icon: '🗂️' },
  { to: '/parametros-calculo', label: 'Parámetros IA', icon: '🎛️' },
  { to: '/aprendizaje-ia', label: 'Aprendizaje IA', icon: '📈' },
]

// Barra inferior móvil (estilo "tab bar" con botón central): los destinos de uso diario y,
// al centro, el "+" que arranca un levantamiento nuevo en un toque. Todo lo demás vive en la
// hoja "Más" para no recargar la barra.
const TAB_LEFT: NavItem[] = [
  { to: '/', label: 'Inicio', icon: '🏠', end: true },
  { to: '/proyectos', label: 'Proyectos', icon: '📁' },
]
const TAB_RIGHT: NavItem[] = [{ to: '/clientes', label: 'Clientes', icon: '👤' }]
const IN_TAB_BAR = new Set(['/', '/proyectos', '/clientes'])

function TabLink({ item }: { item: NavItem }) {
  return (
    <NavLink
      to={item.to}
      end={item.end}
      className={({ isActive }) =>
        `flex flex-1 flex-col items-center gap-0.5 rounded-2xl py-1.5 text-[11px] font-medium ${
          isActive ? 'text-brand-blue' : 'text-gray-400'
        }`
      }
    >
      <span className="text-xl leading-none">{item.icon}</span>
      {item.label}
    </NavLink>
  )
}

function MoreSheet({ items, onClose }: { items: NavItem[]; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-30 md:hidden" role="dialog" aria-modal="true" aria-label="Más opciones">
      <button aria-label="Cerrar" className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div
        className="absolute inset-x-0 bottom-0 mx-auto max-w-lg rounded-t-3xl bg-white p-5 shadow-2xl dark:bg-gray-900"
        style={{ paddingBottom: 'max(1.25rem, env(safe-area-inset-bottom))' }}
      >
        <div className="mx-auto mb-4 h-1.5 w-10 rounded-full bg-gray-300 dark:bg-gray-700" />
        <div className="grid grid-cols-3 gap-3">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onClose}
              className="flex flex-col items-center gap-1 rounded-2xl bg-brand-gray px-2 py-3 text-center text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-200"
            >
              <span className="text-2xl">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
          <button
            onClick={() => logout()}
            className="flex flex-col items-center gap-1 rounded-2xl bg-brand-gray px-2 py-3 text-xs font-medium text-red-600 dark:bg-gray-800 dark:text-red-400"
          >
            <span className="text-2xl">🚪</span>
            Salir
          </button>
        </div>
      </div>
    </div>
  )
}

export function Layout() {
  const { user, setUser } = useAuthStore()
  const location = useLocation()
  const [moreOpen, setMoreOpen] = useState(false)
  // En el levantamiento rápido la pantalla es de enfoque total: sin barra inferior.
  const hideTabBar = location.pathname.startsWith('/nuevo')

  useEffect(() => {
    if (!user) {
      api
        .get<CurrentUser>('/auth/me')
        .then((res) => setUser(res.data))
        .catch(() => {})
    }
  }, [user, setUser])

  // Contraseña temporal: el servidor ya bloquea todo menos el perfil; aquí se lleva al usuario ahí.
  if (user?.must_change_password && location.pathname !== '/perfil') {
    return <Navigate to="/perfil" replace />
  }

  const sidebarItems = user?.role === 'admin' ? [...sidebarBaseItems, ...adminSidebarItems] : sidebarBaseItems
  const moreItems: NavItem[] = [
    ...sidebarItems.filter((item) => !IN_TAB_BAR.has(item.to)),
    { to: '/perfil', label: 'Mi perfil', icon: '🙍' },
  ]

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
            <NavLink to="/perfil" title="Mi perfil" className="min-w-0 rounded-lg hover:opacity-80">
              <p className="truncate text-sm font-medium text-gray-900 dark:text-gray-100">{user?.name}</p>
              <p className="truncate text-xs text-gray-400">{user?.email}</p>
            </NavLink>
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

      <div className="mx-auto flex min-h-screen max-w-lg flex-1 flex-col pb-28 md:mx-0 md:max-w-none md:min-w-0 md:pb-0">
        <header className="sticky top-0 z-10 flex items-center gap-4 bg-brand-bg/80 px-5 py-4 backdrop-blur md:px-10 md:py-6 dark:bg-gray-950/80">
          <NavLink to="/perfil" className="md:hidden">
            <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">Multitec</p>
            <p className="text-xs text-gray-500">{user?.name}</p>
          </NavLink>
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
          <Suspense fallback={<PageLoader />}>
            <Outlet />
          </Suspense>
        </main>

        {!hideTabBar && (
          <nav className="fixed inset-x-0 bottom-0 z-10 mx-auto max-w-lg border-t border-gray-200 bg-white/95 backdrop-blur md:hidden dark:border-gray-800 dark:bg-gray-900/95">
            <div
              className="flex items-end px-2 pt-2"
              style={{ paddingBottom: 'max(0.5rem, env(safe-area-inset-bottom))' }}
            >
              {TAB_LEFT.map((item) => (
                <TabLink key={item.to} item={item} />
              ))}
              <NavLink
                to="/nuevo"
                aria-label="Nuevo levantamiento"
                className="-mt-7 mb-1 flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-brand-blue text-4xl font-light leading-none text-white shadow-lg ring-4 ring-white active:scale-95 dark:ring-gray-900"
              >
                +
              </NavLink>
              {TAB_RIGHT.map((item) => (
                <TabLink key={item.to} item={item} />
              ))}
              <button
                onClick={() => setMoreOpen(true)}
                className="flex flex-1 flex-col items-center gap-0.5 rounded-2xl py-1.5 text-[11px] font-medium text-gray-400"
              >
                <span className="text-xl leading-none">☰</span>
                Más
              </button>
            </div>
          </nav>
        )}
        {moreOpen && <MoreSheet items={moreItems} onClose={() => setMoreOpen(false)} />}
      </div>
    </div>
  )
}
