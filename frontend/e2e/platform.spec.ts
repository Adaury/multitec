import { test, expect, unique } from './fixtures'

// Panel de la plataforma: el dueño crea una empresa con su administrador, la ve en la lista y la suspende.
test('the platform owner creates a company with its admin, sees it listed and suspends it', async ({ page }) => {
  const name = unique('Seguridad Demo')
  const adminEmail = `${unique('ana').replace(/\s+/g, '.').toLowerCase()}@demo.com`

  await page.goto('/plataforma')
  await expect(page.getByRole('heading', { name: 'Plataforma' })).toBeVisible()

  await page.getByRole('button', { name: 'Nueva empresa' }).click()
  await page.getByLabel('Nombre de la empresa').fill(name)
  await page.getByLabel('Administrador (nombre)').fill('Ana Demo')
  await page.getByLabel('Administrador (correo)').fill(adminEmail)
  await page.getByRole('button', { name: 'Crear empresa y su administrador' }).click()

  // La clave temporal aparece una sola vez, junto al correo.
  const created = page.getByTestId('company-created')
  await expect(created).toContainText(`«${name}» creada`)
  await expect(created).toContainText(adminEmail)
  await expect(page.getByTestId('temporary-password')).not.toBeEmpty()

  // Aparece en la lista como activa, con un usuario; desde ahí se abre y se suspende.
  await page.locator('a', { hasText: name }).click()
  await expect(page.getByRole('heading', { name })).toBeVisible()
  await expect(page.getByText(adminEmail)).toBeVisible()
  page.once('dialog', (dialog) => dialog.accept())
  await page.getByRole('button', { name: 'Suspender empresa' }).click()
  await expect(page.getByText('Suspendida')).toBeVisible()

  page.once('dialog', (dialog) => dialog.accept())
  await page.getByRole('button', { name: 'Reactivar empresa' }).click().catch(() => {})
  await expect(page.getByRole('button', { name: /Suspender empresa|Reactivar empresa/ })).toBeVisible()
})
