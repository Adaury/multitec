import { test, expect, unique } from './fixtures'

test.use({
  geolocation: { latitude: 18.4861, longitude: -69.9312 },
  permissions: ['geolocation'],
})

// Lo que le pasa a un técnico en la obra: señal que se corta a medias, Wi-Fi sin internet, acciones que fallan.

test('requests have a time limit (a half-dead connection no longer hangs forever), longer for the AI and photo uploads', async ({
  page,
}) => {
  await page.goto('/')
  const tiempos = await page.evaluate(async () => {
    const { api } = await import('/src/lib/api.ts')
    // Un adaptador que devuelve la configuración tal como queda DESPUÉS de los interceptores
    const adapter = async (config: { timeout?: number }) => ({
      data: config.timeout,
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
    const medir = async (peticion: Promise<{ data: unknown }>) => (await peticion).data
    const form = new FormData()
    form.append('kind', 'photo')
    return {
      normal: await medir(api.get('/clients', { adapter } as never)),
      ia: await medir(api.post('/ai/ask', {}, { adapter } as never)),
      transcribir: await medir(api.post('/projects/1/survey/assets/2/transcribe', {}, { adapter } as never)),
      foto: await medir(api.post('/projects/1/survey/assets', form, { adapter } as never)),
      propio: await medir(api.get('/clients', { adapter, timeout: 5000 } as never)),
    }
  })
  expect(tiempos).toEqual({ normal: 45000, ia: 300000, transcribir: 300000, foto: 180000, propio: 5000 })
})

test('a retry after a lost response does not create the project twice', async ({ page }) => {
  await page.goto('/')
  const clientName = unique('Cliente Reintento')
  const servidor = { proyectos: [] as { id: number; client_id: number; survey_type: string | null; created_at: string }[], crearProyecto: 0 }
  let perderRespuesta = true

  await page.route('**/api/clients', (route) =>
    route.request().method() === 'GET'
      ? route.fulfill({ json: [{ id: 7, name: clientName }] })
      : route.fulfill({ status: 201, json: { id: 7, name: clientName } }),
  )
  await page.route('**/api/projects', async (route) => {
    if (route.request().method() === 'GET') return route.fulfill({ json: servidor.proyectos })
    // El servidor SÍ crea el proyecto, pero la respuesta se pierde (se fue la señal justo ahí)
    servidor.crearProyecto += 1
    servidor.proyectos.push({ id: 99, client_id: 7, survey_type: 'Alarma', created_at: new Date().toISOString() })
    if (perderRespuesta) return route.abort('failed')
    return route.fulfill({ status: 201, json: servidor.proyectos[0] })
  })
  await page.route('**/api/projects/99/survey', (route) => route.fulfill({ json: {} }))

  const resultado = await page.evaluate(async (nombre) => {
    const { addPendingSurvey, listPendingSurveys } = await import('/src/lib/offlineQueue.ts')
    const { syncPendingSurveys } = await import('/src/lib/syncPending.ts')
    await addPendingSurvey({
      clientName: nombre,
      phone: '',
      surveyType: 'Alarma',
      address: '',
      locationUrl: '',
      notes: 'dos sensores',
      photos: [],
    })
    const primero = await syncPendingSurveys() // la respuesta se pierde: queda pendiente, sin marcarse como rechazado
    const pendiente = (await listPendingSurveys())[0]
    return { primero, marcado: pendiente?.creatingProject, error: pendiente?.lastError ?? null }
  }, clientName)
  expect(resultado.primero.offline).toBe(true)
  expect(resultado.marcado).toBe(true)
  expect(resultado.error).toBeNull()

  // Vuelve la señal: el reintento encuentra el proyecto que ya existe en vez de crear otro
  perderRespuesta = false
  const segundo = await page.evaluate(async () => {
    const { syncPendingSurveys } = await import('/src/lib/syncPending.ts')
    const { listPendingSurveys } = await import('/src/lib/offlineQueue.ts')
    return { r: await syncPendingSurveys(), quedan: (await listPendingSurveys()).length }
  })
  expect(segundo).toEqual({ r: { sent: 1, failed: 0, offline: false }, quedan: 0 })
  expect(servidor.crearProyecto).toBe(1) // un solo proyecto, no dos
})

test('an action that fails without its screen handling it shows a warning instead of failing silently', async ({ page }) => {
  await page.goto('/')
  await page.evaluate(async () => {
    const { queryClient } = await import('/src/lib/queryClient.ts')
    const falla = (detail: string) => async () => {
      throw Object.assign(new Error('x'), { response: { status: 400, data: { detail } } })
    }
    const cache = queryClient.getMutationCache()
    // Sin manejo propio: debe avisar
    cache.build(queryClient, { mutationFn: falla('No se pudo guardar: el cliente ya existe') }).execute(undefined).catch(() => {})
    // Con su propio onError: no se duplica el aviso
    cache
      .build(queryClient, { mutationFn: falla('Este error lo cuenta su pantalla'), onError: () => {} })
      .execute(undefined)
      .catch(() => {})
  })
  const aviso = page.getByRole('alert').filter({ hasText: 'No se pudo guardar: el cliente ya existe' })
  await expect(aviso).toBeVisible()
  await expect(page.getByText('Este error lo cuenta su pantalla')).toHaveCount(0)
  await aviso.getByRole('button', { name: 'Cerrar aviso' }).click()
  await expect(aviso).toHaveCount(0)
})

test('with Wi-Fi but no server, the quick survey moves to the offline form and keeps what was typed', async ({ page }) => {
  const name = unique('Cliente Wifi Sin Internet')
  await page.goto('/nuevo')
  await expect(page.getByText('Soy tu asistente de levantamientos')).toBeVisible()
  await page.locator('input[role="combobox"]').fill(name)
  await page.getByRole('option', { name: /Crear cliente nuevo/ }).click()
  await page.getByLabel('¿Cuál es su número de teléfono?').fill('8095559999')
  await page.getByRole('button', { name: 'Siguiente' }).click()
  await page.getByRole('button', { name: 'Alarma' }).click()

  // El teléfono cree que tiene red (navigator.onLine), pero el servidor no responde
  await page.route('**/api/clients', (route) => (route.request().method() === 'POST' ? route.abort('failed') : route.continue()))
  await page.getByRole('button', { name: /Comenzar levantamiento/ }).click()

  await expect(page.getByText('📴 Sin conexión')).toBeVisible({ timeout: 15000 })
  await expect(page.getByLabel('Cliente')).toHaveValue(name)
  await expect(page.getByLabel('Teléfono')).toHaveValue('809-555-9999')
  await page.getByLabel('Notas del levantamiento').fill('Notas escritas sin servidor')
  await page.getByRole('button', { name: 'Guardar para enviar después' }).click()
  await expect(page.getByText(/Guardado en el teléfono \(1\)/)).toBeVisible()

  // Si ya hay conexión, se puede volver a intentar sin esperar
  await expect(page.getByRole('button', { name: /Ya tengo conexión/ })).toBeVisible()
})
