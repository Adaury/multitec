import { directionsUrl, embedUrl, viewUrl, type Place } from '../lib/maps'

/** Mapa de Google incrustado + botones "Cómo llegar" / "Ver en Maps". No renderiza nada si el
 * lugar no tiene ni dirección ni enlace de ubicación. */
export function MapPreview({ place, className = '' }: { place: Place; className?: string }) {
  const embed = embedUrl(place)
  const directions = directionsUrl(place)
  const view = viewUrl(place)
  if (!directions && !view) return null

  const buttonBase = 'flex flex-1 items-center justify-center gap-2 rounded-2xl px-4 py-3 text-sm font-semibold'
  return (
    <div className={`space-y-2 ${className}`}>
      {embed && (
        <div className="relative">
          <iframe
            title="Mapa de la ubicación"
            src={embed}
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
            className="h-48 w-full rounded-2xl border-0 bg-brand-gray dark:bg-gray-800"
          />
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
          <a href={directions} target="_blank" rel="noopener noreferrer" className={`${buttonBase} bg-brand-blue text-white`}>
            🧭 Cómo llegar
          </a>
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
    </div>
  )
}
