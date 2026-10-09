// Tipos de levantamiento. Es la única fuente de la lista: el backend guarda el texto tal cual
// (Project.survey_type) y recibe esta misma lista al interpretar lo que dicta el usuario.
export const SURVEY_TYPES = [
  'Cámaras de seguridad (CCTV)',
  'Alarma',
  'Control de acceso',
  'Cerco eléctrico',
  'Redes y cableado',
  'Intercomunicador / videoportero',
  'Otro',
] as const

/** Texto de la descripción del proyecto al crearlo desde un levantamiento. */
export function surveyDescription(surveyType: string | null | undefined): string {
  return surveyType ? `Levantamiento · ${surveyType}` : 'Levantamiento en sitio'
}
