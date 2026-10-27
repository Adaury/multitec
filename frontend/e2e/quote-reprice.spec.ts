import { test, expect, unique } from './fixtures'
import { apiClient } from './helpers'

// Subió el precio en el catálogo: la cotización se actualiza mostrando antes qué cambia.
test('update a quote to the current catalog prices, seeing the changes first', async ({ page }) => {
  const api = await apiClient(page)
  const category = await api.post('/categories', { name: unique('Cat Precios'), code_prefix: null })
  const productName = unique('Camara Precio')
  const product = await api.post('/catalog', { category_id: category.id, name: productName, unit: 'unidad', price: 100 })
  const client = await api.post('/clients', { name: unique('Cliente Precios') })
  const project = await api.post('/projects', { client_id: client.id, description: unique('Proyecto Precios') })
  await api.post(`/projects/${project.id}/quotes`, {
    items: [{ product_id: product.id, description: productName, quantity: 2 }],
  })
  // El catálogo sube de precio después de cotizar
  const raise = await page.request.put(`/api/catalog/${product.id}`, { headers: api.headers, data: { price: 150 } })
  expect(raise.ok()).toBeTruthy()

  await page.goto(`/proyectos/${project.id}`)
  await page.getByRole('button', { name: 'Comercial', exact: true }).click()
  await page.getByRole('button', { name: 'Cotización', exact: true }).click()
  await page.locator('button:has-text("RD$ 236.00")').first().click() // 2 × 100 + 18 %

  await page.getByRole('button', { name: 'Actualizar precios' }).click()
  const panel = page.getByTestId('quote-pricing')
  await expect(panel).toContainText(`2 × ${productName}`)
  await expect(panel).toContainText('RD$ 100.00 → RD$ 150.00')
  await expect(panel).toContainText('RD$ 236.00 → RD$ 354.00')
  await panel.getByRole('button', { name: 'Aplicar precios nuevos' }).click()
  await expect(panel).toContainText('Precios actualizados (1)')

  const quotes = await (await api.get(`/projects/${project.id}/quotes`)).json()
  expect(quotes[0].total).toBe(354)
})
