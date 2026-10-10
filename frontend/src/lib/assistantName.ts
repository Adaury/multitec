import type { CurrentUser } from './types'

/** Cómo llama el asistente de IA al usuario: el nombre que configuró en su perfil
 * ("Ing. Pérez") o, si no puso ninguno, "Ing." + su primer nombre. */
export function assistantCallName(user: Pick<CurrentUser, 'name' | 'assistant_alias'> | null | undefined): string {
  const alias = user?.assistant_alias?.trim()
  if (alias) return alias
  const first = user?.name?.trim().split(/\s+/)[0]
  return first ? `Ing. ${first}` : 'Ing.'
}
