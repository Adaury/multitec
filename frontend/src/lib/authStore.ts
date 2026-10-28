import { create } from 'zustand'
import type { CurrentUser } from './types'
import { safeStorage } from './safeStorage'

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
  token: safeStorage.get(STORAGE_KEY),
  user: null,
  setSession: (token, user) => {
    safeStorage.set(STORAGE_KEY, token)
    set({ token, user })
  },
  setToken: (token) => {
    safeStorage.set(STORAGE_KEY, token)
    set({ token })
  },
  setUser: (user) => set({ user }),
  logout: () => {
    safeStorage.remove(STORAGE_KEY)
    safeStorage.remove(LEGACY_REFRESH_STORAGE_KEY)
    set({ token: null, user: null })
  },
}))
