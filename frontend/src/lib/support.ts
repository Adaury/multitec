import { useAuthStore } from './authStore'
import { safeStorage } from './safeStorage'

// Mientras dura el soporte, la sesión del panel queda guardada aparte para volver a ella al salir.
const PLATFORM_TOKEN_KEY = 'multitec_platform_token'
const SUPPORT_KEY = 'multitec_support'

interface SupportInfo {
  companyId: number
  companyName: string
}

export function supportInfo(): SupportInfo | null {
  const raw = safeStorage.get(SUPPORT_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as SupportInfo
  } catch {
    return null
  }
}

/** Entra a una empresa como soporte con el token que dio el servidor (vence en 1 hora). */
export function enterSupport(token: string, companyId: number, companyName: string) {
  const current = useAuthStore.getState().token
  if (current && !supportInfo()) safeStorage.set(PLATFORM_TOKEN_KEY, current)
  safeStorage.set(SUPPORT_KEY, JSON.stringify({ companyId, companyName }))
  useAuthStore.getState().setToken(token)
  window.location.assign('/')
}

/** Sale del soporte y vuelve al panel con la sesión de antes. */
export function exitSupport() {
  const info = supportInfo()
  const platformToken = safeStorage.get(PLATFORM_TOKEN_KEY)
  safeStorage.remove(SUPPORT_KEY)
  safeStorage.remove(PLATFORM_TOKEN_KEY)
  if (platformToken) useAuthStore.getState().setToken(platformToken)
  else useAuthStore.getState().logout()
  window.location.assign(info ? `/plataforma/${info.companyId}` : '/plataforma')
}
