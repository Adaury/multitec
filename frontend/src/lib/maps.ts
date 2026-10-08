// Enlaces y vistas de Google Maps SIN la API de pago: solo URLs públicas de Maps
// (direcciones, búsqueda y el embed "output=embed", que no requiere clave).

export interface Place {
  address?: string | null
  location_url?: string | null
}

export interface Coords {
  lat: number
  lng: number
}

const COORD = '(-?\\d{1,3}\\.\\d+)\\s*,\\s*(-?\\d{1,3}\\.\\d+)'
const COORD_PATTERNS = [
  new RegExp(`[?&](?:q|ll|query|destination)=${COORD}`), // ...?q=18.48,-69.93
  new RegExp(`@${COORD}`), //                              .../@18.48,-69.93,17z
  /!3d(-?\d{1,3}\.\d+)!4d(-?\d{1,3}\.\d+)/, //             ...!3d18.48!4d-69.93
]

/** Saca latitud/longitud de un enlace de Maps, si las trae. Los enlaces cortos
 * (maps.app.goo.gl) no las traen — en ese caso devuelve null y se usa el enlace tal cual. */
export function parseCoords(url?: string | null): Coords | null {
  if (!url) return null
  let text = url
  try {
    text = decodeURIComponent(url)
  } catch {
    // enlace con % mal formado: se usa el texto crudo
  }
  for (const pattern of COORD_PATTERNS) {
    const m = text.match(pattern)
    if (m) {
      const lat = Number(m[1])
      const lng = Number(m[2])
      if (Math.abs(lat) <= 90 && Math.abs(lng) <= 180) return { lat, lng }
    }
  }
  return null
}

/** Enlace para navegar hasta el lugar (abre la app de Maps en el celular). */
export function directionsUrl(place: Place): string | null {
  const coords = parseCoords(place.location_url)
  if (coords) {
    return `https://www.google.com/maps/dir/?api=1&destination=${coords.lat},${coords.lng}&travelmode=driving`
  }
  if (place.address?.trim()) {
    return `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(place.address.trim())}&travelmode=driving`
  }
  return place.location_url?.trim() || null
}

/** Enlace para ver el lugar en Maps. */
export function viewUrl(place: Place): string | null {
  const coords = parseCoords(place.location_url)
  if (coords) return `https://www.google.com/maps/search/?api=1&query=${coords.lat},${coords.lng}`
  if (place.address?.trim()) {
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(place.address.trim())}`
  }
  return place.location_url?.trim() || null
}

/** URL del mapa incrustado (iframe). Null si no hay coordenadas ni dirección: un enlace corto
 * de Maps no se puede incrustar sin la API. */
export function embedUrl(place: Place): string | null {
  const coords = parseCoords(place.location_url)
  const query = coords ? `${coords.lat},${coords.lng}` : place.address?.trim()
  return query ? `https://maps.google.com/maps?q=${encodeURIComponent(query)}&z=16&output=embed` : null
}

/** Enlace de Maps a un punto exacto (lo que se guarda al capturar el GPS). */
export function mapsPointUrl(lat: number, lng: number): string {
  return `https://www.google.com/maps?q=${lat.toFixed(6)},${lng.toFixed(6)}`
}

/** Texto que Google Maps entiende como una parada de ruta: coordenadas o dirección. Un enlace
 * corto (maps.app.goo.gl) no sirve como parada — Maps no lo acepta en `waypoints`. */
export function routeQuery(place: Place): string | null {
  const coords = parseCoords(place.location_url)
  if (coords) return `${coords.lat},${coords.lng}`
  return place.address?.trim() || null
}

// La URL de Maps admite un destino + hasta 9 paradas intermedias por enlace.
const MAX_STOPS_PER_LINK = 10

/** Enlaces de Google Maps para recorrer las paradas en orden, partiendo de donde esté el
 * usuario. Con más de 10 paradas se parte en tramos encadenados: cada tramo arranca en la
 * última parada del anterior. */
export function routeUrls(stops: string[]): string[] {
  const urls: string[] = []
  for (let start = 0; start < stops.length; start += MAX_STOPS_PER_LINK) {
    const leg = stops.slice(start, start + MAX_STOPS_PER_LINK)
    const params = new URLSearchParams({ api: '1', travelmode: 'driving', destination: leg[leg.length - 1] })
    if (start > 0) params.set('origin', stops[start - 1])
    if (leg.length > 1) params.set('waypoints', leg.slice(0, -1).join('|'))
    urls.push(`https://www.google.com/maps/dir/?${params.toString()}`)
  }
  return urls
}
