import { test, expect, unique } from './fixtures'
import { apiClient, createQuote } from './helpers'

// Guardar la ingeniería dice que se guardó (antes no mostraba nada y parecía que el botón no hacía nada).
test('saving engineering confirms it was saved', async ({ page }) => {
  const api = await apiClient(page)
  const { project } = await createQuote(api, unique('Cliente Ingenieria'))

  await page.goto(`/proyectos/${project.id}?tab=ingenieria`)
  await page.locator('label:has-text("Equipos recomendados") textarea').fill('4 cámaras IP 4MP y un NVR de 8 canales')
  await page.getByRole('button', { name: 'Guardar ingeniería' }).click()
  await expect(page.getByRole('status').filter({ hasText: 'Ingeniería guardada' })).toBeVisible()

  await page.reload()
  await expect(page.locator('label:has-text("Equipos recomendados") textarea')).toHaveValue('4 cámaras IP 4MP y un NVR de 8 canales')
})

// El ojito del portal de cliente abre en grande el PDF de la cotización que ve el cliente.
test('the client portal eye opens the quote PDF', async ({ page }) => {
  const api = await apiClient(page)
  const { project, quote } = await createQuote(api, unique('Cliente Portal PDF'))
  await api.post(`/projects/${project.id}/public-link`)

  await page.goto(`/proyectos/${project.id}?tab=info`)
  await page.getByRole('button', { name: `Ver el PDF de ${quote.code}` }).first().click()
  const viewer = page.getByRole('dialog', { name: `Cotización ${quote.code}` })
  await expect(viewer).toBeVisible()
  await expect(viewer.getByLabel('Página 1')).toBeVisible({ timeout: 20_000 })
})
