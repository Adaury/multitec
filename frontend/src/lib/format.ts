export const ITBIS_RATE = 0.18

export function formatDOP(value: number): string {
  return `RD$ ${value.toLocaleString('es-DO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}
