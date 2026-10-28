import { test, expect, unique } from './fixtures'
import { apiClient, makePng } from './helpers'

// Las fotos del teléfono suelen ser VERTICALES. El editor las muestra dentro de un recuadro más ancho; las posiciones de
// los puntos tienen que ser las de la FOTO (0 a 1 sobre su ancho y alto), no las del recuadro: el anexo de la cotización
// las dibuja sobre la foto real. Con una foto horizontal pequeña la diferencia casi no se notaba.
for (const [nombre, ancho, alto] of [
  ['vertical', 300, 400],
  ['muy vertical', 270, 600],
  ['horizontal', 400, 250],
] as const) {
  test(`points marked on a ${nombre} photo are saved at the position of the photo itself`, async ({ page }) => {
    const api = await apiClient(page)
    const client = await api.post('/clients', { name: unique('Cliente Foto Real') })
    const project = await api.post('/projects', { client_id: client.id, description: unique('Proyecto') })
    const upload = await page.request.post(`/api/projects/${project.id}/survey/assets`, {
      headers: api.headers,
      multipart: { kind: 'photo', file: { name: 'foto.png', mimeType: 'image/png', buffer: makePng(ancho, alto) } },
    })
    expect(upload.ok()).toBeTruthy()

    await page.goto(`/proyectos/${project.id}`)
    await page.getByRole('button', { name: 'Datos', exact: true }).click()
    await page.getByRole('button', { name: 'Levantamiento', exact: true }).click()
    await page.getByRole('button', { name: 'Marcar equipos en la foto' }).click()
    const imagen = page.getByAltText('Foto del levantamiento')
    await expect(imagen).toHaveJSProperty('complete', true)
    await expect.poll(async () => (await imagen.boundingBox())?.height ?? 0).toBeGreaterThan(50)

    // Donde está dibujada la foto de verdad (descontando los márgenes si el recuadro es más grande que ella). Se mide en
    // cada toque, como lo hace quien marca: la pantalla puede moverse entre un toque y otro.
    const dondeEstaLaFoto = () =>
      imagen.evaluate((img: HTMLImageElement) => {
        const caja = img.getBoundingClientRect()
        const escala = Math.min(caja.width / img.naturalWidth, caja.height / img.naturalHeight)
        const w = img.naturalWidth * escala
        const h = img.naturalHeight * escala
        return { x: caja.left + (caja.width - w) / 2, y: caja.top + (caja.height - h) / 2, w, h }
      })
    const posicionInicial = await dondeEstaLaFoto()
    // Dos toques en puntos conocidos de la foto
    for (const [fx, fy] of [[0.25, 0.3], [0.8, 0.7]]) {
      const foto = await dondeEstaLaFoto()
      await page.mouse.click(foto.x + foto.w * fx, foto.y + foto.h * fy)
    }
    // La foto no se movió al añadir el primer punto (la hoja del teléfono tiene altura fija)
    const posicionFinal = await dondeEstaLaFoto()
    expect(Math.abs(posicionFinal.y - posicionInicial.y)).toBeLessThan(2)
    await page.getByRole('button', { name: 'Guardar puntos' }).click()
    await expect(page.getByRole('button', { name: 'Marcar equipos en la foto' })).toContainText('2')

    const survey = await (await api.get(`/projects/${project.id}/survey`)).json()
    const guardados = survey.assets[0].markers as { x: number; y: number }[]
    expect(guardados).toHaveLength(2)
    expect(guardados[0].x).toBeCloseTo(0.25, 1)
    expect(guardados[0].y).toBeCloseTo(0.3, 1)
    expect(guardados[1].x).toBeCloseTo(0.8, 1)
    expect(guardados[1].y).toBeCloseTo(0.7, 1)
  })
}

test('a tap outside the photo (empty margin) does not create a point', async ({ page }) => {
  const api = await apiClient(page)
  const client = await api.post('/clients', { name: unique('Cliente Margen') })
  const project = await api.post('/projects', { client_id: client.id, description: unique('Proyecto') })
  const upload = await page.request.post(`/api/projects/${project.id}/survey/assets`, {
    headers: api.headers,
    multipart: { kind: 'photo', file: { name: 'foto.png', mimeType: 'image/png', buffer: makePng(270, 600) } },
  })
  expect(upload.ok()).toBeTruthy()
  await page.goto(`/proyectos/${project.id}`)
  await page.getByRole('button', { name: 'Datos', exact: true }).click()
  await page.getByRole('button', { name: 'Levantamiento', exact: true }).click()
  await page.getByRole('button', { name: 'Marcar equipos en la foto' }).click()
  await expect(page.getByAltText('Foto del levantamiento')).toHaveJSProperty('complete', true)
  const superficie = (await page.getByTestId('marker-surface').boundingBox())!
  const imagen = (await page.getByAltText('Foto del levantamiento').boundingBox())!
  // Toque a la izquierda de la foto, dentro del recuadro de la pantalla pero fuera de la foto
  if (imagen.x - superficie.x > 20) {
    await page.mouse.click(superficie.x + 5, superficie.y + superficie.height / 2)
  }
  await expect(page.getByPlaceholder('Nombre del punto')).toHaveCount(0)
})
