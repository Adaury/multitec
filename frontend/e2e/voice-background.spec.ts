import { test, expect, unique } from './fixtures'

// Micrófono y GPS simulados: Chromium trae un micrófono falso que emite un tono.
test.use({
  geolocation: { latitude: 18.4861, longitude: -69.9312 },
  permissions: ['geolocation', 'microphone'],
  launchOptions: { args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'] },
})

test('a dictation is processed in the background while the technician keeps working', async ({ page }) => {
  const name = unique('Cliente Voz')

  // La IA real (Whisper + Ollama) tarda ~30 s: aquí se responde con retraso y datos fijos para
  // probar el comportamiento de la pantalla, no la calidad de la transcripción.
  let release!: () => void
  const gate = new Promise<void>((resolve) => (release = resolve))
  await page.route('**/survey/assets/*/transcribe', async (route) => {
    await gate
    await route.fulfill({
      json: {
        transcript: 'Instalar cuatro cámaras de 4 megapíxeles Hikvision',
        notes: 'Instalar 4 cámaras de 4 megapíxeles Hikvision',
        measurements: '',
        observations: '',
        classified: true,
      },
    })
  })

  // Cliente nuevo con el asistente y arranque del levantamiento.
  await page.goto('/nuevo')
  await page.getByRole('button', { name: '🆕 Cliente nuevo' }).click()
  await page.getByLabel('¿Cómo se llama el cliente?').fill(name)
  await page.getByRole('button', { name: 'Siguiente' }).click()
  await page.getByRole('button', { name: 'Omitir' }).click()
  await page.getByRole('button', { name: 'Omitir' }).click()
  await page.getByRole('button', { name: /Comenzar levantamiento/ }).click()
  await expect(page.getByRole('button', { name: 'Empezar a narrar' })).toBeVisible({ timeout: 15000 })

  // Graba unos segundos y termina.
  await page.getByRole('button', { name: 'Empezar a narrar' }).click()
  await expect(page.getByText(/Grabando/)).toBeVisible()
  await page.waitForTimeout(2500)
  await page.getByRole('button', { name: 'Detener grabación' }).click()

  // Mientras la IA trabaja se ve el estado con su cronómetro, y NADA queda bloqueado.
  const status = page.getByRole('status').filter({ hasText: 'Procesando tu dictado' })
  await expect(status).toBeVisible({ timeout: 15000 })
  await expect(status).toContainText('Puedes seguir')
  await expect(page.getByRole('button', { name: 'Empezar a narrar' })).toBeEnabled()
  await expect(page.getByRole('button', { name: /Tomar foto/ })).toBeEnabled()

  // Al terminar aparece el aviso de dictado listo, sin que el técnico haya tenido que esperar.
  release()
  await expect(page.getByText('Tu dictado está listo')).toBeVisible({ timeout: 15000 })
  await expect(status).toHaveCount(0)
  await page.getByRole('button', { name: 'Revisar lo que entendí' }).click()
  await expect(page.getByLabel('Notas')).toHaveValue('Instalar 4 cámaras de 4 megapíxeles Hikvision')
})
