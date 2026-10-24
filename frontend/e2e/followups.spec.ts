import { test, expect, unique } from './fixtures'
import { apiClient, createQuote } from './helpers'

test('unpaid invoice shows up in Seguimiento with a WhatsApp message and can be marked paid', async ({ page }) => {
  const name = unique('Cliente Cobro')
  const api = await apiClient(page)
  const nextYear = new Date()
  nextYear.setFullYear(nextYear.getFullYear() + 1)
  await api.post('/ncf-sequences', {
    ncf_type: 'B01',
    description: 'E2E',
    range_start: 1,
    range_end: 9999,
    expires_at: nextYear.toISOString().slice(0, 10),
  })
  const { quote } = await createQuote(api, name, '809-555-0101', '130000001')
  await api.post(`/quotes/${quote.id}/approve`)
  const pre = await api.post(`/quotes/${quote.id}/generate-pre-invoice`)
  const invoice = await api.post(`/pre-invoices/${pre.id}/convert-to-invoice`, {})

  await page.goto('/seguimiento')
  await expect(page.getByRole('heading', { name: 'Seguimiento' })).toBeVisible()
  const card = page.getByTestId(`factura-${invoice.code}`)
  await expect(card).toBeVisible()
  await expect(card).toContainText(name)

  // El mensaje ya viene escrito y el enlace abre WhatsApp con el número dominicano completo.
  const whatsapp = card.getByRole('link', { name: /WhatsApp/ })
  await expect(whatsapp).toHaveAttribute('href', /^https:\/\/wa\.me\/18095550101\?text=/)
  await card.getByRole('button', { name: 'Ver el mensaje' }).click()
  await expect(card.getByText(new RegExp(`factura ${invoice.code}`))).toBeVisible()

  // Marcarla como cobrada la saca de la lista.
  page.once('dialog', (dialog) => dialog.accept())
  await card.getByRole('button', { name: /Marcar como cobrada/ }).click()
  await expect(page.getByText(invoice.code)).toHaveCount(0, { timeout: 10000 })
})
