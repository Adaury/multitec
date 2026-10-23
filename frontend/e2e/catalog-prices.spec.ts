import { test, expect, unique } from './fixtures'

test('bulk price editor: filter, adjust by percent and save', async ({ page }) => {
  const name = unique('Camara Precio E2E')
  const csv = ['sep=;', 'Nombre;Categoria;Unidad;Precio', `${name};Cámaras IP;unidad;1.000,00`].join('\n')

  await page.goto('/catalogo')
  await page.getByRole('button', { name: /Importar/ }).click()
  await page.getByLabel('Archivo CSV').setInputFiles({
    name: 'catalogo.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(csv, 'utf-8'),
  })
  await page.getByRole('button', { name: 'Revisar archivo' }).click()
  await page.getByRole('button', { name: 'Importar 1 producto(s)' }).click()
  await page.getByRole('button', { name: 'Listo', exact: true }).click()
  await expect(page.getByText(name)).toBeVisible({ timeout: 10000 })

  await page.getByRole('button', { name: /Precios/ }).click()
  await page.getByPlaceholder('Buscar producto…').fill(name)
  await page.getByPlaceholder('Ajuste % (ej. 10 o -5)').fill('10')
  await page.getByRole('button', { name: 'Aplicar a los que se ven' }).click()
  await page.getByRole('button', { name: 'Guardar 1 cambio(s)' }).click()

  // El editor se cierra y el catálogo muestra el precio con +10 %.
  await expect(page.getByText('Actualizar precios')).toHaveCount(0)
  await expect(page.getByText('RD$ 1,100.00')).toBeVisible({ timeout: 10000 })
})
