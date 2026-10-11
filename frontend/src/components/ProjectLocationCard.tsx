import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { useGeolocation } from '../lib/useGeolocation'
import type { ProjectDetail } from '../lib/types'
import { Button, Card, Field, Input } from './ui'
import { MapPreview } from './MapPreview'

/** Ubicación de la obra. Es propia del proyecto (un cliente puede tener varias obras); si el
 * proyecto no tiene, se muestra la del cliente como respaldo. */
export function ProjectLocationCard({ project }: { project: ProjectDetail }) {
  const queryClient = useQueryClient()
  const own = Boolean(project.address || project.location_url)
  const place = {
    address: project.address || project.client.address,
    location_url: project.location_url || project.client.location_url,
  }
  const hasPlace = Boolean(place.address || place.location_url)

  const [editing, setEditing] = useState(false)
  const [address, setAddress] = useState('')
  const [locationUrl, setLocationUrl] = useState('')
  const [error, setError] = useState<string | null>(null)
  const gps = useGeolocation(setLocationUrl)

  function startEditing() {
    setAddress(project.address ?? '')
    setLocationUrl(project.location_url ?? '')
    setError(null)
    setEditing(true)
    // Al agregar la ubicación de una obra que aún no tiene, se pide el GPS directamente. Solo al
    // tocar "Agregar" (nunca al abrir la ficha): quien mira el proyecto desde la oficina no debe
    // sobrescribir la ubicación de la obra con la suya.
    if (!own) gps.capture()
  }

  const save = useMutation({
    mutationFn: async () =>
      (
        await api.put(`/projects/${project.id}`, {
          address: address.trim() || null,
          location_url: locationUrl.trim() || null,
        })
      ).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      queryClient.invalidateQueries({ queryKey: ['visits'] })
      setEditing(false)
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'No se pudo guardar la ubicación')
    },
  })

  return (
    <Card className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <p className="font-medium text-gray-800 dark:text-gray-200">📍 Ubicación de la obra</p>
        {!editing && (
          <button
            onClick={startEditing}
            className="shrink-0 rounded-full bg-brand-gray px-3 py-1 text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300"
          >
            {hasPlace ? 'Editar' : 'Agregar'}
          </button>
        )}
      </div>

      {editing ? (
        <div className="space-y-3">
          <Button variant="secondary" onClick={gps.capture} disabled={gps.locating}>
            {gps.locating ? 'Buscando señal GPS…' : '📍 Usar mi ubicación actual'}
          </Button>
          {gps.note && <p className="text-sm text-gray-600 dark:text-gray-400">{gps.note}</p>}
          <Field label="Dirección o referencia">
            <Input value={address} onChange={(e) => setAddress(e.target.value)} />
          </Field>
          <Field label="Enlace de Google Maps">
            <Input
              placeholder="Se llena con el GPS, o pega uno"
              value={locationUrl}
              onChange={(e) => setLocationUrl(e.target.value)}
            />
          </Field>
          <MapPreview place={{ address, location_url: locationUrl }} />
          {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
          <div className="flex gap-2">
            <Button className="!w-auto flex-1" onClick={() => save.mutate()} disabled={save.isPending}>
              {save.isPending ? 'Guardando…' : 'Guardar'}
            </Button>
            <Button
              className="!w-auto flex-1"
              variant="secondary"
              onClick={() => setEditing(false)}
              disabled={save.isPending}
            >
              Cancelar
            </Button>
          </div>
        </div>
      ) : hasPlace ? (
        <>
          {place.address && <p className="text-sm text-gray-600 dark:text-gray-400">{place.address}</p>}
          {!own && <p className="text-xs text-gray-400">Es la ubicación del cliente; esta obra aún no tiene la suya.</p>}
          <MapPreview place={place} collapsible />
        </>
      ) : (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Aún no hay ubicación. Agrégala para que las visitas tengan "Cómo llegar" y entren en la ruta del día.
        </p>
      )}
    </Card>
  )
}
