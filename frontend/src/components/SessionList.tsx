import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Smartphone } from 'lucide-react'
import { api, apiErrorMessage } from '../lib/api'
import type { AppSession } from '../lib/types'
import { describeDevice, timeAgo } from '../lib/userAgent'
import { Badge, Button } from './ui'

/** Dispositivos con la sesión abierta. Sirve para el propio usuario (`/auth/sessions`) y para que el admin vea
 * las de otra persona (`/users/{id}/sessions`). Cerrar una sesión la saca de ese dispositivo en el acto. */
export function SessionList({
  listPath,
  closeOne,
  closeAll,
  closeAllLabel,
  onClosedAll,
}: {
  listPath: string
  /** Cerrar una sola sesión; si no se da, no se ofrece (el propio usuario solo cierra todas). */
  closeOne?: (sessionId: number) => Promise<unknown>
  closeAll: () => Promise<unknown>
  closeAllLabel: string
  onClosedAll?: () => void
}) {
  const queryClient = useQueryClient()
  const { data: sessions, isLoading } = useQuery({
    queryKey: ['sessions', listPath],
    queryFn: async () => (await api.get<AppSession[]>(listPath)).data,
  })

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['sessions', listPath] })
  const one = useMutation({ mutationFn: (id: number) => closeOne!(id), onSuccess: refresh })
  const all = useMutation({
    mutationFn: closeAll,
    onSuccess: () => {
      refresh()
      onClosedAll?.()
    },
  })

  return (
    <div className="space-y-2">
      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}
      {sessions?.length === 0 && <p className="text-sm text-gray-500">No hay sesiones abiertas.</p>}
      <ul className="space-y-2">
        {sessions?.map((s) => (
          <li
            key={s.id}
            className="flex items-center gap-3 rounded-xl bg-brand-gray px-3 py-2 text-sm dark:bg-gray-800"
          >
            <Smartphone className="h-5 w-5 shrink-0 text-gray-500" aria-hidden="true" />
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium text-gray-900 dark:text-gray-100">
                {describeDevice(s.user_agent)} {s.current && <Badge tone="green">Este dispositivo</Badge>}
              </p>
              <p className="truncate text-xs text-gray-500 dark:text-gray-400">
                Última vez {timeAgo(s.last_used_at ?? s.created_at)}
                {s.ip ? ` · ${s.ip}` : ''}
              </p>
            </div>
            {closeOne && (
              <button
                onClick={() => one.mutate(s.id)}
                disabled={one.isPending}
                className="shrink-0 rounded-full bg-white px-3 py-1.5 text-xs font-medium text-red-600 dark:bg-gray-900 dark:text-red-400"
              >
                Cerrar
              </button>
            )}
          </li>
        ))}
      </ul>
      {(one.isError || all.isError) && (
        <p className="text-sm text-red-600 dark:text-red-400">
          {apiErrorMessage(one.error ?? all.error, 'No se pudo cerrar la sesión')}
        </p>
      )}
      {sessions && sessions.length > 0 && (
        <Button
          variant="secondary"
          className="!w-auto px-4"
          onClick={() => {
            if (window.confirm(`${closeAllLabel}\n\nTendrán que volver a iniciar sesión.`)) all.mutate()
          }}
          disabled={all.isPending}
        >
          {closeAllLabel}
        </Button>
      )}
    </div>
  )
}
