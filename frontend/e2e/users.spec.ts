import { test, expect, unique } from './fixtures'
import { apiClient } from './helpers'

test('admin creates a user and sees it in the list', async ({ page }) => {
  const email = `${unique('e2e.user').replace(/\s+/g, '.').toLowerCase()}@multitec.com`

  await page.goto('/usuarios')
  await expect(page.getByRole('heading', { name: 'Usuarios' })).toBeVisible()

  await page.click('button:has-text("+ Nuevo")')
  await page.locator('label:has-text("Nombre") input').fill('Usuario E2E')
  await page.locator('label:has-text("Correo") input').fill(email)
  await page.locator('label:has-text("Contraseña") input').fill('claveE2E123')
  await page.locator('label:has-text("Rol") select').selectOption('tecnico')
  await page.click('button:has-text("Crear usuario")')

  await expect(page.getByText(email)).toBeVisible({ timeout: 10000 })
})

test('duplicate email is rejected with a visible error', async ({ page }) => {
  const email = `${unique('dup').replace(/\s+/g, '.').toLowerCase()}@multitec.com`

  await page.goto('/usuarios')
  for (let i = 0; i < 2; i++) {
    await page.click('button:has-text("+ Nuevo")')
    await page.locator('label:has-text("Nombre") input').fill('Usuario Duplicado')
    await page.locator('label:has-text("Correo") input').fill(email)
    await page.locator('label:has-text("Contraseña") input').fill('claveE2E123')
    await page.click('button:has-text("Crear usuario")')
    if (i === 0) {
      await expect(page.getByText(email)).toBeVisible({ timeout: 10000 })
    }
  }

  await expect(page.getByText('Ya existe un usuario con ese correo')).toBeVisible({ timeout: 10000 })
})

test("admin's own role selector is disabled", async ({ page }) => {
  await page.goto('/usuarios')

  const selfCard = page.locator('.rounded-3xl', { hasText: '(tú)' }).first()
  await selfCard.getByRole('button', { name: 'Editar' }).click()
  await expect(page.getByText('No puedes cambiar tu propio rol de administrador.')).toBeVisible()
})

test("admin changes a user's email and a duplicate is rejected without losing the edit panel", async ({ page }) => {
  const mail = (label: string) => `${unique(label).replace(/\s+/g, '.').toLowerCase()}@multitec.com`
  const oldEmail = mail('juan.tecnico')
  const newEmail = mail('frank.santos')
  const otherEmail = mail('otro.usuario')

  const api = await apiClient(page)
  await api.post('/users', { name: 'Juan Tecnico', email: oldEmail, password: 'claveE2E123', role: 'tecnico' })
  await api.post('/users', { name: 'Otro Usuario', email: otherEmail, password: 'claveE2E123', role: 'tecnico' })

  await page.goto('/usuarios')
  const card = (email: string) => page.locator('.rounded-3xl', { hasText: email }).first()

  await card(oldEmail).getByRole('button', { name: 'Editar' }).click()
  await card(oldEmail).getByLabel('Nombre').fill('Frank Santos')
  await card(oldEmail).getByLabel('Correo (con el que entra)').fill(newEmail)
  await card(oldEmail).getByRole('button', { name: 'Guardar cambios' }).click()

  await expect(page.getByText(newEmail)).toBeVisible({ timeout: 10000 })
  await expect(page.getByText(oldEmail)).toHaveCount(0)

  // Un correo que ya usa otra persona se rechaza y el panel sigue abierto para corregirlo.
  await card(otherEmail).getByRole('button', { name: 'Editar' }).click()
  await card(otherEmail).getByLabel('Correo (con el que entra)').fill(newEmail)
  await card(otherEmail).getByRole('button', { name: 'Guardar cambios' }).click()
  await expect(card(otherEmail).getByText('Ya existe un usuario con ese correo')).toBeVisible({ timeout: 10000 })
  await expect(card(otherEmail).getByLabel('Correo (con el que entra)')).toBeVisible()
})
