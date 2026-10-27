import { test, expect } from './fixtures'

// Si la app se rompe al abrir (p. ej. el teléfono guardó una versión vieja y ya no puede bajar una pantalla), el
// usuario ve qué pasó y cómo salir, en vez de una pantalla negra.
test('a screen that fails to load shows a recovery screen instead of a blank page', async ({ page }) => {
  // Ya hubo la recarga automática de esta sesión: aquí se prueba lo que ve el usuario cuando persiste
  await page.addInitScript(() => sessionStorage.setItem('multitec_reloaded', '1'))
  await page.route('**/*Dashboard*', (route) => route.abort())
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Algo salió mal al abrir la app' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Recargar' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Actualizar la app' })).toBeVisible()
  await expect(page.getByText('siguen guardados')).toBeVisible()
})
