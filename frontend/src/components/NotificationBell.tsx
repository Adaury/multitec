import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { AppNotification } from '../lib/types'
import { IconButton } from './ui'

function timeAgo(iso: string): string {
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (seconds < 60) return 'ahora'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `hace ${minutes} min`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `hace ${hours} h`
  const days = Math.floor(hours / 24)
  return `hace ${days} d`
}

export function NotificationBell() {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  const { data: unread } = useQuery({
    queryKey: ['notifications', 'unread-count'],
    queryFn: async () => (await api.get<{ count: number }>('/notifications/unread-count')).data,
    refetchInterval: 30000,
  })

  const { data: notifications } = useQuery({
    queryKey: ['notifications'],
    queryFn: async () => (await api.get<AppNotification[]>('/notifications')).data,
    enabled: open,
  })

  const markRead = useMutation({
    mutationFn: async (id: number) => (await api.put(`/notifications/${id}/read`)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['notifications', 'unread-count'] })
    },
  })

  const markAllRead = useMutation({
    mutationFn: async () => (await api.post('/notifications/read-all')).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      queryClient.invalidateQueries({ queryKey: ['notifications', 'unread-count'] })
    },
  })

  function handleClick(notification: AppNotification) {
    if (!notification.read) markRead.mutate(notification.id)
    if (notification.link) {
      navigate(notification.link)
      setOpen(false)
    }
  }

  const count = unread?.count ?? 0

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <IconButton aria-label="Notificaciones" onClick={() => setOpen((v) => !v)}>
          🔔
        </IconButton>
        {count > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold text-white">
            {count > 9 ? '9+' : count}
          </span>
        )}
      </div>

      {open && (
        <div className="absolute right-0 top-0 z-20 w-72 rounded-2xl bg-white p-3 shadow-lg ring-1 ring-black/5">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm font-medium text-gray-800">Notificaciones</p>
            {count > 0 && (
              <button
                onClick={() => markAllRead.mutate()}
                className="text-xs font-medium text-brand-blue"
              >
                Marcar todas leídas
              </button>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto">
            {notifications?.map((n) => (
              <button
                key={n.id}
                onClick={() => handleClick(n)}
                className={`block w-full rounded-xl px-2 py-2 text-left text-sm hover:bg-brand-gray ${
                  n.read ? 'text-gray-500' : 'text-gray-900'
                }`}
              >
                <div className="flex items-start gap-2">
                  {!n.read && <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-brand-blue" />}
                  <div className={n.read ? '' : 'flex-1'}>
                    <p className="font-medium">{n.title}</p>
                    <p className="text-xs text-gray-400">{timeAgo(n.created_at)}</p>
                  </div>
                </div>
              </button>
            ))}
            {notifications?.length === 0 && (
              <p className="px-2 py-2 text-xs text-gray-400">Aún no tienes notificaciones.</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
