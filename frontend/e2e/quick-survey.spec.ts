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
  // El mapa de la vista previa es el de OpenStreetMap (carga siempre, el de Google se quedaba en
  // blanco en iPhone) y lleva el marcador en el punto capturado.
  await expect(page.locator('iframe[title="Mapa de la ubicación"]')).toHaveAttribute(
    'src',
    /openstreetmap\.org\/export\/embed\.html\?.*marker=18\.4861%2C-69\.9312/,
  )
  // Tocar el mapa (o "Cómo llegar" / "Ver en Maps") abre Google Maps en el punto capturado.
  await expect(page.getByRole('link', { name: 'Abrir el mapa en Google Maps' })).toHaveAttribute(
    'href',
    /google\.com\/maps\/search\/.*18\.4861,-69\.9312/,
  )
  await expect(page.getByRole('link', { name: /Cómo llegar/ })).toHaveAttribute('href', /destination=18\.4861,-69\.9312/)

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

test('the assistant greets by name as soon as the screen opens, and the technician configures that name', async ({
  page,
}) => {
  // Aparece solo, sin tocar nada, y dice en qué puede ayudar. Por defecto: "Ing." + primer nombre.
  await page.goto('/nuevo')
  await expect(page.getByText('Hola, Ing. Administrador. Soy tu asistente de levantamientos.')).toBeVisible()
  await expect(page.getByText('Te puedo ayudar a:')).toBeVisible()
  await expect(page.getByText(/Tomar tu ubicación actual/)).toBeVisible()
  await expect(page.getByRole('button', { name: '🆕 Cliente nuevo' })).toBeVisible()
  await expect(page.getByRole('button', { name: '🎙️ Decir todo de una vez' })).toBeVisible()
  await expect(page.getByRole('button', { name: '🔎 Buscar un cliente' })).toBeVisible()

  // El técnico configura cómo lo llama en su perfil.
  await page.goto('/perfil')
  await page.getByLabel('Cómo te llama el asistente de IA').fill('Ing. Pérez')
  await page.getByRole('button', { name: 'Guardar perfil' }).click()
  await expect(page.getByText('Perfil actualizado')).toBeVisible()

  await page.goto('/nuevo')
  await expect(page.getByText('Hola, Ing. Pérez. Soy tu asistente de levantamientos.')).toBeVisible()

  // "Decir todo de una vez" abre directo el cuadro para dictar o escribir todo junto.
  await page.getByRole('button', { name: '🎙️ Decir todo de una vez' }).click()
  await expect(page.getByText('Dime todo de una vez').last()).toBeVisible()
  await expect(page.getByPlaceholder(/Juan Pérez, 809 555 1234/)).toBeVisible()
  // Una vez que arranca el alta, el saludo largo se oculta para no estorbar.
  await expect(page.getByText('Te puedo ayudar a:')).toHaveCount(0)

  // Dejar el perfil como estaba para no afectar otras pruebas.
  await page.goto('/perfil')
  await page.getByLabel('Cómo te llama el asistente de IA').fill('')
  await page.getByRole('button', { name: 'Guardar perfil' }).click()
  await expect(page.getByText('Perfil actualizado')).toBeVisible()
})

test('the assistant asks for the name first when nothing was typed', async ({ page }) => {
  await page.goto('/nuevo')
  // El alta es un botón visible desde el principio (no depende de abrir la lista del buscador).
  await page.getByRole('button', { name: '＋ Cliente nuevo · el asistente te pregunta' }).click()
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
