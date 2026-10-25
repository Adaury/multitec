/** "iPhone · Safari" a partir del user-agent, para que una persona reconozca sus dispositivos en la lista de
 * sesiones. Es una descripción aproximada: sirve para distinguir, no para identificar. */
export function describeDevice(userAgent: string | null): string {
  if (!userAgent) return 'Dispositivo desconocido'
  const ua = userAgent
  const device = /iPhone/.test(ua)
    ? 'iPhone'
    : /iPad/.test(ua)
      ? 'iPad'
      : /Android/.test(ua)
        ? 'Android'
        : /Windows/.test(ua)
          ? 'Windows'
          : /Macintosh|Mac OS X/.test(ua)
            ? 'Mac'
            : /Linux/.test(ua)
              ? 'Linux'
              : 'Dispositivo'
  const browser = /Edg\//.test(ua)
    ? 'Edge'
    : /CriOS|Chrome\//.test(ua)
      ? 'Chrome'
      : /FxiOS|Firefox\//.test(ua)
        ? 'Firefox'
        : /Safari\//.test(ua)
          ? 'Safari'
          : ''
  return browser ? `${device} · ${browser}` : device
}

/** "hace 5 min", "hace 3 h", "ayer", o la fecha si fue hace más de una semana. */
export function timeAgo(iso: string | null): string {
  if (!iso) return 'nunca'
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  if (seconds < 90) return 'ahora mismo'
  if (seconds < 3600) return `hace ${Math.round(seconds / 60)} min`
  if (seconds < 86_400) return `hace ${Math.round(seconds / 3600)} h`
  if (seconds < 172_800) return 'ayer'
  if (seconds < 604_800) return `hace ${Math.round(seconds / 86_400)} días`
  return new Date(iso).toLocaleDateString('es-DO')
}
