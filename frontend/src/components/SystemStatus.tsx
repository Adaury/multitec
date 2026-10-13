import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { useOnline } from '../lib/useOnline'

interface SystemStatusData {
  overall: 'ok' | 'degraded' | 'down'
  database: boolean
  ai: { reachable: boolean; model: string; installed: boolean; warm: boolean }
  voice_loaded: boolean
}

type Level = 'ok' | 'warn' | 'bad'

const DOT: Record<Level, string> = {
  ok: 'bg-emerald-500',
  warn: 'bg-amber-500',
  bad: 'bg-red-500',
}

function Row({ label, level, text }: { label: string; level: Level; text: string }) {
  return (
    <div className="flex items-center justify-between gap-3 text-sm">
      <span className="text-gray-600 dark:text-gray-300">{label}</span>
      <span className="flex items-center gap-2 font-medium text-gray-900 dark:text-gray-100">
        <span className={`h-2.5 w-2.5 rounded-full ${DOT[level]}`} />
        {text}
      </span>
    </div>
  )
}

/** Indicador de estado en el encabezado: un punto de color que dice si el sistema está listo. Al
 * tocarlo explica qué falla (sin conexión, sin base de datos, IA apagada o fría). Es lo que le
 * dice al técnico POR QUÉ algo tarda, en vez de dejarlo adivinando. */
export function SystemStatus() {
  const online = useOnline()
  const [open, setOpen] = useState(false)
  const { data, isError, error } = useQuery({
    queryKey: ['system', 'status'],
    queryFn: async () => (await api.get<SystemStatusData>('/system/status')).data,
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,
    retry: false,
  })

  // 403 = contraseña temporal sin cambiar: el servidor responde, solo que aún no deja ver nada.
  // No es una caída y no debe pintarse en rojo.
  const forbidden = (error as { response?: { status?: number } } | null)?.response?.status === 403
  if (forbidden && online) return null

  const unreachable = !online || isError
  let level: Level = 'ok'
  let summary = 'Todo listo'
  if (unreachable) {
    level = 'bad'
    summary = online ? 'Sin conexión con el servidor' : 'Sin conexión a internet'
  } else if (data?.overall === 'down') {
    level = 'bad'
    summary = 'La base de datos no responde'
  } else if (data?.overall === 'degraded') {
    level = 'warn'
    summary = 'La IA no está disponible: puedes trabajar a mano'
  } else if (data && !data.ai.warm) {
    summary = 'Listo (la primera respuesta de la IA tarda un poco)'
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={`Estado del sistema: ${summary}`}
        aria-expanded={open}
        className="flex h-10 w-10 items-center justify-center rounded-full bg-white shadow-sm ring-1 ring-black/5 dark:bg-gray-900 dark:ring-white/10"
      >
        <span className={`h-3 w-3 rounded-full ${DOT[level]}`} />
      </button>
      {open && (
        <div
          role="status"
          className="absolute right-0 top-12 z-20 w-72 space-y-2 rounded-2xl bg-white p-4 shadow-lg ring-1 ring-black/10 dark:bg-gray-900 dark:ring-white/10"
        >
          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{summary}</p>
          {data && !unreachable && (
            <div className="space-y-1.5">
              <Row label="Servidor" level="ok" text="Conectado" />
              <Row
                label="Base de datos"
                level={data.database ? 'ok' : 'bad'}
                text={data.database ? 'Lista' : 'No responde'}
              />
              <Row
                label="IA de texto"
                level={data.ai.reachable && data.ai.installed ? 'ok' : 'warn'}
                text={
                  !data.ai.reachable
                    ? 'Apagada'
                    : !data.ai.installed
                      ? 'Sin el modelo'
                      : data.ai.warm
                        ? 'Lista'
                        : 'Fría (tarda ~15 s)'
                }
              />
              <Row
                label="Voz"
                level="ok"
                text={data.voice_loaded ? 'Lista' : 'Se carga al primer dictado'}
              />
            </div>
          )}
          {unreachable && (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Lo que captures en un levantamiento se guarda en el teléfono y se envía solo cuando vuelva la conexión.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
