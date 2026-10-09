import { useCallback, useEffect, useRef, useState } from 'react'
import { mapsPointUrl } from './maps'

/** Captura la ubicación GPS del dispositivo y la entrega como enlace de Google Maps. El GPS del
 * navegador solo funciona en HTTPS o localhost; si falla, `note` explica por qué.
 *
 * Con `auto` pide la ubicación apenas se abre la pantalla (una sola vez), sin tocar nada: pensado
 * para el levantamiento en sitio, donde el técnico ya está en la obra. */
export function useGeolocation(onLocation: (mapsUrl: string) => void, options: { auto?: boolean } = {}) {
  const [locating, setLocating] = useState(false)
  const [note, setNote] = useState<string | null>(null)

  const capture = useCallback(() => {
    setNote(null)
    if (!navigator.geolocation) {
      setNote('Este navegador no da la ubicación (requiere HTTPS). Pega un enlace de Google Maps.')
      return
    }
    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        onLocation(mapsPointUrl(pos.coords.latitude, pos.coords.longitude))
        setNote(`📍 Ubicación capturada (±${Math.round(pos.coords.accuracy)} m)`)
        setLocating(false)
      },
      (err) => {
        setNote(
          err.code === err.PERMISSION_DENIED
            ? 'Permiso de ubicación denegado. Actívalo en el navegador o pega un enlace de Google Maps.'
            : 'No se pudo obtener la ubicación. Intenta de nuevo o pega un enlace de Google Maps.',
        )
        setLocating(false)
      },
      { enableHighAccuracy: true, timeout: 20_000, maximumAge: 30_000 },
    )
  }, [onLocation])

  const autoDone = useRef(false)
  useEffect(() => {
    if (options.auto && !autoDone.current) {
      autoDone.current = true
      capture()
    }
  }, [options.auto, capture])

  return { locating, note, capture }
}
