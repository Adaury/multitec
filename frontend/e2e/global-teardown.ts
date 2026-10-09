import fs from 'node:fs'
import { E2E_TMP_DIR, ISOLATED } from './isolated'

/** Borra la base y los uploads temporales del modo aislado. En Windows el archivo SQLite
 * puede seguir bloqueado porque Playwright apaga el backend después del teardown; en ese
 * caso no pasa nada: start-backend.mjs limpia la carpeta al arrancar la próxima corrida. */
export default async function globalTeardown() {
  if (!ISOLATED) return
  try {
    fs.rmSync(E2E_TMP_DIR, { recursive: true, force: true })
  } catch {
    // Se limpia en la próxima corrida.
  }
}
