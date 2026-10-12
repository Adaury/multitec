import { test, expect, unique } from './fixtures'
import { apiClient, createQuote, makePng } from './helpers'

test('mark equipment on a survey photo and see the numbered annex in the quote PDF', async ({ page }) => {
  const api = await apiClient(page)
  const { project, quote } = await createQuote(api, unique('Cliente Fotos'))

  const upload = await page.request.post(`/api/projects/${project.id}/survey/assets`, {
    headers: api.headers,
    multipart: { kind: 'photo', file: { name: 'fachada.png', mimeType: 'image/png', buffer: makePng(320, 240) } },
  })
  expect(upload.ok()).toBeTruthy()

  await page.goto(`/proyectos/${project.id}`)
  await page.getByRole('button', { name: 'Datos', exact: true }).click()
  await page.getByRole('button', { name: 'Levantamiento', exact: true }).click()
  await page.getByRole('button', { name: 'Marcar equipos en la foto' }).click()

  // Dos toques sobre la foto = dos puntos numerados; el segundo se renombra.
  const surface = page.getByTestId('marker-surface')
  // Espera a que la foto cargue: antes de eso no tiene alto y no hay dónde tocar.
  await expect(page.getByAltText('Foto del levantamiento')).toHaveJSProperty('complete', true)
  const box = (await surface.boundingBox())!
  await surface.click({ position: { x: box.width * 0.25, y: box.height * 0.4 } })
  await surface.click({ position: { x: box.width * 0.7, y: box.height * 0.6 } })
  await page.getByPlaceholder('Nombre del punto').nth(1).fill('NVR')
  await page.getByRole('button', { name: 'Guardar puntos' }).click()

  // El contador aparece en la foto y el servidor numeró de corrido.
  await expect(page.getByRole('button', { name: 'Marcar equipos en la foto' })).toContainText('2')
  const survey = await (await api.get(`/projects/${project.id}/survey`)).json()
  const markers = survey.assets[0].markers
  expect(markers.map((m: { number: number }) => m.number)).toEqual([1, 2])
  expect(markers[1].label).toBe('NVR')

  // La cotización con fotos es un PDF más grande que la normal.
  const plain = await (await page.request.get(`/api/quotes/${quote.id}/pdf`, { headers: api.headers })).body()
  const withPhotos = await (
    await page.request.get(`/api/quotes/${quote.id}/pdf?photos=marked`, { headers: api.headers })
  ).body()
  expect(withPhotos.subarray(0, 4).toString()).toBe('%PDF')
  expect(withPhotos.length).toBeGreaterThan(plain.length)
})

test('the client can reject a quote from their link and the office sees why', async ({ page }) => {
  const api = await apiClient(page)
  const { project, quote } = await createQuote(api, unique('Cliente Portal'), '809-555-4321')
  const link = await api.post(`/projects/${project.id}/public-link`)

  // La cotización lleva el botón de WhatsApp del cliente (con teléfono válido).
  await page.goto(`/proyectos/${project.id}`)
  await page.getByRole('button', { name: 'Comercial', exact: true }).click()
  await page.getByRole('button', { name: 'Cotización', exact: true }).click()
  await page.getByText(quote.code).click()
  await expect(page.getByRole('button', { name: 'Enviar al cliente por WhatsApp' })).toBeVisible()

  // Vista del cliente: sin sesión.
  const clientPage = await page.context().browser()!.newContext({ baseURL: page.url().split('/proyectos')[0] })
  const portal = await clientPage.newPage()
  await portal.goto(`/portal/${link.token}`)
  await expect(portal.getByRole('link', { name: 'Ver cotización en PDF' })).toBeVisible()
  await portal.getByPlaceholder('Tu nombre (queda como constancia)').fill('María Pérez')
  await portal.getByRole('button', { name: 'No me interesa o quiero cambios' }).click()
  await portal.getByPlaceholder('¿Qué te gustaría cambiar? (opcional)').fill('Quiero una cámara menos')
  await portal.getByRole('button', { name: 'Confirmar rechazo' }).click()
  await expect(portal.getByText('No aprobada').first()).toBeVisible()
  await clientPage.close()

  const history = await (await api.get(`/quotes/${quote.id}/history`)).json()
  expect(history.some((h: { note: string }) => h.note?.includes('María Pérez') && h.note.includes('una cámara menos'))).toBe(
    true,
  )
})
