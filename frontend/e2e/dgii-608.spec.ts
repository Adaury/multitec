import { test, expect, unique } from './fixtures'
import { apiClient, issueInvoice } from './helpers'

test('voiding an invoice moves it from the 607 to the 608 and marks it in the project', async ({ page }) => {
  const api = await apiClient(page)
  const { project, invoice } = await issueInvoice(api, unique('Cliente Anulado'))

  const now = new Date()
  const period = `year=${now.getFullYear()}&month=${now.getMonth() + 1}`
  const before = await (await page.request.get(`/api/reports/dgii-607?${period}`, { headers: api.headers })).text()
  expect(before).toContain(invoice.ncf) // antes de anular sí es una venta del 607

  await page.goto(`/proyectos/${project.id}`)
  await page.getByRole('button', { name: 'Facturación', exact: true }).click()
  await page.getByRole('button', { name: 'Factura', exact: true }).click()
  await page.getByText(invoice.code).click()

  await page.getByRole('button', { name: 'Anular factura…' }).click()
  await page.getByLabel('Tipo de anulación').selectOption('04')
  await page.getByLabel('Nota (opcional)').fill('RNC mal digitado')
  await page.getByRole('button', { name: 'Confirmar anulación' }).click()

  await expect(page.getByText(/ANULADA \(tipo 04\)/)).toBeVisible()
  // Una factura anulada ya no se cobra ni se vuelve a anular.
  await expect(page.getByRole('button', { name: 'Anular factura…' })).toHaveCount(0)
  await expect(page.getByText('Cobro y retenciones (para el 607)')).toHaveCount(0)

  const r607 = await (await page.request.get(`/api/reports/dgii-607?${period}`, { headers: api.headers })).text()
  const r608 = await (await page.request.get(`/api/reports/dgii-608?${period}`, { headers: api.headers })).text()
  expect(r607).not.toContain(invoice.ncf)
  expect(r608).toContain(invoice.ncf)
  expect(r608).toContain('Corrección de la información')
})

test('the DGII .txt explains what is missing when the company RNC is not configured', async ({ page }) => {
  await page.goto('/ncf')
  await page.getByRole('button', { name: 'Archivo DGII (.txt)' }).first().click()

  // El backend de pruebas no tiene COMPANY_RNC: el mensaje dice qué hacer, no un error genérico.
  await expect(page.getByText(/COMPANY_RNC en backend\/\.env/).last()).toBeVisible()
})
