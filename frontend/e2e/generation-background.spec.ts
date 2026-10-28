import { test, expect, unique, type Page } from './fixtures'
import { apiClient } from './helpers'

const QUOTE_DONE = {
  budget: { id: 1, items: [] },
  quote: { id: 1, code: 'COT-000099', total: 1180, items: [] },
  engineering_drafted: false,
  warnings: [],
}

async function projectWithSurvey(page: Page) {
  const name = unique('Cliente IA')
  const api = await apiClient(page)
  const client = await api.post('/clients', { name })
  const project = await api.post('/projects', { client_id: client.id, description: unique('Proyecto') })
  const saved = await page.request.put(`/api/projects/${project.id}/survey`, {
    headers: api.headers,
    data: { notes: 'Instalar 4 cámaras', measurements: '', observations: '' },
  })
  expect(saved.ok()).toBeTruthy()
  return { name, project }
}

/** Simula el servidor: la IA real tarda minutos, aquí el test decide cuándo termina. */
async function fakeServer(page: Page, label: string, projectId: number, options: { failStartOnce?: boolean } = {}) {
  let phase: 'idle' | 'running' | 'done' = 'idle'
  let failStart = options.failStartOnce ?? false
  const job = () => ({
    project_id: projectId,
    label,
    status: phase === 'done' ? 'done' : 'running',
    finished_at: '2026-10-25T20:00:00+00:00',
    result: phase === 'done' ? QUOTE_DONE : null,
  })

  await page.route('**/generate-from-survey/start*', async (route) => {
    if (failStart) {
      failStart = false
      phase = 'running' // la petición llegó al servidor, pero la respuesta nunca volvió (iPhone suspendió la página)
      await route.abort('failed')
      return
    }
    phase = 'running'
    await route.fulfill({ status: 202, json: job() })
  })
  await page.route('**/generate-from-survey/status*', async (route) => {
    await route.fulfill({ json: phase === 'idle' ? { project_id: projectId, status: 'none' } : job() })
  })
  await page.route('**/ai/generation-jobs*', async (route) => {
    await route.fulfill({ json: phase === 'idle' ? [] : [job()] })
  })
  return {
    finish: () => {
      phase = 'done'
    },
  }
}

test('the AI keeps building the quote when the technician leaves the screen', async ({ page }) => {
  const { name, project } = await projectWithSurvey(page)
  const server = await fakeServer(page, name, project.id)

  await page.goto(`/proyectos/${project.id}?tab=levantamiento`)
  await page.getByRole('button', { name: /Generar cotización con IA/ }).click()
  await expect(page.getByRole('status').getByText(`Armando la cotización de ${name}`)).toBeVisible()

  // Cambia de pantalla con un enlace de la app (no recarga): la barra de la IA no desaparece.
  await page.getByRole('link', { name: /Clientes/ }).first().click()
  await expect(page).toHaveURL(/\/clientes$/)
  await expect(page.getByRole('status').getByText(`Armando la cotización de ${name}`)).toBeVisible()

  // Al terminar avisa y lleva a la cotización.
  server.finish()
  await expect(page.getByRole('status').getByText(/Cotización lista/)).toBeVisible({ timeout: 15000 })
  await page.getByRole('link', { name: 'Ver y ajustar la cotización' }).click()
  await expect(page).toHaveURL(`/proyectos/${project.id}?tab=cotizacion`)
  await expect(page.getByText('Cotización lista')).toHaveCount(0)
})

test('reloading the page mid-generation (iPhone suspended the app) does not lose the job', async ({ page }) => {
  const { name, project } = await projectWithSurvey(page)
  const server = await fakeServer(page, name, project.id)

  await page.goto(`/proyectos/${project.id}?tab=levantamiento`)
  await page.getByRole('button', { name: /Generar cotización con IA/ }).click()
  await expect(page.getByRole('status').getByText(`Armando la cotización de ${name}`)).toBeVisible()

  // La página se recarga por completo: el estado de la pantalla se pierde, el del servidor no.
  await page.reload()
  await expect(page.getByRole('status').getByText(`Armando la cotización de ${name}`)).toBeVisible({ timeout: 10000 })

  server.finish()
  await expect(page.getByRole('status').getByText(/Cotización lista/)).toBeVisible({ timeout: 15000 })
  // Ni un error de IA: nunca llegó a fallar nada.
  await expect(page.getByText(/No se pudo armar la cotización/)).toHaveCount(0)
})

test('a dropped connection when starting is not reported as an AI error if the server did start', async ({ page }) => {
  const { name, project } = await projectWithSurvey(page)
  const server = await fakeServer(page, name, project.id, { failStartOnce: true })

  await page.goto(`/proyectos/${project.id}?tab=levantamiento`)
  await page.getByRole('button', { name: /Generar cotización con IA/ }).click()
  await expect(page.getByRole('status').getByText(`Armando la cotización de ${name}`)).toBeVisible()
  await expect(page.getByText(/No se pudo armar la cotización/)).toHaveCount(0)

  server.finish()
  await expect(page.getByRole('status').getByText(/Cotización lista/)).toBeVisible({ timeout: 15000 })
})
