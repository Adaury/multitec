import { create } from 'zustand'

export interface Toast {
  id: number
  text: string
}

interface ToastState {
  toasts: Toast[]
  push: (text: string) => void
  dismiss: (id: number) => void
}

let nextId = 1
const AUTO_DISMISS_MS = 7000
const MAX_VISIBLE = 3

/** Avisos cortos de error que no pertenecen a ninguna pantalla (ver queryClient: una acción que falla sin que su pantalla
 * lo cuente). Un mismo texto seguido no se repite. */
export const useToastStore = create<ToastState>((set, get) => ({
  toasts: [],
  push: (text) => {
    if (get().toasts.some((t) => t.text === text)) return
    const id = nextId++
    set((s) => ({ toasts: [...s.toasts, { id, text }].slice(-MAX_VISIBLE) }))
    setTimeout(() => get().dismiss(id), AUTO_DISMISS_MS)
  },
  dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}))
