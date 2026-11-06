import { test, expect, unique } from './fixtures'
import { apiClient } from './helpers'

test('a partner added in the panel shows on the public home page with a link to its site', async ({ page }) => {
  const name = unique('Aliado Tecnología')
  const api = await apiClient(page)
  await api.post('/platform/site/partners', { name, description: 'Tecnología para oficinas y redes', url: 'www.ejemplo-aliado.com.do' })

  await page.goto('/web')
  const partners = page.getByTestId('partners')
  await expect(partners.getByText(name)).toBeVisible()
  await expect(partners.getByRole('link', { name: /Visitar sitio/ }).first()).toHaveAttribute('href', /^https:\/\//)

  await page.goto('/plataforma/sitio')
  await expect(page.locator(`input[value="${name}"]`)).toBeVisible()
})
