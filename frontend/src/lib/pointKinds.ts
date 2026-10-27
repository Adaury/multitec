/** Tipos de punto que se marcan sobre las fotos del levantamiento. Las claves son las mismas que usa el servidor
 * (backend/app/services/survey_points.py): con ellas la IA cuenta los equipos y cuadra las cantidades de la cotización. */
export const POINT_KINDS = [
  { key: 'camara', label: 'Cámara' },
  { key: 'grabador', label: 'NVR / DVR' },
  { key: 'switch', label: 'Switch' },
  { key: 'gabinete', label: 'Gabinete / rack' },
  { key: 'punto_red', label: 'Punto de red / WiFi' },
  { key: 'acceso', label: 'Cerradura / lector' },
  { key: 'sensor', label: 'Sensor / alarma' },
  { key: 'otro', label: 'Otro' },
] as const

export type PointKind = (typeof POINT_KINDS)[number]['key']

export function pointKindLabel(kind: string): string {
  return POINT_KINDS.find((k) => k.key === kind)?.label ?? 'Otro'
}
