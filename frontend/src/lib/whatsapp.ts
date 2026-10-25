/** Teléfono dominicano de 10 dígitos (o 11 con el 1) → enlace de WhatsApp (wa.me), con un mensaje ya escrito
 * si se da. Devuelve null si el número no se puede usar. */
export function whatsappUrl(phone: string | null | undefined, message?: string): string | null {
  const digits = (phone ?? '').replace(/\D/g, '')
  let base: string | null = null
  if (digits.length === 10) base = `https://wa.me/1${digits}`
  else if (digits.length === 11 && digits.startsWith('1')) base = `https://wa.me/${digits}`
  if (!base) return null
  return message ? `${base}?text=${encodeURIComponent(message)}` : base
}

/** "martes 12 de noviembre" a partir de AAAA-MM-DD, sin que la zona horaria lo corra un día. */
export function longDate(iso: string): string {
  return new Date(`${iso}T12:00:00`).toLocaleDateString('es-DO', { weekday: 'long', day: 'numeric', month: 'long' })
}
