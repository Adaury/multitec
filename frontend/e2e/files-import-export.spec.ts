import { test, expect, unique } from './fixtures'
import { apiClient, createQuote } from './helpers'

// Catálogo: varios archivos a la vez (Excel y CSV) y las categorías que faltan se crean con un toque.
test('several catalog files load at once and missing categories are created', async ({ page }) => {
  const alarm = unique('Sirena Exterior E2E')
  const hardware = unique('Taco Plastico E2E')
  await page.goto('/catalogo')
  await page.getByRole('button', { name: /Importar/ }).click()
  await page.getByLabel(/Archivo CSV o Excel/).setInputFiles([
    { name: 'alarma.csv', mimeType: 'text/csv', buffer: Buffer.from(`Nombre;Categoria;Precio\n${alarm};Alarmas E2E > Sirenas;1850\n`) },
    { name: 'ferreteria.csv', mimeType: 'text/csv', buffer: Buffer.from(`Nombre;Categoria;Precio\n${hardware};Ferreteria E2E > Anclajes;25\n`) },
  ])
  await page.getByRole('button', { name: 'Revisar 2 archivos' }).click()
  await expect(page.getByRole('status')).toContainText('2 con error')
  await page.getByRole('button', { name: 'Crearlas y revisar de nuevo' }).click()
  await expect(page.getByText(/Se crearán estas categorías/)).toBeVisible()
  await page.getByRole('button', { name: 'Importar 2 producto(s)' }).click()
  await expect(page.getByRole('status')).toContainText('Importación terminada')
  await page.getByRole('button', { name: 'Listo', exact: true }).click()
  await expect(page.getByText(alarm)).toBeVisible()
  await expect(page.getByText(hardware)).toBeVisible()
})

// Cotización: las partidas se descargan en Excel y se cargan desde archivos al editar.
test('quote items download as a file and load back from files when editing', async ({ page }) => {
  const api = await apiClient(page)
  const { project, quote } = await createQuote(api, unique('Cliente Archivos'))
  await page.goto(`/proyectos/${project.id}?tab=cotizacion&cotizacion=${quote.id}`)
  await page.getByRole('toolbar').getByRole('button', { name: 'Partidas', exact: true }).click()
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'Descargar partidas (Excel)' }).click(),
  ])
  expect(download.suggestedFilename()).toBe(`${quote.code}-partidas.xlsx`)

  await page.getByRole('toolbar').getByRole('button', { name: 'Editar', exact: true }).click()
  await page.getByLabel('Archivos de partidas (Excel o CSV)').setInputFiles([
    { name: 'materiales.csv', mimeType: 'text/csv', buffer: Buffer.from('Descripcion;Cantidad;Precio\nSensor PIR E2E;3;900\nAmarres plasticos;2;150\n') },
  ])
  await expect(page.getByRole('status').filter({ hasText: 'Se agregaron 2 partida(s)' })).toBeVisible()
  await page.getByRole('button', { name: 'Guardar cambios' }).click()
  await expect(page.getByText('3 partidas', { exact: false })).toBeVisible()
  // La sección Partidas sigue abierta tras guardar.
  await expect(page.getByText(/3 × Sensor PIR E2E/)).toBeVisible()
})
