export const ITBIS_RATE = 0.18

/** Fecha local como AAAA-MM-DD. `toISOString()` da la fecha en UTC: en República Dominicana (UTC-4) pasadas
 * las 8 pm ya es "mañana", y el calendario o la fecha de una factura quedaban un día adelantados. */
export function localISODate(date: Date = new Date()): string {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

export function formatDOP(value: number): string {
  return `RD$ ${value.toLocaleString('es-DO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}
