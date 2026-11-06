import { test, expect, login, unique } from './fixtures'

// Con su propia cuenta (una empresa recién registrada) para no cerrar la sesión que comparten las demás pruebas.
test.use({ storageState: { cookies: [], origins: [] } })

test('logging out returns to the login screen with a confirmation that disappears on reload', async ({ page }) => {
  const email = `${unique('salir').toLowerCase().replace(/[^a-z0-9]/g, '')}@e2e.com`
  const password = 'Salir-Prueba-2026'
  const res = await page.request.post('/api/signup', {
    data: { company_name: unique('Empresa Salir'), admin_name: 'Rosa Salir', email, phone: '809-555-0303', password, accept_terms: true },
  })
  expect(res.ok(), await res.text()).toBeTruthy()

  await login(page, email, password)
  await page.getByRole('button', { name: 'Salir' }).filter({ visible: true }).first().click()
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByText('Cerraste sesión. Vuelve a entrar cuando quieras.')).toBeVisible()

  // El aviso es de una sola vez; una clave mala tampoco lo convierte en «sesión terminada».
  await page.reload()
  await expect(page.getByText('Cerraste sesión')).toHaveCount(0)
  await page.fill('input[type="email"]', email)
  await page.fill('input[type="password"]', 'clave-equivocada-123')
  await page.click('button[type="submit"]')
  await expect(page.getByText('Correo o contraseña incorrectos')).toBeVisible()
  await page.reload()
  await expect(page.getByText('Tu sesión terminó')).toHaveCount(0)
})
