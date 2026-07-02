import { create } from 'zustand'
import type { CurrentUser } from './types'

interface AuthState {
  token: string | null
  user: CurrentUser | null
  setSession: (token: string, user: CurrentUser) => void
  setUser: (user: CurrentUser) => void
  logout: () => void
}

const STORAGE_KEY = 'multitec_token'

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem(STORAGE_KEY),
  user: null,
  setSession: (token, user) => {
    localStorage.setItem(STORAGE_KEY, token)
    set({ token, user })
  },
  setUser: (user) => set({ user }),
  logout: () => {
    localStorage.removeItem(STORAGE_KEY)
    set({ token: null, user: null })
  },
}))
