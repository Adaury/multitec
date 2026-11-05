import { test, expect, unique } from './fixtures'
import { apiClient, createQuote } from './helpers'

// Administración → Borrar datos de prueba: se elige un cliente, se ve qué se borra, se confirma con BORRAR y desaparece
// con su proyecto y su cotización.
test('a test client is deleted with everything it owns after typing BORRAR', async ({ page }) => {
  const name = unique('Cliente Prueba Borrar')
  const api = await apiClient(page)
  const { project } = await createQuote(api, name)

  await page.goto('/administracion')
  await page.getByRole('link', { name: /Borrar datos de prueba/ }).click()
  await expect(page).toHaveURL(/\/borrar-pruebas$/)

  // Otras pruebas corren a la vez: se desmarca todo y se elige solo el cliente de esta prueba.
  // (Clientes y productos tienen cada uno su «Desmarcar todo»; el de productos solo aparece si hay alguno marcado.)
  const unmark = page.getByRole('button', { name: 'Desmarcar todo' })
  await expect(unmark.first()).toBeVisible()
  while ((await unmark.count()) > 1) await unmark.last().click()
  await unmark.first().click()
  await page.getByLabel('Buscar cliente o producto').fill(name)
  await page.getByLabel(`Borrar cliente ${name}`).check()
  await expect(page.getByText('1 cliente(s) y 0 producto(s) elegidos.')).toBeVisible()

  await page.getByRole('button', { name: 'Revisar qué se borra' }).click()
  const dialog = page.getByRole('dialog', { name: 'Confirmar borrado' })
  await expect(dialog.getByText('Proyectos')).toBeVisible()
  await expect(dialog.getByText('Cotizaciones')).toBeVisible()
  const remove = dialog.getByRole('button', { name: 'Borrar definitivamente' })
  await expect(remove).toBeDisabled()
  await dialog.getByLabel('Escribe BORRAR para confirmar').fill('borrar')
  await remove.click()

  await expect(page.getByRole('status')).toContainText('se borraron los datos de prueba')
  const res = await page.request.get(`/api/projects/${project.id}`, { headers: api.headers })
  expect(res.status()).toBe(404)
})

// Catálogo → Importar: el catálogo base muestra cuántos artículos agregaría (vista previa, no cambia nada).
test('the base catalog preview lists the articles it would add', async ({ page }) => {
  await page.goto('/catalogo')
  await page.getByRole('button', { name: /Importar/ }).click()
  await expect(page.getByText(/Catálogo base · \d+ artículos/)).toBeVisible()
  await expect(page.getByLabel('Descargar lista de cerco eléctrico en Excel')).toBeVisible()
  await page.getByRole('button', { name: 'Ver qué se agrega' }).click()
  await expect(page.getByRole('status')).toContainText('Catálogo base:')
  await expect(page.getByRole('button', { name: /Importar \d+ producto\(s\)/ })).toBeEnabled()
})
