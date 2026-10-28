import { test, expect } from './fixtures'

test.use({ storageState: { cookies: [], origins: [] } })

// Una pantalla vacía sin ningún mensaje es lo peor que le puede pasar a alguien en la obra: si la app no arranca, se avisa
// con el error y se manda al servidor para poder leerlo.
test('if the app never starts, a recovery notice appears and the error is reported to the server', async ({ page }) => {
  const reports: unknown[] = []
  await page.route('**/api/client-errors', async (route) => {
    reports.push(route.request().postDataJSON())
    await route.fulfill({ status: 204 })
  })
  // El programa principal no llega (red caída a medias, archivo viejo…): #root queda vacío
  await page.route(/\/src\/main\.tsx|\/assets\/index-[^/]+\.js$/, (route) => route.abort())

  await page.goto('/login')
  const aviso = page.getByRole('alert')
  await expect(aviso).toContainText('No se pudo abrir la aplicación', { timeout: 15000 })
  await expect(aviso.getByRole('button', { name: 'Recargar' })).toBeVisible()
  await expect(aviso.getByRole('button', { name: 'Actualizar la app' })).toBeVisible()

  await expect.poll(() => reports.length, { timeout: 5000 }).toBeGreaterThan(0)
  // Dice cuál archivo no cargó y que la pantalla no arrancó
  expect(reports).toContainEqual(expect.objectContaining({ kind: 'recurso', message: expect.stringMatching(/^no cargó .*(main\.tsx|index-)/) }))
  await expect.poll(() => reports.some((r) => (r as { kind: string }).kind === 'no-arranco'), { timeout: 15000 }).toBe(true)
})

test('the notice goes away by itself when the app was only slow', async ({ page }) => {
  let release!: () => void
  const gate = new Promise<void>((resolve) => (release = resolve))
  await page.route(/\/src\/main\.tsx|\/assets\/index-[^/]+\.js$/, async (route) => {
    await gate
    await route.continue()
  })
  await page.goto('/login', { waitUntil: 'commit' })
  await expect(page.getByRole('alert')).toContainText('No se pudo abrir la aplicación', { timeout: 15000 })
  release()
  await expect(page.getByRole('button', { name: 'Ingresar' })).toBeVisible({ timeout: 15000 })
  await expect(page.getByRole('alert')).toHaveCount(0)
})

test('blocked browser storage (private mode, restrictions) does not leave a blank screen', async ({ page }) => {
  await page.addInitScript(() => {
    const blocked = () => {
      throw new DOMException('The operation is insecure.', 'SecurityError')
    }
    Storage.prototype.getItem = blocked
    Storage.prototype.setItem = blocked
    Storage.prototype.removeItem = blocked
  })
  await page.goto('/login')
  await expect(page.getByRole('button', { name: 'Ingresar' })).toBeVisible({ timeout: 15000 })
})
