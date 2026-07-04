import { test, expect, login, ADMIN_EMAIL } from './fixtures'

// Estos tests prueban el login/logout real, así que arrancan sin sesión — a
// diferencia del resto de la suite, que reusa la sesión de global-setup.ts.
test.use({ storageState: { cookies: [], origins: [] } })

test('login with valid credentials reaches the dashboard', async ({ page }) => {
  await login(page)
  await expect(page.getByRole('heading', { name: 'Acciones rápidas' })).toBeVisible()
})

test('login with wrong password shows an error and stays on the login page', async ({ page }) => {
  await page.goto('/')
  await page.fill('input[type="email"]', ADMIN_EMAIL)
  await page.fill('input[type="password"]', 'contraseña-incorrecta')
  await page.click('button[type="submit"]')
  await expect(page.getByText('Correo o contraseña incorrectos')).toBeVisible()
  await expect(page).toHaveURL(/login/)
})

test('logout revokes the session and redirects to login', async ({ page }) => {
  await login(page)
  const accessBefore = await page.evaluate(() => localStorage.getItem('multitec_token'))
  expect(accessBefore).toBeTruthy()

  // Hay dos botones "Salir" en el DOM (sidebar de escritorio + header móvil, oculto
  // el que no aplica al viewport actual vía CSS) — getByRole solo expone el visible.
  await page.getByRole('button', { name: 'Salir' }).click()
  await expect(page).toHaveURL(/login/, { timeout: 10000 })

  const accessAfter = await page.evaluate(() => localStorage.getItem('multitec_token'))
  expect(accessAfter).toBeNull()
})

test('unauthenticated visitor is redirected to login', async ({ page }) => {
  await page.goto('/proyectos')
  await expect(page).toHaveURL(/login/)
})
