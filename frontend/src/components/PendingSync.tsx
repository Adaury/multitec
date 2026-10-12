import { useCallback, useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { listPendingSurveys, onPendingSurveysChange, type PendingSurvey } from '../lib/offlineQueue'
import { syncPendingSurveys } from '../lib/syncPending'
import { useOnline } from '../lib/useOnline'

/** Barra con los levantamientos guardados sin conexión. Los envía solos al volver la señal y deja
 * un botón por si el técnico quiere forzarlo. No ocupa espacio si no hay nada pendiente. */
export function PendingSync() {
  const queryClient = useQueryClient()
  const online = useOnline()
  const [pending, setPending] = useState<PendingSurvey[]>([])
  const [sending, setSending] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setPending(await listPendingSurveys())
    } catch {
      // IndexedDB no disponible (modo privado): no hay cola, y la barra queda oculta.
    }
  }, [])

  const send = useCallback(async () => {
    setSending(true)
    setMessage(null)
    try {
      const result = await syncPendingSurveys()
      if (result.sent > 0) {
        queryClient.invalidateQueries({ queryKey: ['projects'] })
        queryClient.invalidateQueries({ queryKey: ['clients'] })
        setMessage(
          result.sent === 1 ? 'Se envió 1 levantamiento.' : `Se enviaron ${result.sent} levantamientos.`,
        )
      }
      if (result.offline) setMessage('Todavía sin conexión con el servidor.')
    } finally {
      setSending(false)
      void refresh()
    }
  }, [queryClient, refresh])

  useEffect(() => {
    void refresh()
    return onPendingSurveysChange(() => void refresh())
  }, [refresh])

  // Al abrir la app y cada vez que vuelve la señal.
  useEffect(() => {
    if (online) void send()
  }, [online, send])

  if (pending.length === 0 && !message) return null

  const withError = pending.filter((p) => p.lastError)
  return (
    <div
      role="status"
      className="mx-5 mb-2 space-y-1 rounded-2xl bg-amber-50 px-4 py-3 text-sm ring-1 ring-amber-200 md:mx-10 dark:bg-amber-950 dark:ring-amber-900"
    >
      {pending.length > 0 && (
        <div className="flex items-center justify-between gap-3">
          <p className="font-medium text-amber-900 dark:text-amber-200">
            {pending.length === 1
              ? '1 levantamiento guardado sin enviar'
              : `${pending.length} levantamientos guardados sin enviar`}
            {!online && ' · sin conexión'}
          </p>
          <button
            onClick={() => void send()}
            disabled={sending || !online}
            className="shrink-0 rounded-full bg-amber-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
          >
            {sending ? 'Enviando…' : 'Enviar ahora'}
          </button>
        </div>
      )}
      {withError.map((p) => (
        <p key={p.id} className="text-xs text-red-700 dark:text-red-400">
          {p.clientName}: {p.lastError}
        </p>
      ))}
      {message && <p className="text-xs text-amber-800 dark:text-amber-300">{message}</p>}
    </div>
  )
}
