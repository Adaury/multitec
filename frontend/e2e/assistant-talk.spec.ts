import { test, expect, unique } from './fixtures'
import { apiClient } from './helpers'

// El navegador de pruebas no tiene micrófono ni voz: la conversación se prueba por el camino
// escrito, que usa exactamente el mismo flujo que el hablado.
// Cada turno espera a que el asistente "termine de hablar" (en el navegador de pruebas no suena,
// así que corre el tope de espera) y una frase desconocida pasa por la IA local: varios turnos
// no caben en los 30 s por defecto.
test.setTimeout(150_000)

async function openTalk(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.getByRole('button', { name: /Hablar con el asistente/ }).filter({ visible: true }).click()
  await expect(page.getByText(/¿Qué toca hoy\?/).filter({ visible: true })).toBeVisible()
}

async function say(page: import('@playwright/test').Page, text: string) {
  await page.getByLabel('Escribe lo que quieres hacer').filter({ visible: true }).fill(text)
  await page.getByRole('button', { name: 'Enviar' }).filter({ visible: true }).click()
}

test('the assistant asks what is on for today and starts the survey the technician describes', async ({ page }) => {
  const name = unique('Rosa Conversa')

  await openTalk(page)
  // El saludo lleva el nombre del técnico y el resumen del día antes de la pregunta.
  await expect(page.getByText(/🤖 Buen(os días|as tardes|as noches), .*¿Qué toca hoy\?/).filter({ visible: true })).toBeVisible()

  await say(page, `un levantamiento de alarma para ${name}`)

  // Entendió cliente y tipo, lo confirma y lleva al levantamiento sin volver a preguntarlos.
  await expect(page).toHaveURL(/\/nuevo\?nombre=/, { timeout: 15000 })
  await expect(page.getByText('¿Cuál es su número de teléfono?').last()).toBeVisible()
  await expect(page.getByText('¿Cómo se llama el cliente?')).toHaveCount(0)
})

test('the assistant opens an existing project by the client name and answers the agenda', async ({ page }) => {
  const api = await apiClient(page)
  const clientName = unique('Ferreteria Dialogo')
  const client = await api.post('/clients', { name: clientName })
  const project = await api.post('/projects', { client_id: client.id, description: 'Cámaras' })

  await openTalk(page)

  // Preguntar por el día no lleva a ningún lado: responde y sigue escuchando.
  await say(page, 'qué tengo hoy')
  await expect(page.getByText(/¿(Con cuál empezamos|Qué quieres hacer)\?/).filter({ visible: true })).toBeVisible({
    timeout: 15000,
  })
  await expect(page).toHaveURL(/\/$/)

  // Algo que no se entiende: pide repetir con ejemplos, sin inventar una acción.
  await say(page, 'bla bla bla')
  await expect(page.getByText(/No te entendí bien/).filter({ visible: true })).toBeVisible({ timeout: 90000 })

  await say(page, `continuar con ${clientName}`)
  await expect(page).toHaveURL(new RegExp(`/proyectos/${project.id}$`), { timeout: 15000 })
})
