import { chromium, type FullConfig } from '@playwright/test'
import { ADMIN_EMAIL, ADMIN_PASSWORD, STORAGE_STATE_PATH } from './fixtures'

/**
 * Inicia sesión una sola vez para toda la corrida y guarda el estado (localStorage con
 * los tokens) en disco. Evita que cada spec haga su propio login — con 10+ specs eso
 * agotaría el rate limit de /api/auth/login (10/min) que agregamos a propósito.
 */
export default async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0].use.baseURL ?? 'http://localhost:5173'
  const browser = await chromium.launch()
  const page = await browser.newPage()

  await page.goto(baseURL)
  await page.fill('input[type="email"]', ADMIN_EMAIL)
  await page.fill('input[type="password"]', ADMIN_PASSWORD)
  await page.click('button[type="submit"]')
  await page.waitForSelector('h1:has-text("Acciones rápidas")', { timeout: 15000 })

  await page.context().storageState({ path: STORAGE_STATE_PATH })
  await browser.close()
}
