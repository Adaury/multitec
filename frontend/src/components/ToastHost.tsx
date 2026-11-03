import { useToastStore } from '../lib/toastStore'

/** Dibuja los avisos de error. Va sobre la barra inferior del teléfono y sin tapar toques fuera de ellos. */
export function ToastHost() {
  const toasts = useToastStore((s) => s.toasts)
  const dismiss = useToastStore((s) => s.dismiss)
  if (toasts.length === 0) return null
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-28 z-[90] flex flex-col items-center gap-2 px-4 md:bottom-6">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="alert"
          className="pointer-events-auto flex max-w-md items-start gap-3 rounded-2xl bg-red-600 px-4 py-3 text-sm font-medium text-white shadow-lg"
        >
          <span className="flex-1">{toast.text}</span>
          <button
            type="button"
            onClick={() => dismiss(toast.id)}
            aria-label="Cerrar aviso"
            className="shrink-0 rounded-full px-2 text-base leading-none text-white/90"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  )
}
