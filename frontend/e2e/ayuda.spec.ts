import { test, expect, unique } from './fixtures'
import { apiClient } from './helpers'

test('the help page shows the full guide, the step by step with its videos and the FAQ', async ({ page }) => {
  await page.goto('/ayuda')
  await expect(page.getByRole('heading', { name: 'Ayuda', exact: true })).toBeVisible()

  // Guía completa y un paso con su video corto y sus pasos en texto
  await expect(page.getByTestId('video-00-guia-completa')).toBeVisible()
  const entrar = page.getByTestId('ayuda-paso-entrar')
  await expect(entrar).toContainText('Entrar al sistema')
  await expect(entrar.getByTestId('video-01-entrar-al-sistema')).toBeVisible()
  await entrar.getByText('Ver los pasos en texto').click()
  await expect(entrar.getByText(/el asistente te dice qué hay para hoy/).last()).toBeVisible()

  // El administrador de la plataforma ve también los pasos de oficina y de plataforma
  await expect(page.getByTestId('ayuda-paso-cotizacion-ia')).toBeVisible()
  await expect(page.getByTestId('ayuda-paso-plataforma')).toBeVisible()

  // Preguntas frecuentes plegables
  const pregunta = page.getByText('Olvidé mi contraseña. ¿Qué hago?')
  await pregunta.click()
  await expect(page.getByText(/te genera una clave temporal de un solo uso/)).toBeVisible()
})

test('the videos and their covers are served without a session and support seeking (iPhone needs ranges)', async ({
  request,
}) => {
  const ids = [
    '00-guia-completa',
    '01-entrar-al-sistema',
    '02-cliente-y-proyecto',
    '03-levantamiento-y-puntos',
    '04-cotizacion-con-ia',
    '05-precios-y-comparar',
    '06-mapa-y-como-llegar',
    '07-plataforma-y-demos',
    '08-el-tecnico-en-el-iphone',
  ]
  for (const id of ids) {
    const video = await request.get(`/videos/${id}.mp4`, { headers: { Range: 'bytes=0-99' } })
    expect(video.status(), id).toBe(206)
    expect(video.headers()['content-type'], id).toContain('video/mp4')
    const cover = await request.get(`/videos/${id}.jpg`)
    expect(cover.status(), id).toBe(200)
    expect(cover.headers()['content-type'], id).toContain('image/jpeg')
  }
})

test('a technician sees only the help that applies to them', async ({ browser, request }) => {
  const api = await apiClient(await (await browser.newContext()).newPage())
  const email = `${unique('ayuda').replace(/\s+/g, '.').toLowerCase()}@multitec.com`
  const created = await api.post('/users', { name: 'Técnico Ayuda', email, password: 'clave-temporal-1', role: 'tecnico' })
  expect(created.id).toBeTruthy()
  // Cambia la clave temporal por la suya (si no, la app solo le deja ver el perfil)
  const login = await request.post('/api/auth/login', { form: { username: email, password: 'clave-temporal-1' } })
  const token = (await login.json()).access_token
  const changed = await request.post('/api/auth/change-password', {
    headers: { Authorization: `Bearer ${token}` },
    data: { current_password: 'clave-temporal-1', new_password: 'MiClaveTecnico-77' },
  })
  expect(changed.ok()).toBeTruthy()

  const context = await browser.newContext({ storageState: { cookies: [], origins: [] } })
  const page = await context.newPage()
  await page.goto('/')
  await page.fill('input[type="email"]', email)
  await page.fill('input[type="password"]', 'MiClaveTecnico-77')
  await page.click('button[type="submit"]')
  await expect(page.getByRole('button', { name: 'Salir' })).toBeVisible({ timeout: 15000 })

  await page.goto('/ayuda')
  await expect(page.getByTestId('ayuda-paso-levantamiento')).toBeVisible()
  await expect(page.getByTestId('ayuda-paso-tecnico')).toBeVisible()
  // Lo de dinero y lo de la plataforma no se le muestra
  await expect(page.getByTestId('ayuda-paso-cotizacion-ia')).toHaveCount(0)
  await expect(page.getByTestId('ayuda-paso-precios-comparar')).toHaveCount(0)
  await expect(page.getByTestId('ayuda-paso-plataforma')).toHaveCount(0)
  await context.close()
})

test.describe('before signing in', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test('the login screen offers the tutorials, loaded only when opened', async ({ page }) => {
    let videoRequests = 0
    page.on('request', (r) => r.url().endsWith('.mp4') && videoRequests++)
    await page.goto('/login')
    await expect(page.getByTestId('video-01-entrar-al-sistema')).toHaveCount(0)

    await page.getByText('Aprende a usar el sistema').click()
    await expect(page.getByTestId('video-01-entrar-al-sistema')).toBeVisible()
    await expect(page.getByTestId('video-08-el-tecnico-en-el-iphone')).toBeVisible()
    await expect(page.locator('video').first()).toHaveAttribute('src', /\/videos\/01-entrar-al-sistema\.mp4$/)
    // Los videos no se descargan hasta que alguien pulsa reproducir (cuida los datos del teléfono)
    expect(videoRequests).toBe(0)
  })
})
