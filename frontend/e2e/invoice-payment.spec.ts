import { test, expect, unique } from './fixtures'

/** Arma por la API (con la sesión del navegador) una factura emitida: NCF → cliente → proyecto →
 * presupuesto → cotización aprobada → prefactura → factura. Devuelve los ids para la prueba. */
async function issueInvoice(page: import('@playwright/test').Page, clientName: string) {
  await page.goto('/')
  const token = await page.evaluate(() => localStorage.getItem('multitec_token'))
  const headers = { Authorization: `Bearer ${token}` }
  const post = async (url: string, data?: unknown) => {
    const res = await page.request.post(`/api${url}`, { headers, data })
    expect(res.ok(), `${url} -> ${res.status()} ${await res.text()}`).toBeTruthy()
    return res.json()
  }

  const nextYear = new Date()
  nextYear.setFullYear(nextYear.getFullYear() + 1)
  await post('/ncf-sequences', {
    ncf_type: 'B02',
    description: 'E2E',
    range_start: 1,
    range_end: 9999,
    expires_at: nextYear.toISOString().slice(0, 10),
  })
  const client = await post('/clients', { name: clientName })
  const project = await post('/projects', { client_id: client.id, description: unique('Proyecto Cobro') })
  const budget = await post(`/projects/${project.id}/budgets`, {
    items: [{ description: 'Cámara IP', quantity: 1, unit_price: 1000 }],
  })
  const quote = await post(`/budgets/${budget.id}/convert-to-quote`)
  await post(`/quotes/${quote.id}/approve`)
  const preInvoice = await post(`/quotes/${quote.id}/generate-pre-invoice`)
  const invoice = await post(`/pre-invoices/${preInvoice.id}/convert-to-invoice`, {})
  return { project, invoice, headers }
}

test('register how an invoice was paid and its retentions, and see them in the 607', async ({ page }) => {
  const { project, invoice, headers } = await issueInvoice(page, unique('Cliente Cobro'))

  await page.goto(`/proyectos/${project.id}`)
  await page.getByRole('button', { name: 'Facturación', exact: true }).click()
  await page.getByRole('button', { name: 'Factura', exact: true }).click()
  await page.getByText(invoice.code).click() // despliega la factura

  await expect(page.getByText('Cobro y retenciones (para el 607)')).toBeVisible()
  await page.getByLabel('Forma de pago').selectOption('tarjeta')
  await page.getByLabel('ITBIS retenido').fill('50')
  // Con una retención, la fecha pasa a ser obligatoria.
  await expect(page.getByLabel('Fecha de la retención')).toBeVisible()
  await page.getByLabel('Fecha de la retención').fill(new Date().toISOString().slice(0, 10))
  await page.getByRole('button', { name: 'Guardar cobro y retenciones' }).click()
  await expect(page.getByText('Guardado. Se usará en el reporte 607.')).toBeVisible()

  // El dato quedó en el backend y sale en el reporte 607 en las columnas correctas.
  const saved = await (await page.request.get(`/api/invoices/${invoice.id}`, { headers })).json()
  expect(saved.payment_method).toBe('tarjeta')
  expect(saved.itbis_withheld).toBe(50)

  const now = new Date()
  const csvRes = await page.request.get(`/api/reports/dgii-607?year=${now.getFullYear()}&month=${now.getMonth() + 1}`, {
    headers,
  })
  const lines = (await csvRes.text()).replace(/^﻿/, '').trim().split(/\r?\n/)
  const header = lines[0].split(',')
  const row = lines.find((l) => l.includes(invoice.ncf))!.split(',')
  expect(row[header.indexOf('Tarjeta Débito/Crédito')]).toBe('1180.0') // 1000 + 18% de ITBIS
  expect(row[header.indexOf('ITBIS Retenido')]).toBe('50.0')

  // Un valor inválido lo rechaza el servidor y la pantalla lo muestra.
  await page.getByLabel('ITBIS retenido').fill('9999')
  await page.getByRole('button', { name: 'Guardar cobro y retenciones' }).click()
  await expect(page.getByText(/ITBIS retenido no puede ser mayor/)).toBeVisible()
})
