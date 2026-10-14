import { test, expect, unique, ADMIN_EMAIL, ADMIN_PASSWORD } from './fixtures'

// Sin la sesión de admin que usa el resto de la suite: aquí entra un técnico.
test.use({ storageState: { cookies: [], origins: [] } })

test('a technician only sees the sections they can use and is sent home from money pages', async ({
  page,
  request,
}) => {
  const email = `${unique('tecnico').replace(/\s+/g, '.').toLowerCase()}@multitec.com`
  const temporary = 'clave-temporal-1'
  const mine = 'mi-clave-propia-9'

  const adminLogin = await request.post('/api/auth/login', { form: { username: ADMIN_EMAIL, password: ADMIN_PASSWORD } })
  expect(adminLogin.ok(), await adminLogin.text()).toBeTruthy()
  const adminHeaders = { Authorization: `Bearer ${(await adminLogin.json()).access_token}` }
  const created = await request.post('/api/users', {
    headers: adminHeaders,
    data: { name: 'Tecnico de Campo', email, password: temporary, role: 'tecnico' },
  })
  expect(created.ok(), await created.text()).toBeTruthy()

  // Reemplaza la contraseña temporal por la API para entrar directo a la app.
  const tempLogin = await request.post('/api/auth/login', { form: { username: email, password: temporary } })
  const tempHeaders = { Authorization: `Bearer ${(await tempLogin.json()).access_token}` }
  const changed = await request.post('/api/auth/change-password', {
    headers: tempHeaders,
    data: { current_password: temporary, new_password: mine },
  })
  expect(changed.ok(), await changed.text()).toBeTruthy()

  await page.goto('/')
  await page.fill('input[type="email"]', email)
  await page.fill('input[type="password"]', mine)
  await page.click('button[type="submit"]')
  await expect(page).toHaveURL(/\/$/, { timeout: 15000 })

  // Viewport de teléfono: los destinos de uso diario van en la barra inferior y el resto en "Más".
  const tabBar = page.locator('nav.fixed')
  await expect(tabBar.getByRole('link', { name: /Proyectos/ })).toBeVisible()
  await expect(tabBar.getByRole('link', { name: /Clientes/ })).toBeVisible()
  await tabBar.getByRole('button', { name: /Más/ }).click()
  const more = page.getByRole('dialog', { name: 'Más opciones' })
  await expect(more.getByRole('link', { name: /Calendario/ })).toBeVisible()
  await expect(more.getByRole('link', { name: /Preguntar IA/ })).toBeVisible()
  for (const hidden of [/Cotizaciones/, /Catálogo/, /Compras/, /Usuarios/, /NCF/, /Ajustes de IA/]) {
    await expect(more.getByRole('link', { name: hidden })).toHaveCount(0)
  }

  // Escribir la dirección a mano tampoco le abre una pantalla vacía: vuelve al Inicio.
  for (const path of ['/cotizaciones', '/catalogo', '/compras', '/usuarios']) {
    await page.goto(path)
    await expect(page).toHaveURL(/\/$/, { timeout: 10000 })
  }
})
