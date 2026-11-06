/** Precios de la plataforma (planes, instalación, mensualidad) en su moneda: US$40, RD$2,500. */
export function platformMoney(amount: number, currency: string = 'USD', decimals = false): string {
  const prefix = currency === 'DOP' ? 'RD$' : 'US$'
  return `${prefix}${amount.toLocaleString('es-DO', {
    minimumFractionDigits: decimals ? 2 : 0,
    maximumFractionDigits: decimals ? 2 : 0,
  })}`
}

/** Enlace de WhatsApp para un número dominicano escrito como sea (829-283-1336, (809) 555 0101...). */
export function whatsappLink(phone: string, text?: string): string {
  let digits = phone.replace(/\D/g, '')
  if (/^8[024]9\d{7}$/.test(digits)) digits = `1${digits}`
  return `https://wa.me/${digits}${text ? `?text=${encodeURIComponent(text)}` : ''}`
}

export interface SitePlan {
  id: number
  name: string
  description: string | null
  monthly_price: number
  setup_price: number
  max_users: number | null
  features: string[]
  highlighted: boolean
  active: boolean
  sort: number
}

export interface SiteTestimonial {
  id: number
  author: string
  role: string | null
  company: string | null
  quote: string
  rating: number
  published: boolean
  is_example: boolean
  sort: number
  /** "cliente" = lo envió un cliente desde la página pública. */
  source?: 'panel' | 'cliente'
  /** Teléfono o correo de quien lo envió (solo en el panel, nunca en la página). */
  contact?: string | null
}

export interface SitePartner {
  id: number
  name: string
  description: string | null
  url: string | null
  logo_url: string | null
  published: boolean
  sort: number
}

export interface SiteInfo {
  currency: string
  trial_days: number
  signup_enabled: boolean
  phones: string[]
  plans: SitePlan[]
  testimonials: SiteTestimonial[]
  partners: SitePartner[]
}
