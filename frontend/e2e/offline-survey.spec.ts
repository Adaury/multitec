import { test, expect, unique } from './fixtures'
import { apiClient, makePng } from './helpers'

test.use({
  geolocation: { latitude: 18.4861, longitude: -69.9312 },
  permissions: ['geolocation'],
})

test('a survey captured without signal is kept on the phone and sent when the connection returns', async ({
  page,
  context,
}) => {
  const api = await apiClient(page)
  const name = unique('Cliente Sin Senal')

  await page.goto('/nuevo')
  await expect(page.getByText('Soy tu asistente de levantamientos')).toBeVisible()

  // Se corta la señal con la app ya cargada (como en una obra con cobertura mala).
  await context.setOffline(true)
  await expect(page.getByText('Sin conexión').first()).toBeVisible()

  await page.getByLabel('Cliente').fill(name)
  await page.getByLabel('Teléfono').fill('809-555-0000')
  await page.getByRole('button', { name: 'Alarma' }).click()
  await page.getByLabel('Notas del levantamiento').fill('Cuatro sensores de puerta y una sirena exterior')
  await page.getByTestId('offline-photo-input').setInputFiles({
    name: 'foto.png',
    mimeType: 'image/png',
    buffer: makePng(),
  })
  await page.getByRole('button', { name: 'Guardar para enviar después' }).click()

  await expect(page.getByText(/Guardado en el teléfono \(1\)/)).toBeVisible()
  await expect(page.getByText(/1 levantamiento guardado sin enviar/)).toBeVisible()

  // Vuelve la señal: se envía solo, sin tocar nada.
  await context.setOffline(false)
  await expect(page.getByText(/1 levantamiento guardado sin enviar/)).toHaveCount(0, { timeout: 30000 })

  const clients = await (await api.get('/clients')).json()
  const client = clients.find((c: { name: string }) => c.name === name)
  expect(client).toBeTruthy()
  expect(client.phone).toBe('809-555-0000')

  const projects = await (await api.get('/projects')).json()
  const project = projects.find((p: { client_id: number }) => p.client_id === client.id)
  expect(project.survey_type).toBe('Alarma')

  const survey = await (await api.get(`/projects/${project.id}/survey`)).json()
  expect(survey.notes).toContain('sensores de puerta')
  expect(survey.assets.filter((a: { kind: string }) => a.kind === 'photo')).toHaveLength(1)
})
