import axios from 'axios'
import { useAuthStore } from './authStore'

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
  const refreshToken = useAuthStore.getState().refreshToken
  if (!refreshToken) throw new Error('No hay refresh token')

  // Si ya hay una renovación en curso, todas las peticiones que lleguen mientras
  // esperan comparten la misma promesa en vez de disparar refresh en paralelo.
  if (!refreshPromise) {
    refreshPromise = axios
      .post('/api/auth/refresh', { refresh_token: refreshToken })
      .then(({ data }) => {
        useAuthStore.getState().setAccessToken(data.access_token)
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
    if (error.response?.status === 401 && !original?._retry && useAuthStore.getState().refreshToken) {
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

export async function logout() {
  const refreshToken = useAuthStore.getState().refreshToken
  if (refreshToken) {
    try {
      await api.post('/auth/logout', { refresh_token: refreshToken })
    } catch {
      // si falla la llamada (red, token ya vencido, etc.) igual limpiamos la sesión local
    }
  }
  useAuthStore.getState().logout()
}
