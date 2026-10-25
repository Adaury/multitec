import { test, expect } from './fixtures'

// En el navegador el menú es una columna de iconos que se abre al pasar el mouse; el pin lo deja abierto
// y se recuerda. En el teléfono no existe esta barra (hay barra inferior), por eso se fuerza un viewport ancho.
test.use({ viewport: { width: 1440, height: 900 } })

test('the desktop menu shrinks to icons, opens on hover and can be pinned open', async ({ page }) => {
  await page.goto('/')
  const nav = page.locator('aside')
  const clientes = nav.getByRole('link', { name: 'Clientes' })

  // Cerrado: solo iconos (el nombre sigue accesible, pero no se ve escrito).
  await page.mouse.move(900, 500)
  await expect(nav).toHaveCSS('width', '72px')
  await expect(nav.getByText('admin@multitec.com')).toHaveCount(0) // el pie con el correo solo aparece abierto

  // Al pasar el mouse se abre y muestra los nombres.
  await clientes.hover()
  await expect(nav).toHaveCSS('width', '256px')
  await expect(nav.getByText('admin@multitec.com')).toBeVisible()

  // Al irse el mouse se cierra solo.
  await page.mouse.move(900, 500)
  await expect(nav).toHaveCSS('width', '72px')

  // Fijado: queda abierto, el contenido se acomoda y se recuerda tras recargar.
  await clientes.hover()
  await page.getByRole('button', { name: 'Mantener el menú abierto' }).click()
  await page.mouse.move(900, 500)
  await expect(nav).toHaveCSS('width', '256px')
  await page.reload()
  await page.mouse.move(900, 500)
  await expect(nav).toHaveCSS('width', '256px')

  // Se puede volver a dejar que se cierre solo.
  await page.getByRole('button', { name: 'Dejar que el menú se cierre solo' }).click()
  await page.mouse.move(900, 500)
  await expect(nav).toHaveCSS('width', '72px')
})

test('the menu opens with the keyboard too', async ({ page }) => {
  await page.goto('/')
  const nav = page.locator('aside')
  await nav.getByRole('link', { name: 'Inicio' }).focus()
  await expect(nav).toHaveCSS('width', '256px')
})
