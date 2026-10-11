import { test, expect, unique } from './fixtures'

test('project screen on a phone: grouped sections, folded map and quick contact actions', async ({ page }) => {
  await page.goto('/')
  const token = await page.evaluate(() => localStorage.getItem('multitec_token'))
  const headers = { Authorization: `Bearer ${token}` }
  const post = async (url: string, data?: unknown) => {
    const res = await page.request.post(`/api${url}`, { headers, data })
    expect(res.ok(), `${url} -> ${res.status()} ${await res.text()}`).toBeTruthy()
    return res.json()
  }
  const client = await post('/clients', { name: unique('Cliente Movil'), phone: '809-555-1234' })
  const project = await post('/projects', {
    client_id: client.id,
    description: 'Videovigilancia de nave',
    survey_type: 'Cámaras de seguridad (CCTV)',
    location_url: 'https://www.google.com/maps?q=18.486100,-69.931200',
  })

  await page.goto(`/proyectos/${project.id}`)

  // Acciones rápidas del cliente, y qué tipo de trabajo es.
  await expect(page.getByRole('link', { name: /Llamar/ })).toHaveAttribute('href', 'tel:8095551234')
  await expect(page.getByRole('link', { name: /WhatsApp/ })).toHaveAttribute('href', 'https://wa.me/18095551234')
  await expect(page.getByText('Cámaras de seguridad (CCTV)').first()).toBeVisible()

  // El mapa arranca plegado; "Cómo llegar" sigue a un toque.
  await expect(page.getByRole('link', { name: /Cómo llegar/ })).toBeVisible()
  await expect(page.locator('iframe[title="Mapa de la ubicación"]')).toHaveCount(0)
  await page.getByRole('button', { name: /Ver mapa/ }).click()
  await expect(page.locator('iframe[title="Mapa de la ubicación"]')).toHaveCount(1)
  await page.getByRole('button', { name: /Ocultar mapa/ }).click()
  await expect(page.locator('iframe[title="Mapa de la ubicación"]')).toHaveCount(0)

  // Cuatro grupos que caben en el ancho de la pantalla, sin deslizar.
  const nav = page.getByRole('navigation', { name: 'Secciones del proyecto' })
  for (const phase of ['Datos', 'Comercial', 'Obra', 'Facturación']) {
    await expect(nav.getByRole('button', { name: phase, exact: true })).toBeVisible()
  }
  const viewport = page.viewportSize()!
  const navBox = (await nav.boundingBox())!
  // Completo y por encima de la barra inferior de navegación (~100 px), sin hacer scroll.
  expect(navBox.y + navBox.height).toBeLessThan(viewport.height - 100)
  expect(navBox.x + navBox.width).toBeLessThanOrEqual(viewport.width)

  // Dentro de cada grupo, sus pestañas.
  await expect(nav.getByRole('button', { name: 'Levantamiento', exact: true })).toBeVisible()
  await nav.getByRole('button', { name: 'Obra', exact: true }).click()
  for (const tab of ['Compras', 'Ejecución', 'Bitácora', 'Tickets']) {
    await expect(nav.getByRole('button', { name: tab, exact: true })).toBeVisible()
  }
  await nav.getByRole('button', { name: 'Facturación', exact: true }).click()
  await expect(nav.getByRole('button', { name: 'Prefactura', exact: true })).toBeVisible()
  await expect(nav.getByRole('button', { name: 'Factura', exact: true })).toBeVisible()

  // La URL con ?tab= sigue abriendo la pestaña correcta, y resalta su grupo.
  await page.goto(`/proyectos/${project.id}?tab=cotizacion`)
  await expect(
    page.getByRole('navigation', { name: 'Secciones del proyecto' }).getByRole('button', { name: 'Comercial', exact: true }),
  ).toHaveAttribute('aria-current', 'true')
})
