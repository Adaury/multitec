import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../lib/authStore'
import { PageLoader } from './PageLoader'

export function ProtectedRoute() {
  const token = useAuthStore((s) => s.token)
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return <Outlet />
}

/** Sección reservada a ciertos roles: quien no la tiene vuelve al Inicio en vez de ver una pantalla
 * vacía (el servidor ya responde 403; esto solo evita la confusión). */
/** Panel de la plataforma (crear y suspender empresas): solo el dueño del sistema. */
export function PlatformRoute() {
  const user = useAuthStore((s) => s.user)
  if (!user) return <PageLoader />
  if (!user.is_platform_admin) return <Navigate to="/" replace />
  return <Outlet />
}

export function RoleRoute({ roles }: { roles: string[] }) {
  const user = useAuthStore((s) => s.user)
  if (!user) return <PageLoader />
  if (!roles.includes(user.role)) return <Navigate to="/" replace />
  return <Outlet />
}
