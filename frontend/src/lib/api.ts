import axios from 'axios'
import { LEGACY_REFRESH_STORAGE_KEY, useAuthStore } from './authStore'

export const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshPromise: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  // Si ya hay una renovación en curso, todas las peticiones que lleguen mientras
  // esperan comparten la misma promesa en vez de disparar refresh en paralelo.
  if (!refreshPromise) {
    // El refresh token va en una cookie HttpOnly: el navegador la manda sola. Una sesión abierta
    // antes de ese cambio aún lo tiene en localStorage: se envía una última vez para migrarla
    // (el servidor responde con la cookie nueva) y se borra.
    const legacy = localStorage.getItem(LEGACY_REFRESH_STORAGE_KEY)
    refreshPromise = axios
      .post('/api/auth/refresh', legacy ? { refresh_token: legacy } : undefined)
      .then(({ data }) => {
        localStorage.removeItem(LEGACY_REFRESH_STORAGE_KEY)
        useAuthStore.getState().setToken(data.access_token)
        return data.access_token as string
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    // Con login/refresh un 401 es la respuesta real (clave mala / sesión vencida), no un token por renovar.
    const isAuthCall = /\/auth\/(login|refresh)$/.test(original?.url ?? '')
    if (error.response?.status === 401 && !original?._retry && !isAuthCall && useAuthStore.getState().token) {
      original._retry = true
      try {
        const newToken = await refreshAccessToken()
        original.headers.Authorization = `Bearer ${newToken}`
        return api(original)
      } catch {
        useAuthStore.getState().logout()
        return Promise.reject(error)
      }
    }
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
    }
    return Promise.reject(error)
  },
)

export async function downloadFile(path: string, filename: string) {
  const response = await api.get(path, { responseType: 'blob' })
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export async function viewFile(path: string) {
  // window.open debe llamarse sincrónicamente dentro del gesto del usuario (el click) o
  // el navegador lo trata como popup no solicitado y abre una pestaña en blanco — por eso
  // se abre primero y se navega después de que llegue el blob, en vez de esperar el await
  // y abrir recién con la URL final ya resuelta.
  const newWindow = window.open('', '_blank')
  const response = await api.get(path, { responseType: 'blob' })
  const url = URL.createObjectURL(response.data)
  if (newWindow) {
    newWindow.location.href = url
  } else {
    window.open(url, '_blank')
  }
}

export async function logout() {
  try {
    // El servidor lee el refresh token de la cookie, la revoca y la borra.
    const legacy = localStorage.getItem(LEGACY_REFRESH_STORAGE_KEY)
    await api.post('/auth/logout', legacy ? { refresh_token: legacy } : undefined, { _retry: true } as object)
  } catch {
    // si falla la llamada (red, token ya vencido, etc.) igual limpiamos la sesión local
  }
  useAuthStore.getState().logout()
}

/** Texto legible de un error del servidor. `detail` es un texto en los errores de negocio, pero una
 * lista de objetos en los de validación (422): pintar esa lista directamente rompe la pantalla. */
export function apiErrorMessage(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (item && typeof (item as { msg?: unknown }).msg === 'string' ? (item as { msg: string }).msg : null))
      .filter((m): m is string => m !== null)
    if (messages.length) return messages.join('. ')
  }
  return fallback
}
