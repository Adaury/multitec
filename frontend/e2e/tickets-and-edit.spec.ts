import { test, expect, unique } from './fixtures'
import { apiClient, createQuote } from './helpers'

// La tarjeta «Tickets abiertos» del Inicio lleva a la lista, y cada ticket abre su proyecto.
test('open tickets are listed and each one opens its project', async ({ page }) => {
  const api = await apiClient(page)
  const { client, project } = await createQuote(api, unique('Cliente Ticket'))
  const ticket = await api.post(`/projects/${project.id}/tickets`, { problem: 'La cámara del portón no da imagen' })

  await page.goto('/tickets')
  const card = page.getByRole('link', { name: new RegExp(ticket.code) })
  await expect(card).toContainText(client.name)
  await expect(card).toContainText('La cámara del portón no da imagen')
  await card.click()

  await expect(page).toHaveURL(new RegExp(`/proyectos/${project.id}\\?tab=tickets&ticket=${ticket.id}`))
  await expect(page.getByText(ticket.code)).toBeVisible()
})

// Una cotización aprobada no se cambia: «Editar» crea una copia pendiente y la abre para editar.
test('editing an approved quote creates an editable copy', async ({ page }) => {
  const api = await apiClient(page)
  const { project, quote } = await createQuote(api, unique('Cliente Copia'))
  await api.post(`/quotes/${quote.id}/approve`)

  await page.goto(`/proyectos/${project.id}?tab=cotizacion&cotizacion=${quote.id}`)
  await page.getByRole('toolbar', { name: `Acciones de ${quote.code}` }).getByRole('button', { name: 'Editar' }).click()
  await page.getByRole('button', { name: 'Crear copia y editar' }).click()
  await expect(page.getByRole('button', { name: 'Guardar cambios' })).toBeVisible()
})
