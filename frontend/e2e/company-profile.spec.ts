import { test, expect } from './fixtures'
import { makePng } from './helpers'

test('edit the company details and replace or remove the logo', async ({ page }) => {
  await page.goto('/empresa')
  await expect(page.getByRole('heading', { name: 'Mi empresa' })).toBeVisible()

  // Datos del membrete.
  await page.getByLabel('Nombre de la empresa').fill('Multitec E2E')
  await page.getByLabel('Lema (opcional)').fill('Servicios de calidad')
  await page.getByRole('button', { name: 'Guardar datos' }).click()
  await expect(page.getByRole('status')).toContainText('Datos guardados')

  // Logo: subirlo, verlo y quitarlo.
  await page.getByLabel('Archivo del logo').setInputFiles({
    name: 'logo.png',
    mimeType: 'image/png',
    buffer: makePng(),
  })
  await expect(page.getByAltText('Logo de la empresa')).toBeVisible({ timeout: 10000 })
  await expect(page.getByRole('button', { name: 'Cambiar logo' })).toBeVisible()

  await page.getByRole('button', { name: 'Quitar' }).click()
  await expect(page.getByText('Sin logo: se imprime el nombre de la empresa.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Subir logo' })).toBeVisible()

  // Los datos guardados siguen ahí al volver a abrir la pantalla.
  await page.reload()
  await expect(page.getByLabel('Nombre de la empresa')).toHaveValue('Multitec E2E')
})
