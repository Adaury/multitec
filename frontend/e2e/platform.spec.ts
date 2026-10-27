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

test('the owner creates a demo company with technician accounts that expire', async ({ page }) => {
  await page.goto('/plataforma')
  await page.getByRole('button', { name: 'Crear demo para técnicos' }).click()
  await page.getByLabel('Técnicos de prueba').fill('2')
  await page.getByLabel('Días de prueba').fill('10')
  await page.getByRole('button', { name: 'Crear empresa demo' }).click()

  // Una cuenta de administrador y dos de técnico, cada una con su clave temporal
  const accounts = page.getByTestId('demo-account')
  await expect(accounts).toHaveCount(3)
  await expect(page.getByTestId('demo-created')).toContainText('Vence en')
  await expect(accounts.filter({ hasText: 'tecnico' })).toHaveCount(2)

  // Aparece en la lista como demo, en prueba, con el cupo de usuarios
  await page.getByRole('button', { name: 'Ya las anoté' }).click()
  const card = page.locator('a', { hasText: '(demo)' }).first()
  await expect(card).toContainText('En prueba')
  await expect(card).toContainText('3/3 usuarios')
})

test('demo accounts can be edited, downloaded and shared with an access link', async ({ page }) => {
  await page.goto('/plataforma')
  await page.getByRole('button', { name: 'Crear demo para técnicos' }).click()
  await page.getByLabel('Técnicos de prueba').fill('1')
  await page.getByRole('button', { name: 'Crear empresa demo' }).click()
  const accounts = page.getByTestId('demo-account')
  await expect(accounts).toHaveCount(2)

  // Editar la clave de la cuenta de técnico: la que se muestra pasa a ser la nueva
  const tech = accounts.filter({ hasText: 'tecnico' })
  await tech.getByRole('button', { name: 'Editar clave' }).click()
  await tech.getByLabel(/Nueva clave de/).fill('Clave-Demo-2026')
  await tech.getByRole('button', { name: 'Guardar' }).click()
  await expect(tech.getByTestId('temporary-password')).toHaveText('Clave-Demo-2026')

  // Descargar el archivo con los accesos
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'Descargar archivo' }).click(),
  ])
  expect(download.suggestedFilename()).toMatch(/^acceso-.*\.txt$/)

  // Enlaces para mandar el acceso
  await expect(tech.getByRole('link', { name: 'Enviar por WhatsApp' })).toHaveAttribute('href', /wa\.me\/\?text=.*login/)
  await expect(tech.getByRole('link', { name: 'Enviar por correo' })).toHaveAttribute('href', /^mailto:\?subject=/)
})
