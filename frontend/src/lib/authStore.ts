import { create } from 'zustand'
import type { CurrentUser } from './types'

interface AuthState {
  token: string | null
  user: CurrentUser | null
  setSession: (token: string, user: CurrentUser) => void
  setToken: (token: string) => void
  setUser: (user: CurrentUser) => void
  logout: () => void
}

const STORAGE_KEY = 'multitec_token'
// Clave antigua: el refresh token ya no vive en localStorage (ahora va en una cookie HttpOnly).
// Se conserva el nombre solo para migrar sesiones abiertas y borrarlo (ver api.ts).
export const LEGACY_REFRESH_STORAGE_KEY = 'multitec_refresh_token'

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem(STORAGE_KEY),
  user: null,
  setSession: (token, user) => {
    localStorage.setItem(STORAGE_KEY, token)
    set({ token, user })
  },
  setToken: (token) => {
    localStorage.setItem(STORAGE_KEY, token)
    set({ token })
  },
  setUser: (user) => set({ user }),
  logout: () => {
    localStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem(LEGACY_REFRESH_STORAGE_KEY)
    set({ token: null, user: null })
  },
}))
