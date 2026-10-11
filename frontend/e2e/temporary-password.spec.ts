import { test, expect, unique, ADMIN_EMAIL, ADMIN_PASSWORD } from './fixtures'

// Sin la sesión de admin que usa el resto de la suite: aquí entra un usuario nuevo.
test.use({ storageState: { cookies: [], origins: [] } })

test('a user created by an admin must replace the temporary password before using the app', async ({
  page,
  request,
}) => {
  const email = `${unique('temporal').replace(/\s+/g, '.').toLowerCase()}@multitec.com`
  const temporary = 'clave-temporal-1'
  const mine = 'mi-clave-propia-9'

  // El admin crea al usuario por la API.
  const login = await request.post('/api/auth/login', { form: { username: ADMIN_EMAIL, password: ADMIN_PASSWORD } })
  expect(login.ok(), await login.text()).toBeTruthy()
  const adminHeaders = { Authorization: `Bearer ${(await login.json()).access_token}` }
  const created = await request.post('/api/users', {
    headers: adminHeaders,
    data: { name: 'Usuario Temporal', email, password: temporary, role: 'oficina' },
  })
  expect(created.ok(), await created.text()).toBeTruthy()

  // Entra con la contraseña temporal: lo lleva directo al perfil, con el aviso.
  await page.goto('/')
  await page.fill('input[type="email"]', email)
  await page.fill('input[type="password"]', temporary)
  await page.click('button[type="submit"]')
  await expect(page).toHaveURL(/\/perfil$/, { timeout: 15000 })
  await expect(page.getByRole('alert')).toContainText('Tu contraseña es temporal')

  // Intentar ir a otra pantalla lo devuelve al perfil.
  await page.goto('/clientes')
  await expect(page).toHaveURL(/\/perfil$/)

  // Cambia la contraseña y queda libre.
  await page.getByLabel('Contraseña actual').fill(temporary)
  await page.getByLabel('Nueva contraseña (mínimo 8 caracteres)').fill(mine)
  await page.getByLabel('Confirmar nueva contraseña').fill(mine)
  await page.getByRole('button', { name: 'Cambiar contraseña' }).click()
  await expect(page.getByText(/Contraseña actualizada/)).toBeVisible({ timeout: 10000 })
  await expect(page.getByRole('alert')).toHaveCount(0)

  await page.getByRole('link', { name: /Clientes/ }).first().click()
  await expect(page).toHaveURL(/\/clientes/)
  await expect(page.getByRole('heading', { name: 'Clientes' })).toBeVisible()
})
