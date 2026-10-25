import { test, expect, unique } from './fixtures'
import { apiClient } from './helpers'

test('admin fills in a team member profile, resets the password and reviews sessions', async ({ page }) => {
  const email = `${unique('equipo').replace(/\s+/g, '.').toLowerCase()}@multitec.com`

  await page.goto('/usuarios')
  await page.click('button:has-text("+ Nuevo")')
  await page.locator('label:has-text("Nombre") input').fill('Luis Técnico')
  await page.locator('label:has-text("Correo") input').fill(email)
  await page.locator('label:has-text("Contraseña") input').fill('Tornillo-azul-47')
  await page.locator('label:has-text("Rol") select').selectOption('tecnico')
  await page.locator('label:has-text("Teléfono") input').fill('809-555-0100')
  await page.locator('label:has-text("Zona que cubre") input').fill('Moca y Cibao')
  await page.locator('label:has-text("Especialidades") input').fill('CCTV, redes')
  await page.click('button:has-text("Crear usuario")')

  const card = page.locator('div.rounded-3xl', { hasText: email })
  await expect(card).toBeVisible({ timeout: 10000 })
  await expect(card.getByText('Zona: Moca y Cibao')).toBeVisible()
  await expect(card.getByText('Especialidades: CCTV, redes')).toBeVisible()
  await expect(card.getByText('Último acceso: nunca')).toBeVisible()

  // Restablecer la clave: se muestra una vez y obliga a cambiarla.
  page.once('dialog', (dialog) => dialog.accept())
  await card.getByRole('button', { name: 'Restablecer clave' }).click()
  const banner = card.getByRole('status')
  await expect(banner).toContainText('Clave temporal de Luis Técnico')
  await expect(banner).toContainText('no se vuelve a mostrar')

  // Sesiones: aún no ha entrado nadie con esa cuenta.
  await card.getByRole('button', { name: 'Sesiones' }).click()
  await expect(card.getByText('No hay sesiones abiertas.')).toBeVisible()
})

test('the audit log shows who did what and can be filtered', async ({ page }) => {
  await page.goto('/auditoria')
  await expect(page.getByRole('heading', { name: 'Auditoría' })).toBeVisible()
  // Las filas son <p>: el mismo texto también existe como <option> (oculta) en el filtro.
  const created = page.locator('p', { hasText: /^Usuario creado$/ })
  await expect(created.first()).toBeVisible({ timeout: 10000 })

  await page.getByLabel('Filtrar por acción').selectOption('user_created')
  await expect(created.first()).toBeVisible()
  await expect(page.locator('p', { hasText: /^Inició sesión$/ })).toHaveCount(0)
})

test('a technician marks arrival and departure on a visit and the timesheet adds the hours', async ({ page }) => {
  const api = await apiClient(page)
  const client = await api.post('/clients', { name: unique('Cliente visita') })
  const project = await api.post('/projects', { client_id: client.id })
  const today = new Date().toLocaleDateString('en-CA') // AAAA-MM-DD en hora local
  await api.post('/visits', { project_id: project.id, scheduled_date: today, duration_min: 60 })

  await page.goto('/calendario')
  const visit = page.locator('div.rounded-3xl', { hasText: project.code })
  await expect(visit).toBeVisible({ timeout: 10000 })

  await visit.getByRole('button', { name: /Llegué al sitio/ }).click()
  await expect(visit.getByText('En el sitio')).toBeVisible({ timeout: 10000 })
  await expect(visit.getByText(/Llegó a las/)).toBeVisible()

  await visit.getByRole('button', { name: /Terminé la visita/ }).click()
  await expect(visit.getByText('Completada')).toBeVisible({ timeout: 10000 })
  await expect(visit.getByText(/estuvo/)).toBeVisible()

  await page.goto('/hoja-de-tiempo')
  await expect(page.getByRole('heading', { name: 'Hoja de tiempo' })).toBeVisible()
  await expect(page.getByText(project.code).first()).toBeVisible({ timeout: 10000 })
})

test('anyone can review their own sessions from the profile', async ({ page }) => {
  await page.goto('/perfil')
  await expect(page.getByText('Mis sesiones')).toBeVisible()
  await expect(page.getByText('Este dispositivo')).toBeVisible({ timeout: 10000 })
  await expect(page.getByRole('button', { name: 'Cerrar sesión en todos los dispositivos' })).toBeVisible()
})
