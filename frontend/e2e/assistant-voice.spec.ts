import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test, expect } from './fixtures'

const dirname = path.dirname(fileURLToPath(import.meta.url))
// Voz sintética diciendo "Un levantamiento de cámaras para Juan Pérez". Chromium la entrega como
// si fuera el micrófono (%noloop: después de la frase queda en silencio, como una persona real).
const SPOKEN = path.join(dirname, 'fixtures', 'levantamiento-juan-perez.wav')

test.use({
  launchOptions: {
    args: [
      '--use-fake-ui-for-media-stream',
      '--use-fake-device-for-media-stream',
      `--use-file-for-fake-audio-capture=${SPOKEN}%noloop`,
    ],
  },
  permissions: ['microphone'],
})

// Camino de voz completo y real: el navegador graba, el servidor transcribe con Whisper local y
// entiende la frase. Es lento en CPU (carga del modelo + transcripción), de ahí el margen.
test.setTimeout(180_000)

test('the technician answers by voice and the assistant starts that survey', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: /Hablar con el asistente/ }).filter({ visible: true }).click()
  await expect(page.getByText(/¿Qué toca hoy\?/).filter({ visible: true })).toBeVisible()

  // Tras el saludo el micrófono se abre solo; al notar la pausa, envía lo grabado sin tocar nada.
  await expect(page.getByText(/Te escucho/).filter({ visible: true })).toBeVisible({ timeout: 30000 })

  // Lo que entendió aparece como burbuja del técnico, y lleva al levantamiento con cliente y tipo.
  await expect(page.getByText(/levantamiento de cámaras para Juan Pérez/i).filter({ visible: true }).first()).toBeVisible({
    timeout: 120000,
  })
  await expect(page).toHaveURL(/\/nuevo\?nombre=Juan\+P%C3%A9rez&tipo=/, { timeout: 60000 })
  await expect(page.getByText('¿Cuál es su número de teléfono?').last()).toBeVisible()
})
