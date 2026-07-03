import { test, expect, unique } from './fixtures'

test('budget -> convert to quote -> approve, with correct ITBIS math', async ({ page }) => {
  const clientName = unique('Cliente Cotizacion')
  const description = unique('Proyecto Cotizacion')

  await page.goto('/clientes')
  await page.click('button:has-text("+ Nuevo")')
  await page.locator('label:has-text("Nombre") input').fill(clientName)
  await page.click('button:has-text("Guardar cliente")')
  await expect(page.getByText(clientName)).toBeVisible({ timeout: 10000 })

  await page.goto('/proyectos')
  await page.click('button:has-text("+ Nuevo")')
  await page.locator('label:has-text("Cliente") select').selectOption({ label: clientName })
  await page.locator('label:has-text("Descripción") textarea').fill(description)
  await page.click('button:has-text("Crear proyecto")')
  await page.locator('a', { hasText: description }).click()
  await expect(page).toHaveURL(/\/proyectos\/\d+/)

  // Presupuesto: una línea de texto libre, 4 x 100 = 400
  await page.click('button:has-text("Presupuesto")')
  await page.click('button:has-text("+ Nuevo")')
  await page.click('button:has-text("+ Agregar línea")')
  await page.fill('input[placeholder="Descripción"]', 'Cámara domo 4MP')
  await page.fill('input[placeholder="Cantidad"]', '4')
  await page.fill('input[placeholder="Precio unitario"]', '100')
  await expect(page.getByText('RD$ 400.00').last()).toBeVisible()
  await page.click('button:has-text("Guardar presupuesto")')
  await expect(page.getByText('Cámara domo 4MP')).toBeVisible({ timeout: 10000 })

  // Convertir a cotización -> cambia de pestaña sola
  await page.click('button:has-text("Convertir a cotización")')
  await expect(page.getByRole('button', { name: 'Cotización', exact: true })).toHaveClass(/text-brand-blue/, {
    timeout: 10000,
  })

  // ITBIS 18% sobre 400 = 72; total 472
  const quoteCard = page.locator('button:has-text("RD$ 472.00")').first()
  await expect(quoteCard).toBeVisible({ timeout: 10000 })
  await quoteCard.click()
  await expect(page.getByText('RD$ 72.00')).toBeVisible()

  await page.click('button:has-text("Aprobar")')
  await expect(page.getByText('Aprobada').first()).toBeVisible({ timeout: 10000 })

  // La aprobación genera materiales automáticamente
  await page.click('button:has-text("Compras")')
  await expect(page.getByText('Cámara domo 4MP')).toBeVisible({ timeout: 10000 })
})
