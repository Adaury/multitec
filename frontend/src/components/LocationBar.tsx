import { useState } from 'react'
import { Button, Field, Input } from './ui'
import { MapPreview } from './MapPreview'

/** Ubicación en un solo renglón: dice si ya se tomó el GPS y, solo si se toca, despliega el mapa y
 * los campos para corregirla. Plegada ocupa casi nada, así que la pantalla del levantamiento
 * rápido no necesita scroll en el celular. */
export function LocationBar({
  address,
  onAddressChange,
  locationUrl,
  onLocationUrlChange,
  locating,
  note,
  onCapture,
}: {
  address: string
  onAddressChange: (value: string) => void
  locationUrl: string
  onLocationUrlChange: (value: string) => void
  locating: boolean
  /** Mensaje del GPS ("📍 Ubicación capturada (±12 m)" o el motivo del fallo). */
  note: string | null
  onCapture: () => void
}) {
  const [open, setOpen] = useState(false)
  const hasLocation = Boolean(locationUrl.trim())
  const status = locating
    ? '📍 Buscando tu ubicación…'
    : hasLocation
      ? (note ?? '📍 Ubicación lista')
      : (note ?? '📍 Sin ubicación todavía')

  return (
    <div className="rounded-2xl bg-white ring-1 ring-black/5 dark:bg-gray-900 dark:ring-white/10">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left"
      >
        <span className={`truncate text-sm ${hasLocation ? 'text-gray-800 dark:text-gray-100' : 'text-amber-700 dark:text-amber-400'}`}>
          {status}
        </span>
        <span className="shrink-0 text-sm font-medium text-brand-blue">{open ? 'Ocultar ▴' : 'Ver mapa ▾'}</span>
      </button>
      {open && (
        <div className="space-y-3 px-4 pb-4">
          <MapPreview place={{ address, location_url: locationUrl }} />
          <Button variant="secondary" onClick={onCapture} disabled={locating}>
            {locating ? 'Buscando señal GPS…' : hasLocation ? '📍 Actualizar mi ubicación' : '📍 Usar mi ubicación actual'}
          </Button>
          <Field label="Dirección o referencia (opcional)">
            <Input placeholder="Ej. Calle 5 #12, frente al colmado" value={address} onChange={(e) => onAddressChange(e.target.value)} />
          </Field>
          <Field label="Enlace de Google Maps (opcional)">
            <Input
              placeholder="Se llena solo con el GPS, o pega uno"
              value={locationUrl}
              onChange={(e) => onLocationUrlChange(e.target.value)}
            />
          </Field>
        </div>
      )}
    </div>
  )
}
