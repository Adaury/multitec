import os from 'node:os'
import path from 'node:path'

/**
 * Modo aislado (por defecto en local): Playwright levanta su PROPIO backend (puerto 8100,
 * SQLite temporal) y su propio Vite (puerto 5174), así que los tests nunca escriben en la
 * base real de desarrollo. Se desactiva cuando:
 *  - CI está definido (el workflow ya levanta sus propios servidores), o
 *  - E2E_BASE_URL está definido (el usuario apunta a un servidor concreto a propósito).
 */
export const ISOLATED = !process.env.CI && !process.env.E2E_BASE_URL

export const E2E_API_PORT = 8100
// Lejos de 5173/5174: Vite salta solo al siguiente puerto libre cuando el suyo está ocupado,
// así que un dev server "de más" suele terminar en 5174.
export const E2E_WEB_PORT = 5190
export const E2E_TMP_DIR = path.join(os.tmpdir(), 'multitec-e2e')

// Contraseña desechable de la base temporal; no es la de ningún entorno real.
export const E2E_DEFAULT_ADMIN_PASSWORD = 'e2e-admin-password'
