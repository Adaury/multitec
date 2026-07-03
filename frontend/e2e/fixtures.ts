import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { test as base, expect, type Page } from '@playwright/test'

const dirname = path.dirname(fileURLToPath(import.meta.url))

export const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? 'admin@multitec.com'
export const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? 'change-this-password'
export const STORAGE_STATE_PATH = path.join(dirname, '.auth-state.json')

export async function login(page: Page, email = ADMIN_EMAIL, password = ADMIN_PASSWORD) {
  await page.goto('/')
  await page.fill('input[type="email"]', email)
  await page.fill('input[type="password"]', password)
  await page.click('button[type="submit"]')
  await expect(page.getByRole('heading', { name: 'Acciones rápidas' })).toBeVisible({ timeout: 15000 })
}

/** Nombre único por corrida, para que los tests no choquen entre sí ni con corridas previas. */
export function unique(label: string) {
  return `${label} ${Date.now()}-${Math.floor(Math.random() * 10000)}`
}

export { expect }
export const test = base
