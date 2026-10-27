import { test, expect, unique } from './fixtures'
import { apiClient } from './helpers'

// Subir la cotización de otro y verla comparada con la propia y con el levantamiento. La lectura con IA (Ollama) se
// simula: lo que se prueba aquí es lo que ve y puede hacer oficina.
test('upload another quote and see it compared line by line and against the survey points', async ({ page }) => {
  const api = await apiClient(page)
  const client = await api.post('/clients', { name: unique('Cliente Comparar') })
  const project = await api.post('/projects', { client_id: client.id, description: unique('Proyecto Comparar') })
  await api.post(`/projects/${project.id}/quotes`, {
    items: [{ description: 'Cámara domo IP 4MP', quantity: 4, unit_price: 4500 }],
  })

  const line = (description: string, quantity: number, unit_price: number) => ({ description, quantity, unit_price })
  const comparison = {
    id: 1,
    project_id: project.id,
    label: 'Competidor X',
    filename: 'cotizacion.pdf',
    file_path: null,
    quote_id: null,
    created_at: new Date().toISOString(),
    items: [line('Camara domo IP 4MP Hikvision', 6, 4200), line('Router WiFi 6', 1, 3500)],
    total: 60000,
    matched: [
      {
        external: line('Camara domo IP 4MP Hikvision', 6, 4200),
        ours: line('Cámara domo IP 4MP', 4, 4500),
        same_quantity: false,
        price: 'mas_barato',
        price_diff_pct: -6.7,
        status: 'diferente',
      },
    ],
    only_external: [line('Router WiFi 6', 1, 3500)],
    only_ours: [],
    coverage: [
      { kind: 'camara', label: 'Cámara', marked: 5, external: 6, ours: 4, external_status: 'sobra', ours_status: 'falta' },
    ],
    totals: { external_subtotal: 28700, external_total: 60000, our_subtotal: 18000, our_total: 21240, our_code: 'COT-000001' },
  }
  await page.route(`**/api/projects/${project.id}/comparisons`, (route) =>
    route.request().method() === 'POST'
      ? route.fulfill({ status: 201, json: comparison })
      : route.fulfill({ json: [{ id: 1, label: 'Competidor X', filename: 'cotizacion.pdf', created_at: comparison.created_at, lines: 2 }] }),
  )

  await page.goto(`/proyectos/${project.id}`)
  await page.getByRole('button', { name: 'Comercial', exact: true }).click()
  await page.getByRole('button', { name: 'Cotización', exact: true }).click()
  await page.getByRole('button', { name: /Comparar con otra cotización/ }).click()

  // Sin etiqueta y sin archivo o texto no se puede subir
  const submit = page.getByRole('button', { name: 'Subir y comparar' })
  await expect(submit).toBeDisabled()
  await page.getByPlaceholder(/Competidor, Proveedor X/).fill('Competidor X')
  await page.getByLabel('…o pega el texto de la cotización').fill('Camara domo IP 4MP Hikvision 6 x 4200\nRouter WiFi 6 1 x 3500')
  await expect(submit).toBeEnabled()
  await submit.click()

  const result = page.getByTestId('comparison-result')
  await expect(result).toContainText('Competidor X')
  // Contra el levantamiento: marcó 5 cámaras; la otra trae 6 (sobra) y la tuya 4 (falta)
  const coverage = page.getByTestId('comparison-coverage')
  await expect(coverage).toContainText('5 marcados')
  await expect(coverage).toContainText('Sobra')
  await expect(coverage).toContainText('Falta')
  // Línea por línea
  await expect(page.getByTestId('comparison-matched')).toContainText('Cantidad distinta')
  await expect(page.getByTestId('comparison-matched')).toContainText('6.7% más barato')
  await expect(result).toContainText('Solo en la otra cotización')
  await expect(result).toContainText('1 × Router WiFi 6')

  // Se puede corregir lo que leyó la IA
  await result.getByRole('button', { name: 'Corregir lo que leyó la IA' }).click()
  await expect(page.getByTestId('comparison-edit').getByLabel('Descripción de la línea 1')).toHaveValue(
    'Camara domo IP 4MP Hikvision',
  )
})
