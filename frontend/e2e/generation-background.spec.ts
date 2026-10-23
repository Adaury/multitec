import { test, expect, unique } from './fixtures'
import { apiClient } from './helpers'

test('the AI keeps building the quote when the technician leaves the screen', async ({ page }) => {
  const name = unique('Cliente IA')
  const api = await apiClient(page)
  const client = await api.post('/clients', { name })
  const project = await api.post('/projects', { client_id: client.id, description: unique('Proyecto') })
  const saved = await page.request.put(`/api/projects/${project.id}/survey`, {
    headers: api.headers,
    data: { notes: 'Instalar 4 cámaras', measurements: '', observations: '' },
  })
  expect(saved.ok()).toBeTruthy()

  // La IA real tarda minutos: aquí se responde cuando el test lo decide, con una cotización fija.
  let release!: () => void
  const gate = new Promise<void>((resolve) => (release = resolve))
  await page.route('**/generate-from-survey*', async (route) => {
    await gate
    await route.fulfill({
      json: {
        budget: { id: 1, items: [] },
        quote: { id: 1, code: 'COT-000099', total: 1180, items: [] },
        engineering_drafted: false,
        warnings: [],
      },
    })
  })

  await page.goto(`/proyectos/${project.id}?tab=levantamiento`)
  await page.getByRole('button', { name: /Generar cotización con IA/ }).click()
  await expect(page.getByRole('status').getByText(`Armando la cotización de ${name}`)).toBeVisible()

  // Cambia de pantalla con un enlace de la app (no recarga): la barra de la IA no desaparece.
  await page.getByRole('link', { name: /Clientes/ }).first().click()
  await expect(page).toHaveURL(/\/clientes$/)
  await expect(page.getByRole('status').getByText(`Armando la cotización de ${name}`)).toBeVisible()

  // Al terminar avisa y lleva a la cotización.
  release()
  await expect(page.getByRole('status').getByText(/Cotización lista/)).toBeVisible({ timeout: 10000 })
  await page.getByRole('link', { name: 'Ver y ajustar la cotización' }).click()
  await expect(page).toHaveURL(`/proyectos/${project.id}?tab=cotizacion`)
  await expect(page.getByText('Cotización lista')).toHaveCount(0)
})
