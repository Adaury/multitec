import { test, expect, unique } from './fixtures'
import { apiClient, createQuote } from './helpers'

test('the assistant greets the user and says what there is to do today', async ({ page }) => {
  const api = await apiClient(page)

  // Una visita para hoy y un levantamiento con notas que todavía no tiene cotización.
  const visitClient = await api.post('/clients', { name: unique('Cliente Visita Hoy'), address: 'Av. Winston Churchill 10' })
  const visitProject = await api.post('/projects', { client_id: visitClient.id, description: 'Visita' })
  // Fecha LOCAL (el servidor decide "hoy" con su reloj): con toISOString, pasadas las 8 pm en RD ya era mañana.
  const now = new Date()
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  await api.post('/visits', { project_id: visitProject.id, scheduled_date: today, scheduled_time: '09:30:00' })

  const readyClient = await api.post('/clients', { name: unique('Cliente Por Cotizar') })
  const readyProject = await api.post('/projects', {
    client_id: readyClient.id,
    description: 'Cámaras',
    survey_type: 'Cámaras de seguridad (CCTV)',
  })
  const survey = await page.request.put(`/api/projects/${readyProject.id}/survey`, {
    headers: api.headers,
    data: { notes: '8 cámaras IP y un NVR de 16 canales' },
  })
  expect(survey.ok()).toBeTruthy()

  // Una cotización esperando respuesta.
  const waiting = await createQuote(api, unique('Cliente Esperando'))

  await page.goto('/')
  await expect(page.getByText(/Buen(os días|as tardes|as noches), /).filter({ visible: true })).toBeVisible()
  await expect(page.getByText(/Hoy tienes/).filter({ visible: true })).toContainText('visita')
  // Siempre pregunta cómo trabajar y ofrece las formas, haya o no pendientes.
  await expect(page.getByText('¿Cómo quieres trabajar hoy?').filter({ visible: true })).toBeVisible()
  await expect(page.getByRole('link', { name: /Dictar un levantamiento/ }).filter({ visible: true })).toHaveAttribute(
    'href',
    '/nuevo?modo=voz',
  )
  await expect(page.getByRole('link', { name: /Escribirlo paso a paso/ }).filter({ visible: true })).toBeVisible()
  await expect(page.getByRole('link', { name: /Continuar: / }).filter({ visible: true }).first()).toBeVisible()

  // Cada pendiente es un toque: lleva directo a la pantalla donde se resuelve.
  await expect(page.getByText(/09:30 · Cliente Visita Hoy/).filter({ visible: true })).toBeVisible()
  await page.getByRole('button', { name: 'Cómo llegar' }).filter({ visible: true }).first().click()
  await expect(page.getByRole('menuitem', { name: 'Google Maps' }).filter({ visible: true })).toHaveAttribute(
    'href',
    /destination=/,
  )
  await expect(page.getByRole('menuitem', { name: 'Waze' }).filter({ visible: true })).toHaveAttribute('href', /waze\.com/)
  const cotizar = page.getByRole('link', { name: /Cotizar: Cliente Por Cotizar/ }).filter({ visible: true })
  await expect(cotizar).toBeVisible()
  await expect(cotizar).toHaveAttribute('href', new RegExp(`/proyectos/${readyProject.id}\\?tab=levantamiento`))
  await expect(page.getByText(new RegExp(waiting.quote.code)).filter({ visible: true })).toBeVisible()

  await cotizar.click()
  await expect(page).toHaveURL(new RegExp(`/proyectos/${readyProject.id}`))

  // "Dictar un levantamiento" entra directo al asistente que lo escucha todo, sin menú intermedio.
  await page.goto('/')
  await page.getByRole('link', { name: /Dictar un levantamiento/ }).filter({ visible: true }).click()
  await expect(page).toHaveURL(/modo=voz/)
  await expect(page.getByText('Soy tu asistente de levantamientos')).toHaveCount(0)
})
