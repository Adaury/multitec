import { Suspense, useEffect, useState } from 'react'
import { Navigate, NavLink, Outlet, useLocation } from 'react-router-dom'
import {
  Bot,
  Building2,
  CalendarDays,
  CircleUser,
  Clock,
  FileText,
  FolderOpen,
  Hash,
  House,
  LogOut,
  Menu,
  Package,
  PhoneCall,
  Plus,
  Settings,
  ShieldCheck,
  ShoppingCart,
  SlidersHorizontal,
  Users,
  type LucideIcon,
} from 'lucide-react'
import { api, logout } from '../lib/api'
import { useAuthStore } from '../lib/authStore'
import type { CurrentUser } from '../lib/types'
import { GlobalSearch } from './GlobalSearch'
import { NotificationBell } from './NotificationBell'
import { PendingSync } from './PendingSync'
import { GenerationBanner } from './GenerationBanner'
import { SystemStatus } from './SystemStatus'
import { PageLoader } from './PageLoader'
import { ThemeToggle } from './ThemeToggle'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  end?: boolean
}

// El técnico no tiene acceso a dinero ni compras (README → Roles y permisos): no se le ofrecen
// secciones que el servidor le rechazaría con 403.
const sidebarBaseItems: NavItem[] = [
  { to: '/', label: 'Inicio', icon: House, end: true },
  { to: '/clientes', label: 'Clientes', icon: Users },
  { to: '/proyectos', label: 'Proyectos', icon: FolderOpen },
  { to: '/calendario', label: 'Calendario', icon: CalendarDays },
  { to: '/preguntar', label: 'Preguntar IA', icon: Bot },
]

const staffSidebarItems: NavItem[] = [
  { to: '/cotizaciones', label: 'Cotizaciones', icon: FileText },
  { to: '/catalogo', label: 'Catálogo', icon: Package },
  { to: '/compras', label: 'Compras', icon: ShoppingCart },
  { to: '/seguimiento', label: 'Seguimiento', icon: PhoneCall },
  { to: '/hoja-de-tiempo', label: 'Hoja de tiempo', icon: Clock },
]

const adminSidebarItems: NavItem[] = [
  { to: '/usuarios', label: 'Usuarios', icon: Settings },
  { to: '/ncf', label: 'NCF', icon: Hash },
  { to: '/empresa', label: 'Mi empresa', icon: Building2 },
  { to: '/auditoria', label: 'Auditoría', icon: ShieldCheck },
  { to: '/aprendizaje-ia', label: 'Ajustes de IA', icon: SlidersHorizontal },
]

// Barra inferior móvil (estilo "tab bar" con botón central): los destinos de uso diario y,
// al centro, el "+" que arranca un levantamiento nuevo en un toque. Todo lo demás vive en la
// hoja "Más" para no recargar la barra.
const TAB_LEFT: NavItem[] = [
  { to: '/', label: 'Inicio', icon: House, end: true },
  { to: '/proyectos', label: 'Proyectos', icon: FolderOpen },
]
const TAB_RIGHT: NavItem[] = [{ to: '/clientes', label: 'Clientes', icon: Users }]
const IN_TAB_BAR = new Set(['/', '/proyectos', '/clientes'])

const MENU_PIN_KEY = 'multitec_menu_pinned'

function readMenuPinned(): boolean {
  try {
    return localStorage.getItem(MENU_PIN_KEY) === '1'
  } catch {
    return false
  }
}

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
      <item.icon className="h-6 w-6" aria-hidden="true" />
      {item.label}
    </NavLink>
  )
}

function MoreSheet({ items, onClose }: { items: NavItem[]; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-30 md:hidden" role="dialog" aria-modal="true" aria-label="Más opciones">
      <button aria-label="Cerrar" className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div
        className="absolute inset-x-0 bottom-0 mx-auto max-h-[88dvh] max-w-lg overflow-y-auto rounded-t-3xl bg-white p-5 shadow-2xl dark:bg-gray-900"
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
              <item.icon className="h-7 w-7" aria-hidden="true" />
              {item.label}
            </NavLink>
          ))}
          <button
            onClick={() => logout()}
            className="flex flex-col items-center gap-1 rounded-2xl bg-brand-gray px-2 py-3 text-xs font-medium text-red-600 dark:bg-gray-800 dark:text-red-400"
          >
            <LogOut className="h-7 w-7" aria-hidden="true" />
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
  // Navegador: el menú es una columna de iconos que se abre al pasar el mouse o enfocarla con el teclado;
  // el pin lo deja abierto y se recuerda (solo comodidad: sin localStorage arranca cerrado).
  const [menuHover, setMenuHover] = useState(false)
  const [menuPinned, setMenuPinned] = useState(readMenuPinned)
  function toggleMenuPinned() {
    const next = !menuPinned
    setMenuPinned(next)
    try {
      localStorage.setItem(MENU_PIN_KEY, next ? '1' : '0')
    } catch {
      // modo privado o almacenamiento bloqueado: el pin solo dura esta sesión
    }
  }
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

  const isAdmin = user?.role === 'admin'
  const isStaff = isAdmin || user?.role === 'oficina'
  const sidebarItems = [
    ...sidebarBaseItems,
    ...(isStaff ? staffSidebarItems : []),
    ...(isAdmin ? adminSidebarItems : []),
  ]
  const moreItems: NavItem[] = [
    ...sidebarItems.filter((item) => !IN_TAB_BAR.has(item.to)),
    { to: '/perfil', label: 'Mi perfil', icon: CircleUser },
  ]

  const expanded = menuPinned || menuHover

  return (
    <div className="min-h-dvh bg-brand-bg md:flex dark:bg-gray-950">
      {/* Reserva el ancho en el flujo: abierto por el mouse la barra se superpone al contenido y no lo
          empuja (sin saltos); fijada, el contenido se acomoda a su ancho. */}
      <div className={`hidden md:block md:shrink-0 ${menuPinned ? 'md:w-64' : 'md:w-[72px]'}`} />
      <aside
        onMouseEnter={() => setMenuHover(true)}
        onMouseLeave={() => setMenuHover(false)}
        onFocus={() => setMenuHover(true)}
        onBlur={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget)) setMenuHover(false)
        }}
        className={`hidden transition-[width] duration-200 md:fixed md:inset-y-0 md:left-0 md:z-20 md:flex md:flex-col md:overflow-hidden md:border-r md:border-gray-200 md:bg-white dark:md:border-gray-800 dark:md:bg-gray-900 ${
          expanded ? 'md:w-64' : 'md:w-[72px]'
        } ${expanded && !menuPinned ? 'md:shadow-2xl' : ''}`}
      >
        <div className="flex items-center gap-2.5 px-[18px] py-6">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand-blue text-lg font-bold text-white">
            M
          </span>
          {expanded && (
            <>
              <p className="flex-1 text-lg font-semibold text-gray-900 dark:text-gray-100">Multitec</p>
              <button
                onClick={toggleMenuPinned}
                aria-pressed={menuPinned}
                aria-label={menuPinned ? 'Dejar que el menú se cierre solo' : 'Mantener el menú abierto'}
                title={menuPinned ? 'Dejar que el menú se cierre solo' : 'Mantener el menú abierto'}
                className={`rounded-lg px-2 py-1 text-sm hover:bg-brand-gray dark:hover:bg-gray-800 ${
                  menuPinned ? 'text-brand-blue' : 'text-gray-400'
                }`}
              >
                📌
              </button>
            </>
          )}
        </div>
        <nav className="flex-1 space-y-1 px-3">
          {sidebarItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              title={expanded ? undefined : item.label}
              className={({ isActive }) =>
                `flex items-center gap-3 whitespace-nowrap rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                  isActive
                    ? 'bg-blue-50 text-brand-blue dark:bg-blue-950 dark:text-blue-300'
                    : 'text-gray-600 hover:bg-brand-gray dark:text-gray-400 dark:hover:bg-gray-800'
                }`
              }
            >
              <span className="flex w-6 shrink-0 justify-center" aria-hidden="true">
                <item.icon className="h-5 w-5" />
              </span>
              {/* Cerrado, el nombre sigue ahí para lectores de pantalla (sr-only) y solo se ve al abrir. */}
              <span className={expanded ? '' : 'sr-only'}>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-gray-100 px-3 py-4 dark:border-gray-800">
          {expanded ? (
            <div className="px-3">
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
          ) : (
            <div className="flex flex-col items-center gap-2">
              <NavLink
                to="/perfil"
                title={user?.name ?? 'Mi perfil'}
                className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-gray text-sm font-semibold text-gray-700 dark:bg-gray-800 dark:text-gray-200"
              >
                <span aria-hidden="true">{(user?.name ?? '?').charAt(0).toUpperCase()}</span>
                <span className="sr-only">Mi perfil</span>
              </NavLink>
              <button
                onClick={() => logout()}
                title="Salir"
                className="flex h-9 w-9 items-center justify-center rounded-full text-lg hover:bg-brand-gray dark:hover:bg-gray-800"
              >
                <LogOut className="h-5 w-5" aria-hidden="true" />
                <span className="sr-only">Salir</span>
              </button>
            </div>
          )}
        </div>
      </aside>

      <div className="mx-auto flex min-h-dvh max-w-lg flex-1 flex-col pb-28 md:mx-0 md:max-w-none md:min-w-0 md:pb-0">
        <header className="sticky top-0 z-10 flex items-center gap-4 bg-brand-bg/80 px-5 pb-4 pt-[max(1rem,env(safe-area-inset-top))] backdrop-blur md:px-10 md:py-6 dark:bg-gray-950/80">
          <NavLink to="/perfil" className="md:hidden">
            <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">Multitec</p>
            <p className="text-xs text-gray-500">{user?.name}</p>
          </NavLink>
          <div className="flex-1" />
          <div className="flex items-center gap-2">
            <ThemeToggle className="md:hidden" />
            <SystemStatus />
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

        <PendingSync />
        <GenerationBanner />

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
                className="-mt-7 mb-1 flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-brand-blue text-white shadow-lg ring-4 ring-white active:scale-95 dark:ring-gray-900"
              >
                <Plus className="h-8 w-8" strokeWidth={2.25} aria-hidden="true" />
              </NavLink>
              {TAB_RIGHT.map((item) => (
                <TabLink key={item.to} item={item} />
              ))}
              <button
                onClick={() => setMoreOpen(true)}
                className="flex flex-1 flex-col items-center gap-0.5 rounded-2xl py-1.5 text-[11px] font-medium text-gray-400"
              >
                <Menu className="h-6 w-6" aria-hidden="true" />
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
