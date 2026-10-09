import { test, expect, unique } from './fixtures'

// El GPS se simula: el navegador de pruebas no tiene señal real.
test.use({
  geolocation: { latitude: 18.4861, longitude: -69.9312 },
  permissions: ['geolocation'],
})

test('quick survey: GPS is captured automatically and the assistant creates the client', async ({ page }) => {
  const name = unique('Cliente Asistente')
  const phoneDigits = '8095551234'

  await page.goto('/nuevo')

  // La ubicación se toma sola al abrir la pantalla, sin tocar nada.
  const maps = page.getByPlaceholder('Se llena solo con el GPS, o pega uno')
  await expect(maps).toHaveValue(/18\.486100,-69\.931200/, { timeout: 15000 })
  await expect(page.getByText('Ubicación capturada')).toBeVisible()

  // El menú de búsqueda ofrece crear el cliente cuando no existe y arranca el asistente. Como el
  // nombre ya se escribió en el buscador, el asistente no lo vuelve a preguntar: va al teléfono.
  await page.locator('input[role="combobox"]').fill(name)
  await page.getByRole('option', { name: /Crear cliente nuevo/ }).click()
  await expect(page.getByText('¿Cuál es su número de teléfono?').last()).toBeVisible()
  await expect(page.getByText('¿Cómo se llama el cliente?')).toHaveCount(0)

  // El asistente pregunta lo que falta: teléfono → tipo de levantamiento.
  await page.getByLabel('¿Cuál es su número de teléfono?').fill(phoneDigits)
  await page.getByRole('button', { name: 'Siguiente' }).click()
  await expect(page.getByText('¿Qué tipo de levantamiento es?').last()).toBeVisible()
  await page.getByRole('button', { name: 'Alarma' }).click()

  // Confirmación con los datos ya formateados, y arranque del levantamiento.
  await expect(page.getByLabel('Teléfono')).toHaveValue('809-555-1234')
  await expect(page.getByLabel('Tipo de levantamiento')).toHaveValue('Alarma')
  await page.getByRole('button', { name: /Comenzar levantamiento/ }).click()
  await expect(page.getByText(name).first()).toBeVisible({ timeout: 15000 })

  // El proyecto quedó con el tipo, y el cliente con su teléfono.
  await page.goto('/proyectos')
  await expect(page.getByText('Alarma').first()).toBeVisible()
  await expect(page.getByText('Levantamiento · Alarma').first()).toBeVisible()
  await page.goto('/clientes')
  await expect(page.getByText(name)).toBeVisible()
})

test('the assistant asks for the name first when nothing was typed', async ({ page }) => {
  await page.goto('/nuevo')
  await page.locator('input[role="combobox"]').click()
  await page.getByRole('option', { name: /Crear cliente nuevo/ }).click()
  await expect(page.getByText('¿Cómo se llama el cliente?').last()).toBeVisible()
  // "Siguiente" no avanza con el nombre vacío.
  await expect(page.getByRole('button', { name: 'Siguiente' })).toBeDisabled()
  await page.getByLabel('¿Cómo se llama el cliente?').fill('juan perez')
  await page.getByRole('button', { name: 'Siguiente' }).click()
  await expect(page.getByText('¿Cuál es su número de teléfono?').last()).toBeVisible()
  // Teléfono y tipo se pueden omitir; el nombre dictado en minúsculas se corrige a Título.
  await page.getByRole('button', { name: 'Omitir' }).click()
  await expect(page.getByText('¿Qué tipo de levantamiento es?').last()).toBeVisible()
  await page.getByRole('button', { name: 'Omitir' }).click()
  await expect(page.getByLabel('Nombre del cliente')).toHaveValue('Juan Perez')
  await expect(page.getByLabel('Tipo de levantamiento')).toHaveValue('')
})

test('client combobox filters while typing and ignores accents', async ({ page }) => {
  const name = unique('Cliente Búsqueda')
  await page.goto('/clientes')
  await page.click('button:has-text("+ Nuevo")')
  await page.locator('label:has-text("Nombre") input').fill(name)
  await page.click('button:has-text("Guardar cliente")')
  await expect(page.getByText(name)).toBeVisible({ timeout: 10000 })

  await page.goto('/proyectos')
  await page.click('button:has-text("+ Nuevo")')
  const combo = page.locator('input[role="combobox"]')
  await combo.fill('cliente busqueda') // sin tilde
  await expect(page.getByRole('option', { name, exact: true })).toBeVisible()
  await combo.fill('zzzz-no-existe')
  await expect(page.getByText('Ningún cliente coincide')).toBeVisible()
  await expect(page.getByRole('option', { name: /Crear cliente nuevo/ })).toBeVisible()
})
