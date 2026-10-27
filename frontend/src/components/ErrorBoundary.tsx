import { Component, type ErrorInfo, type ReactNode } from 'react'

/** Quita el service worker y la copia guardada de la app (Cache Storage) para que el próximo arranque traiga la
 * versión nueva. NO toca localStorage ni IndexedDB: ahí viven la sesión y los levantamientos sin enviar. */
export async function clearAppCache(): Promise<void> {
  try {
    const registrations = (await navigator.serviceWorker?.getRegistrations?.()) ?? []
    await Promise.all(registrations.map((r) => r.unregister()))
    const keys = (await globalThis.caches?.keys?.()) ?? []
    await Promise.all(keys.map((k) => caches.delete(k)))
  } catch {
    // sin permiso o sin soporte: recargar igual
  }
}

// Una pantalla en blanco no dice nada: si algo se rompe, se muestra qué pasó y cómo salir. Lo más común en el iPhone
// es que el teléfono guardó una versión vieja de la app y ya no coincide con la del servidor.
export class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('La app se detuvo:', error, info.componentStack)
  }

  render() {
    if (!this.state.error) return this.props.children
    const reload = () => window.location.reload()
    const refresh = async () => {
      await clearAppCache()
      window.location.reload()
    }
    return (
      <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center gap-4 p-6 text-center">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Algo salió mal al abrir la app</h1>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Tus datos y levantamientos sin enviar siguen guardados. Prueba recargar; si sigue igual, actualiza la app.
        </p>
        <button onClick={reload} className="rounded-2xl bg-brand-blue px-5 py-4 text-base font-medium text-white">
          Recargar
        </button>
        <button
          onClick={refresh}
          className="rounded-2xl bg-brand-gray px-5 py-4 text-base font-medium text-gray-800 dark:bg-gray-800 dark:text-gray-100"
        >
          Actualizar la app
        </button>
        <pre className="overflow-auto rounded-xl bg-gray-100 p-3 text-left text-xs text-gray-600 dark:bg-gray-900 dark:text-gray-400">
          {this.state.error.message}
        </pre>
      </main>
    )
  }
}
