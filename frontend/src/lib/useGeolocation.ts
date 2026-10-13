import { useCallback, useEffect, useRef, useState } from 'react'
import { mapsPointUrl } from './maps'

/** Qué tocar para volver a dar el permiso: en el teléfono no es obvio y sin esto el técnico se
 * queda atascado. Mientras tanto siempre puede escribir la dirección o pegar un enlace. */
function deniedHelp(): string {
  const ua = navigator.userAgent
  if (/iPhone|iPad|iPod/.test(ua)) {
    return (
      'Ubicación bloqueada. En el iPhone: toca "aA" (o el ícono a la izquierda de la dirección) → ' +
      'Configuración del sitio web → Ubicación → Permitir. Si no aparece: Ajustes → Privacidad → ' +
      'Localización → Sitios web de Safari → Al usar la app. Luego toca "Usar mi ubicación actual". ' +
      'También puedes escribir la dirección.'
    )
  }
  if (/Android/.test(ua)) {
    return (
      'Ubicación bloqueada. Toca el candado junto a la dirección → Permisos → Ubicación → Permitir, ' +
      'y luego "Usar mi ubicación actual". También puedes escribir la dirección.'
    )
  }
  return 'Ubicación bloqueada. Actívala en el candado junto a la dirección del navegador, o escribe la dirección.'
}

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
            ? deniedHelp()
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
