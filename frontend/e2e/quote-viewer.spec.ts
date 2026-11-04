import { test, expect, unique } from './fixtures'
import { apiClient, createQuote } from './helpers'

// Visor de la cotización dentro de la app: se ve sin descargar, cambia de formato, abre la edición y envía.
test('the quote opens in the in-app viewer, switches format and offers the send channels', async ({ page }) => {
  const api = await apiClient(page)
  const { project, quote } = await createQuote(api, unique('Cliente Visor'), '809-555-7788')

  await page.goto(`/proyectos/${project.id}`)
  await page.getByRole('button', { name: 'Comercial', exact: true }).click()
  await page.getByRole('button', { name: 'Cotización', exact: true }).click()
  await page.getByText(quote.code).click()
  await page.getByRole('button', { name: 'Ver', exact: true }).click()

  const viewer = page.getByRole('dialog', { name: `Cotización ${quote.code}` })
  await expect(viewer).toBeVisible()
  // El PDF se dibuja en la página (no se descarga).
  await expect(viewer.getByLabel('Página 1')).toBeVisible({ timeout: 20_000 })

  await viewer.getByRole('tab', { name: 'Formato y envío' }).click()
  const general = page.waitForRequest((r) => r.url().includes(`/quotes/${quote.id}/pdf`) && r.url().includes('variant=global'))
  await viewer.getByRole('radio', { name: 'Monto general' }).click()
  await general

  for (const name of ['WhatsApp', 'Correo', 'Enlace']) await expect(viewer.getByRole('button', { name, exact: true })).toBeVisible()
  await viewer.getByRole('button', { name: 'Correo', exact: true }).click()
  await expect(viewer.getByLabel('Correo del cliente')).toBeVisible()

  // Editar cierra el visor y abre la edición de la misma cotización.
  await viewer.getByRole('button', { name: 'Editar' }).click()
  await expect(viewer).toBeHidden()
  await expect(page.getByRole('button', { name: 'Guardar cambios' })).toBeVisible()
})
