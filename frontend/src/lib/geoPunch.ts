/** Posición GPS para marcar entrada o salida de una visita. Nunca bloquea ni falla: si el navegador no la da (sin
 * HTTPS, permiso negado, sin señal o tarda demasiado), devuelve null y la hora se guarda igual. Solo se pide al
 * tocar el botón: no hay seguimiento continuo del técnico. */
export function getPosition(timeoutMs = 8000): Promise<{ lat: number; lng: number } | null> {
  return new Promise((resolve) => {
    if (typeof navigator === 'undefined' || !window.isSecureContext || !navigator.geolocation) {
      resolve(null)
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => resolve(null),
      { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 60_000 },
    )
  })
}

/** "2 h 15 min" a partir de minutos. */
export function formatMinutes(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h === 0) return `${m} min`
  return m === 0 ? `${h} h` : `${h} h ${m} min`
}
