import { test, expect } from './fixtures'

test('the header shows whether the system is ready and explains what is not', async ({ page, context }) => {
  await page.goto('/')
  const indicator = page.getByRole('button', { name: /Estado del sistema/ })
  await expect(indicator).toBeVisible()

  // Tocarlo muestra el detalle: servidor y base de datos siempre; la IA depende de que Ollama corra.
  await indicator.click()
  await expect(page.getByText('Servidor', { exact: true })).toBeVisible()
  await expect(page.getByText('Base de datos', { exact: true })).toBeVisible()
  await expect(page.getByText('IA de texto', { exact: true })).toBeVisible()

  // Sin señal el indicador lo dice y tranquiliza al técnico sobre lo que captura.
  await context.setOffline(true)
  await expect(page.getByRole('button', { name: /Sin conexión a internet/ })).toBeVisible()
  await expect(page.getByText(/se guarda en el teléfono/)).toBeVisible()
  await context.setOffline(false)
})
