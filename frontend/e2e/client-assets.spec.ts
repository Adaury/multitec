import { test, expect, unique } from './fixtures'
import { apiClient } from './helpers'

test('register an installed device with serial and MAC, edit it and remove it', async ({ page }) => {
  const api = await apiClient(page)
  const client = await api.post('/clients', { name: unique('Cliente equipos') })

  await page.goto(`/clientes/${client.id}`)
  await expect(page.getByRole('heading', { name: /Equipos instalados/ })).toBeVisible()
  await expect(page.getByText('Aún no hay equipos registrados')).toBeVisible()

  await page.getByRole('button', { name: /Agregar equipo/ }).click()
  await page.locator('label:has-text("Nombre o descripción") input').fill('Cámara domo entrada')
  await page.locator('label:has-text("Marca") input').fill('Hikvision')
  await page.locator('label:has-text("Serial") input').fill('SN-12345')
  await page.locator('label:has-text("MAC") input').fill('aa-bb-cc-dd-ee-ff')
  await page.locator('label:has-text("Ubicación en el sitio") input').fill('Entrada principal')
  await page.locator('label:has-text("Garantía hasta") input').fill('2020-01-01')
  await page.getByRole('button', { name: 'Guardar equipo' }).click()

  const card = page.locator('div.rounded-3xl', { hasText: 'Cámara domo entrada' })
  await expect(card).toBeVisible({ timeout: 10000 })
  await expect(card.getByText('AA:BB:CC:DD:EE:FF')).toBeVisible() // la MAC se normaliza
  await expect(card.getByText('SN-12345')).toBeVisible()
  await expect(card.getByText('Garantía vencida')).toBeVisible()

  await card.getByRole('button', { name: 'Editar' }).click()
  await page.locator('label:has-text("Ubicación en el sitio") input').fill('Parqueo')
  await page.getByRole('button', { name: 'Guardar equipo' }).click()
  await expect(card.getByText('Ubicación: Parqueo')).toBeVisible({ timeout: 10000 })

  page.once('dialog', (dialog) => dialog.accept())
  await card.getByRole('button', { name: 'Quitar' }).click()
  await expect(page.getByText('Cámara domo entrada')).toHaveCount(0, { timeout: 10000 })
})

test('an invalid MAC shows a readable error', async ({ page }) => {
  const api = await apiClient(page)
  const client = await api.post('/clients', { name: unique('Cliente mac') })
  await page.goto(`/clientes/${client.id}`)
  await page.getByRole('button', { name: /Agregar equipo/ }).click()
  await page.locator('label:has-text("Nombre o descripción") input').fill('Equipo')
  await page.locator('label:has-text("MAC") input').fill('no-es-una-mac')
  await page.getByRole('button', { name: 'Guardar equipo' }).click()
  await expect(page.getByText(/12 dígitos hexadecimales/)).toBeVisible({ timeout: 10000 })
})
