import { test, expect, unique } from './fixtures'

test('create a client and a project for it', async ({ page }) => {
  const clientName = unique('Cliente E2E')
  const description = unique('Proyecto E2E')

  await page.goto('/clientes')
  await page.click('button:has-text("+ Nuevo")')
  await page.locator('label:has-text("Nombre") input').fill(clientName)
  await page.click('button:has-text("Guardar cliente")')
  await expect(page.getByText(clientName)).toBeVisible({ timeout: 10000 })

  await page.click(`text=${clientName}`)
  await expect(page).toHaveURL(/\/clientes\/\d+/)

  await page.goto('/proyectos')
  await page.click('button:has-text("+ Nuevo")')
  await page.locator('label:has-text("Cliente") select').selectOption({ label: clientName })
  await page.locator('label:has-text("Descripción") textarea').fill(description)
  await page.click('button:has-text("Crear proyecto")')

  const projectCard = page.locator('a', { hasText: description })
  await expect(projectCard).toBeVisible({ timeout: 10000 })

  await projectCard.click()
  await expect(page).toHaveURL(/\/proyectos\/\d+/)
  await expect(page.getByText(clientName).first()).toBeVisible()
})
