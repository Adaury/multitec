import { useEffect } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuthStore } from '../lib/authStore'
import type { CurrentUser } from '../lib/types'

const navItems = [
  { to: '/', label: 'Inicio', icon: '🏠', end: true },
  { to: '/proyectos', label: 'Proyectos', icon: '📁' },
  { to: '/clientes', label: 'Clientes', icon: '👤' },
  { to: '/catalogo', label: 'Catálogo', icon: '📦' },
]

export function Layout() {
  const { user, logout, setUser } = useAuthStore()

  useEffect(() => {
    if (!user) {
      api
        .get<CurrentUser>('/auth/me')
        .then((res) => setUser(res.data))
        .catch(() => {})
    }
  }, [user, setUser])

  return (
    <div className="mx-auto flex min-h-screen max-w-lg flex-col bg-brand-bg pb-24">
      <header className="sticky top-0 z-10 flex items-center justify-between bg-brand-bg/80 px-5 py-4 backdrop-blur">
        <div>
          <p className="text-lg font-semibold text-gray-900">Multitec</p>
          <p className="text-xs text-gray-500">{user?.name}</p>
        </div>
        <button
          onClick={logout}
          className="rounded-full bg-white px-4 py-2 text-sm font-medium text-gray-600 shadow-sm ring-1 ring-black/5"
        >
          Salir
        </button>
      </header>

      <main className="flex-1 px-5">
        <Outlet />
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-10 mx-auto max-w-lg border-t border-gray-200 bg-white/95 backdrop-blur">
        <div className="flex justify-around px-2 py-2" style={{ paddingBottom: 'max(0.5rem, env(safe-area-inset-bottom))' }}>
          {navItems.map((item) => (
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
  )
}
