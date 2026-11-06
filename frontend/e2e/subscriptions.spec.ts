import { test, expect, unique } from './fixtures'
import { apiClient } from './helpers'

const PASSWORD = 'Registro-E2E-2026'

test.describe('registro público', () => {
  // Sin sesión: lo que ve una empresa nueva.
  test.use({ storageState: { cookies: [], origins: [] } })

  test('the public home page shows the plans and leads to signup with the plan chosen', async ({ page }) => {
    await page.goto('/web')
    await expect(page.getByRole('heading', { name: /cámaras, alarmas y cercos eléctricos/ })).toBeVisible()
    const pricing = page.getByTestId('pricing')
    await expect(pricing.getByText('Más popular')).toBeVisible()
    await expect(pricing.getByText('US$40')).toBeVisible()
    await pricing.getByRole('link', { name: /Probar/ }).first().click()
    await expect(page).toHaveURL(/\/registro\?plan=\d+/)
    await expect(page.getByTestId('plan-picker').getByRole('radio', { name: /Básico/ })).toBeChecked()
  })

  test('a company signs up alone and lands inside its own account', async ({ page }) => {
    const company = unique('Seguridad Registro')
    const email = `${unique('registro').toLowerCase().replace(/[^a-z0-9]/g, '')}@e2e.com`
    await page.goto('/login')
    await page.getByRole('link', { name: 'Pruébalo gratis' }).click()
    await expect(page).toHaveURL(/\/registro$/)
    // Planes en dólares, como en ZuraPOS; el destacado viene marcado.
    const picker = page.getByTestId('plan-picker')
    await expect(picker.getByText('US$60')).toBeVisible()
    await expect(picker.getByRole('radio', { checked: true })).toHaveCount(1)

    await page.getByLabel('Nombre de la empresa').fill(company)
    await page.getByLabel('Tu nombre').fill('Ana Registro')
    await page.getByLabel('Correo').fill(email)
    await page.getByLabel('Teléfono / WhatsApp').fill('809-555-0101')
    await page.getByLabel(/Contraseña/).fill(PASSWORD)
    const submit = page.getByRole('button', { name: /días gratis/ })
    await expect(submit).toBeDisabled()
    await page.getByRole('checkbox').check()
    await submit.click()

    await expect(page).toHaveURL(/\/(\?bienvenida=1)?$/, { timeout: 60_000 })
    await expect(page.getByText(company).filter({ visible: true }).first()).toBeVisible()
    await page.goto('/suscripcion')
    await expect(page.getByText('En prueba gratis')).toBeVisible()
  })
})

test('platform support enters a company read-only and returns to the panel', async ({ page }) => {
  const company = unique('Empresa Soporte')
  const email = `${unique('soporte').toLowerCase().replace(/[^a-z0-9]/g, '')}@e2e.com`
  const signup = await page.request.post('/api/signup', {
    data: { company_name: company, admin_name: 'Luis Soporte', email, phone: '829-555-0202', password: PASSWORD, accept_terms: true },
  })
  expect(signup.ok(), await signup.text()).toBeTruthy()

  const api = await apiClient(page)
  const companies = (await (await api.get('/platform/companies')).json()) as { id: number; name: string }[]
  const target = companies.find((c) => c.name === company)!

  await page.goto(`/plataforma/${target.id}`)
  await expect(page.getByTestId('billing')).toBeVisible()
  page.once('dialog', (d) => d.accept())
  await page.getByRole('button', { name: 'Entrar como soporte' }).click()

  const banner = page.getByTestId('support-banner')
  await expect(banner).toContainText(`Modo soporte — ${company}`)
  await expect(banner).toContainText('solo lectura')
  await banner.getByRole('button', { name: 'Salir del soporte' }).click()
  await expect(page).toHaveURL(new RegExp(`/plataforma/${target.id}$`))
  await expect(page.getByTestId('support-banner')).toHaveCount(0)
})
