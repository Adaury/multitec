import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { directionsUrl, embedFromCoords, parseCoords, viewUrl, type Coords, type Place } from '../lib/maps'
import { NavigateMenu } from './NavigateMenu'

/** Mapa incrustado + botones "Cómo llegar" (Google Maps, Waze o Apple Maps) / "Ver en Maps". No renderiza nada si el
 * lugar no tiene ni dirección ni enlace de ubicación.
 *
 * Si el lugar tiene coordenadas el mapa sale de ellas; si solo tiene dirección, el servidor la ubica con OpenStreetMap
 * (/api/geo/search). Con `collapsible` el mapa arranca plegado: solo se ven los botones y un "Ver mapa ▾". En el
 * celular un mapa de 12 rem arriba del todo empujaba el contenido del proyecto fuera de la pantalla. */
export function MapPreview({
  place,
  className = '',
  collapsible = false,
}: {
  place: Place
  className?: string
  collapsible?: boolean
}) {
  const [open, setOpen] = useState(!collapsible)
  const directions = directionsUrl(place)
  const view = viewUrl(place)
  const linkCoords = parseCoords(place.location_url)
  const address = place.address?.trim() ?? ''
  const needsLookup = !linkCoords && address.length >= 5

  const lookup = useQuery({
    queryKey: ['geo', address],
    queryFn: async () => (await api.get<Coords>('/geo/search', { params: { q: address } })).data,
    enabled: needsLookup && open,
    staleTime: Infinity,
    retry: false,
  })
  const coords = linkCoords ?? lookup.data ?? null
  const embed = coords ? embedFromCoords(coords) : null
  if (!directions && !view) return null

  const buttonBase = 'flex flex-1 items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-semibold'
  const showMapArea = (embed || needsLookup) && open
  return (
    <div className={`space-y-2 ${className}`}>
      {showMapArea && (
        <div className="relative">
          {embed ? (
            <iframe
              title="Mapa de la ubicación"
              src={embed}
              referrerPolicy="no-referrer-when-downgrade"
              className="h-48 w-full rounded-2xl border-0 bg-brand-gray dark:bg-gray-800"
            />
          ) : (
            <div className="flex h-48 w-full items-center justify-center rounded-2xl bg-brand-gray px-4 text-center text-sm text-gray-500 dark:bg-gray-800">
              {lookup.isError
                ? 'No pude ubicar esta dirección en el mapa. Usa «Cómo llegar».'
                : 'Ubicando la dirección en el mapa…'}
            </div>
          )}
          {/* Tocar el mapa lo abre en Google Maps. Sirve aunque la vista previa no cargue (queda un
              recuadro gris) y evita que el iframe se coma el scroll de la pantalla en el celular. */}
          {view && (
            <a
              href={view}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Abrir el mapa en Google Maps"
              className="absolute inset-0 rounded-2xl"
            />
          )}
        </div>
      )}
      <div className="flex gap-2">
        {directions && (
          <NavigateMenu place={place} geocoded={lookup.data} className={`${buttonBase} bg-brand-blue text-white`}>
            🧭 Cómo llegar
          </NavigateMenu>
        )}
        {view && (
          <a
            href={view}
            target="_blank"
            rel="noopener noreferrer"
            className={`${buttonBase} bg-brand-gray text-gray-800 dark:bg-gray-800 dark:text-gray-100`}
          >
            📍 Ver en Maps
          </a>
        )}
      </div>
      {collapsible && (embed || needsLookup) && (
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="w-full text-center text-sm font-medium text-brand-blue"
        >
          {open ? 'Ocultar mapa ▴' : 'Ver mapa ▾'}
        </button>
      )}
    </div>
  )
}
