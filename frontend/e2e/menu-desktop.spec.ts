import { test, expect } from './fixtures'

// En el navegador el menú es una columna de iconos que se abre al pasar el mouse; el pin lo deja abierto
// y se recuerda. En el teléfono no existe esta barra (hay barra inferior), por eso se fuerza un viewport ancho.
test.use({ viewport: { width: 1440, height: 900 } })

test('the desktop menu hides completely, shows near the left edge or with the menu button, and can be pinned', async ({
  page,
}) => {
  await page.goto('/')
  const nav = page.locator('aside')
  const hidden = async () => (await nav.evaluate((el) => el.getBoundingClientRect().right)) <= 1

  // Con el mouse lejos, el menú no se ve en absoluto.
  await page.mouse.move(900, 500)
  await expect.poll(hidden).toBe(true)
  await expect(nav.getByText('admin@multitec.com')).toHaveCount(0)

  // Al acercar el mouse al borde izquierdo aparece entero, con los nombres.
  await page.mouse.move(2, 400)
  await expect.poll(hidden).toBe(false)
  await expect(nav.getByRole('link', { name: 'Clientes' })).toBeVisible()
  await expect(nav.getByText('admin@multitec.com')).toBeVisible()

  // Al alejarse se oculta otra vez, aunque se haya hecho clic en una opción.
  await nav.getByRole('link', { name: 'Clientes' }).click()
  await page.mouse.move(900, 500)
  await expect.poll(hidden).toBe(true)

  // También se abre con el botón ☰ de arriba.
  await page.getByRole('button', { name: 'Abrir menú' }).click()
  await expect.poll(hidden).toBe(false)

  // Fijado: queda abierto con el mouse lejos y se recuerda tras recargar.
  await page.getByRole('button', { name: 'Mantener el menú abierto' }).click()
  await page.mouse.move(900, 500)
  await expect.poll(hidden).toBe(false)
  await page.reload()
  await page.mouse.move(900, 500)
  await expect.poll(hidden).toBe(false)

  // Se puede volver a dejar que se oculte solo.
  await page.getByRole('button', { name: 'Dejar que el menú se cierre solo' }).click()
  await page.mouse.move(900, 500)
  await expect.poll(hidden).toBe(true)
})

test('the menu opens with the keyboard too', async ({ page }) => {
  await page.goto('/')
  const nav = page.locator('aside')
  await page.mouse.move(900, 500)
  await nav.getByRole('link', { name: 'Inicio' }).focus()
  await expect.poll(async () => nav.evaluate((el) => el.getBoundingClientRect().right)).toBeGreaterThan(100)
})
