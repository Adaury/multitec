import { create } from 'zustand'
import { safeStorage } from './safeStorage'

type Theme = 'light' | 'dark'

const STORAGE_KEY = 'multitec_theme'

function getInitialTheme(): Theme {
  const stored = safeStorage.get(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark') return stored
  // Modo normal (claro) por defecto; el oscuro solo si la persona lo elige con el botón.
  return 'light'
}

function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark')
}

interface ThemeState {
  theme: Theme
  toggleTheme: () => void
}

const initialTheme = getInitialTheme()
applyTheme(initialTheme)

export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: initialTheme,
  toggleTheme: () => {
    const next: Theme = get().theme === 'dark' ? 'light' : 'dark'
    safeStorage.set(STORAGE_KEY, next)
    applyTheme(next)
    set({ theme: next })
  },
}))
