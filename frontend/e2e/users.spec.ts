import { test, expect, unique } from './fixtures'

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
