import { useRef, useState, type MouseEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { POINT_KINDS, pointKindLabel, type PointKind } from '../lib/pointKinds'
import type { SurveyAsset } from '../lib/types'
import { Button } from './ui'
import { UploadImage } from './UploadMedia'

interface DraftMarker {
  x: number
  y: number
  label: string
  kind: PointKind
}

/** Marca puntos numerados sobre una foto del levantamiento: toca la foto donde irá cada equipo y
 * elige qué es (cámara, NVR, switch...). La numeración es corrida en todo el levantamiento (la
 * reasigna el servidor) y es la que sale en el anexo de la cotización para el cliente. Los puntos,
 * contados por tipo, son los que la IA usa para dar cantidades exactas y precios en la cotización. */
export function PhotoMarkerEditor({
  projectId,
  asset,
  numberOffset,
  onClose,
}: {
  projectId: number
  asset: SurveyAsset
  /** Cuántos marcadores hay en las fotos anteriores: este editor continúa desde ahí. */
  numberOffset: number
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const imageRef = useRef<HTMLImageElement>(null)
  const [markers, setMarkers] = useState<DraftMarker[]>(
    asset.markers.map((m) => ({
      x: m.x,
      y: m.y,
      label: m.label ?? '',
      kind: (POINT_KINDS.some((k) => k.key === m.point_kind) ? m.point_kind : 'otro') as PointKind,
    })),
  )
  // El tipo que se está marcando: cada toque nuevo en la foto crea un punto de este tipo.
  const [currentKind, setCurrentKind] = useState<PointKind>('camara')
  const [error, setError] = useState<string | null>(null)

  const save = useMutation({
    mutationFn: async () =>
      (
        await api.put<SurveyAsset>(`/projects/${projectId}/survey/assets/${asset.id}/markers`, {
          markers: markers.map((m) => ({ x: m.x, y: m.y, label: m.label.trim() || null, kind: m.kind })),
        })
      ).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['survey', projectId] })
      onClose()
    },
    onError: () => setError('No se pudieron guardar los puntos. Intenta de nuevo.'),
  })

  const addMarker = (event: MouseEvent<HTMLDivElement>) => {
    const image = imageRef.current
    if (!image) return
    const rect = image.getBoundingClientRect()
    const x = (event.clientX - rect.left) / rect.width
    const y = (event.clientY - rect.top) / rect.height
    if (x < 0 || x > 1 || y < 0 || y > 1) return
    const sameKind = markers.filter((m) => m.kind === currentKind).length + 1
    setMarkers((prev) => [...prev, { x, y, kind: currentKind, label: `${pointKindLabel(currentKind)} ${sameKind}` }])
  }

  const updateLabel = (index: number, label: string) =>
    setMarkers((prev) => prev.map((m, i) => (i === index ? { ...m, label } : m)))
  const updateKind = (index: number, kind: PointKind) =>
    setMarkers((prev) => prev.map((m, i) => (i === index ? { ...m, kind } : m)))
  const removeMarker = (index: number) => setMarkers((prev) => prev.filter((_, i) => i !== index))

  const summary = POINT_KINDS.map((k) => ({ ...k, count: markers.filter((m) => m.kind === k.key).length })).filter(
    (k) => k.count > 0,
  )

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 md:items-center" role="dialog">
      <div className="max-h-[92vh] w-full max-w-2xl space-y-3 overflow-y-auto rounded-t-3xl bg-white p-4 md:rounded-3xl dark:bg-gray-900">
        <div className="flex items-center justify-between">
          <p className="font-semibold text-gray-900 dark:text-gray-100">Marcar equipos en la foto</p>
          <button className="text-sm text-gray-500" onClick={onClose} aria-label="Cerrar">
            ✕
          </button>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Elige qué vas a marcar y toca la foto donde irá cada equipo. Los números continúan de las fotos anteriores y
          salen en el anexo de la cotización. La IA cuenta estos puntos para dar las cantidades exactas.
        </p>

        <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label="Tipo de punto a marcar">
          {POINT_KINDS.map((k) => (
            <button
              key={k.key}
              type="button"
              role="radio"
              aria-checked={currentKind === k.key}
              onClick={() => setCurrentKind(k.key)}
              className={`rounded-full px-3 py-1.5 text-xs font-medium ${
                currentKind === k.key
                  ? 'bg-brand-blue text-white'
                  : 'bg-brand-gray text-gray-700 dark:bg-gray-800 dark:text-gray-300'
              }`}
            >
              {k.label}
            </button>
          ))}
        </div>

        <div className="relative cursor-crosshair select-none" onClick={addMarker} data-testid="marker-surface">
          <UploadImage
            ref={imageRef}
            filePath={asset.file_path}
            alt="Foto del levantamiento"
            className="block max-h-[55vh] w-full rounded-xl object-contain"
            draggable={false}
          />
          {markers.map((marker, index) => (
            <span
              key={index}
              className="pointer-events-none absolute flex h-7 w-7 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border-2 border-white bg-brand-blue text-xs font-bold text-white shadow"
              style={{ left: `${marker.x * 100}%`, top: `${marker.y * 100}%` }}
            >
              {numberOffset + index + 1}
            </span>
          ))}
        </div>

        {summary.length > 0 && (
          <p className="text-xs font-medium text-gray-600 dark:text-gray-300" data-testid="marker-summary">
            En esta foto: {summary.map((k) => `${k.count} ${k.label.toLowerCase()}`).join(' · ')}
          </p>
        )}

        {markers.length > 0 && (
          <ul className="space-y-2">
            {markers.map((marker, index) => (
              <li key={index} className="flex items-center gap-2">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-blue text-xs font-bold text-white">
                  {numberOffset + index + 1}
                </span>
                <select
                  value={marker.kind}
                  onChange={(e) => updateKind(index, e.target.value as PointKind)}
                  aria-label={`Tipo del punto ${numberOffset + index + 1}`}
                  className="w-32 shrink-0 rounded-xl border border-gray-200 bg-white px-2 py-2 text-sm text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
                >
                  {POINT_KINDS.map((k) => (
                    <option key={k.key} value={k.key}>
                      {k.label}
                    </option>
                  ))}
                </select>
                <input
                  value={marker.label}
                  maxLength={80}
                  onChange={(e) => updateLabel(index, e.target.value)}
                  placeholder="Nombre del punto"
                  className="min-w-0 flex-1 rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
                />
                <button
                  type="button"
                  onClick={() => removeMarker(index)}
                  aria-label={`Quitar punto ${numberOffset + index + 1}`}
                  className="shrink-0 rounded-full bg-brand-gray px-2.5 py-1.5 text-xs text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        )}

        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
        <div className="flex gap-2">
          <Button variant="ghost" className="!w-auto flex-1" onClick={onClose}>
            Cancelar
          </Button>
          <Button className="!w-auto flex-1" onClick={() => save.mutate()} disabled={save.isPending}>
            {save.isPending ? 'Guardando…' : 'Guardar puntos'}
          </Button>
        </div>
      </div>
    </div>
  )
}
