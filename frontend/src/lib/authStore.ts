import { create } from 'zustand'
import type { CurrentUser } from './types'

interface AuthState {
  token: string | null
  refreshToken: string | null
  user: CurrentUser | null
  setSession: (token: string, refreshToken: string, user: CurrentUser) => void
  setAccessToken: (token: string) => void
  setUser: (user: CurrentUser) => void
  logout: () => void
}

const STORAGE_KEY = 'multitec_token'
const REFRESH_STORAGE_KEY = 'multitec_refresh_token'

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem(STORAGE_KEY),
  refreshToken: localStorage.getItem(REFRESH_STORAGE_KEY),
  user: null,
  setSession: (token, refreshToken, user) => {
    localStorage.setItem(STORAGE_KEY, token)
    localStorage.setItem(REFRESH_STORAGE_KEY, refreshToken)
    set({ token, refreshToken, user })
  },
  setAccessToken: (token) => {
    localStorage.setItem(STORAGE_KEY, token)
    set({ token })
  },
  setUser: (user) => set({ user }),
  logout: () => {
    localStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem(REFRESH_STORAGE_KEY)
    set({ token: null, refreshToken: null, user: null })
  },
}))
