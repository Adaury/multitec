import { test, expect, unique } from './fixtures'

test('import products from a CSV: preview first, then apply, and they show in the catalog', async ({ page }) => {
  const name = unique('Camara E2E')
  const csv = [
    'sep=;',
    'Nombre;Categoria;Unidad;Precio;Marca;Etiquetas',
    'EJEMPLO fila que se debe ignorar;Camaras IP;unidad;1;;',
    `${name};Cámaras IP;unidad;3.500,00;Hikvision;"camara;ip;4mp"`,
    'Producto con categoria inventada;Categoria que no existe;unidad;10;;',
  ].join('\n')

  await page.goto('/catalogo')
  await page.getByRole('button', { name: /Importar/ }).click()

  // La plantilla se puede bajar desde el mismo cuadro.
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: /Descargar plantilla/ }).click(),
  ])
  expect(download.suggestedFilename()).toBe('plantilla_catalogo.csv')

  // Primero la vista previa: no se crea nada todavía.
  await page.getByLabel('Archivo CSV').setInputFiles({
    name: 'catalogo.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(csv, 'utf-8'),
  })
  await page.getByRole('button', { name: 'Revisar archivo' }).click()
  const status = page.getByRole('status')
  await expect(status).toContainText('Vista previa')
  await expect(status).toContainText('1 nuevo(s)')
  await expect(status).toContainText('1 omitido(s)')
  await expect(status).toContainText('1 con error')
  await expect(page.getByText(/La categoría 'Categoria que no existe' no existe/)).toBeVisible()
  await expect(page.getByText(name)).toHaveCount(1) // solo en la vista previa, aún no en el catálogo

  // Aplicar: solo entra la fila válida.
  await page.getByRole('button', { name: 'Importar 1 producto(s)' }).click()
  await expect(page.getByRole('status')).toContainText('Importación terminada')
  await page.getByRole('button', { name: 'Listo' }).click()

  await expect(page.getByText(name)).toBeVisible({ timeout: 10000 })
  await expect(page.getByText('Producto con categoria inventada')).toHaveCount(0)
})
