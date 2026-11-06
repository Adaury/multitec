import { test, expect, unique } from './fixtures'

test.describe('cliente sin sesión', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test('a client opens the link, tells its experience and gets a thank-you', async ({ page }) => {
    await page.goto('/web#opinar')
    const form = page.getByRole('form', { name: 'Cuéntanos tu experiencia' })
    await expect(form).toBeVisible()
    await form.getByLabel('Tu nombre').fill(unique('Cliente Opina'))
    await form.getByLabel('Tu empresa (opcional)').fill('Ferretería El Clavo')
    await form.getByLabel('¿Cómo te ha ido con Multitec?').fill('Nos instalaron las cámaras rápido y las vemos desde el celular.')
    await form.getByRole('radio', { name: '4 estrellas' }).click()
    await form.getByLabel(/Teléfono o correo/).fill('809-555-4545')
    const send = form.getByRole('button', { name: 'Enviar mi experiencia' })
    await expect(send).toBeDisabled()
    await form.getByRole('checkbox').check()
    await send.click()
    await expect(page.getByRole('status')).toContainText('¡Gracias por contarnos tu experiencia!')
  })
})

test('the owner sees experiences sent by clients as drafts with their contact', async ({ page }) => {
  const author = unique('Opinión Panel')
  const res = await page.request.post('/api/site/experiences', {
    data: { author, quote: 'Excelente servicio y el sistema es muy fácil de usar.', rating: 5, contact: 'cliente@e2e.com', consent: true },
  })
  expect(res.ok(), await res.text()).toBeTruthy()
  await page.goto('/plataforma/sitio')
  await expect(page.getByText('Pide opiniones a tus clientes')).toBeVisible()
  const card = page.locator('[data-testid^="testimonial-"]').filter({ has: page.locator(`input[value="${author}"]`) })
  await expect(card.getByText('Enviado por cliente')).toBeVisible()
  await expect(card.getByText('cliente@e2e.com')).toBeVisible()
  await expect(card.getByText('Borrador')).toBeVisible()
})
