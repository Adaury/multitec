import { test, expect, unique } from './fixtures'

test('register a purchase invoice, reject a duplicate NCF and download the 606', async ({ page }) => {
  const supplierName = unique('Proveedor E2E')
  const ncf = `B01${String(Date.now()).slice(-8)}`

  await page.goto('/proveedores')
  await page.click('button:has-text("+ Agregar")')
  await page.locator('label:has-text("Nombre") input').fill(supplierName)
  await page.locator('label:has-text("RNC") input').fill('101000009')
  await page.click('button:has-text("Agregar proveedor")')
  await expect(page.getByText(supplierName)).toBeVisible({ timeout: 10000 })

  async function fillInvoice() {
    await page.click('button:has-text("+ Factura de compra")')
    await page.locator('label:has-text("Proveedor") select').selectOption({ label: `${supplierName} (101000009)` })
    await page.locator('label:has-text("NCF") input').first().fill(ncf)
  }

  await page.goto('/compras')
  await fillInvoice()
  await page.locator('label:has-text("Monto en servicios") input').fill('250')
  await page.locator('label:has-text("Monto en bienes") input').fill('750')
  await page.locator('label:has-text("ITBIS facturado") input').fill('180')
  await page.click('button:has-text("Registrar factura")')

  // La base de los E2E es nueva, así que esta es la única factura de compra de la lista.
  await expect(page.getByText(ncf)).toBeVisible({ timeout: 10000 })
  await expect(page.getByText(supplierName).first()).toBeVisible()
  await expect(page.getByText(/Total RD\$\s*1,000\.00/)).toBeVisible()

  // El mismo NCF para el mismo proveedor lo rechaza el backend (409) y la pantalla lo muestra.
  await fillInvoice()
  await page.click('button:has-text("Registrar factura")')
  await expect(page.getByText('Ya existe una factura de este proveedor con ese NCF')).toBeVisible({ timeout: 10000 })
  await page.click('button:has-text("Cancelar")')

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.click('button:has-text("Descargar reporte 606")'),
  ])
  expect(download.suggestedFilename()).toMatch(/^606_\d{6}\.csv$/)
  const stream = await download.createReadStream()
  const chunks: Buffer[] = []
  for await (const chunk of stream) chunks.push(Buffer.from(chunk))
  const csv = Buffer.concat(chunks).toString('utf-8')
  expect(csv).toContain(ncf)
  expect(csv).toContain('101000009')

  page.once('dialog', (dialog) => dialog.accept())
  await page.getByRole('button', { name: 'Eliminar' }).click()
  await expect(page.getByText(ncf)).toHaveCount(0, { timeout: 10000 })
})
