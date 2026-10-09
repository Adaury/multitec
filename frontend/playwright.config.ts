import { defineConfig, devices } from '@playwright/test'
import { STORAGE_STATE_PATH } from './e2e/fixtures'
import {
  E2E_API_PORT,
  E2E_DEFAULT_ADMIN_PASSWORD,
  E2E_TMP_DIR,
  E2E_WEB_PORT,
  ISOLATED,
} from './e2e/isolated'

const baseURL = ISOLATED ? `http://localhost:${E2E_WEB_PORT}` : (process.env.E2E_BASE_URL ?? 'http://localhost:5173')
const adminPassword = process.env.E2E_ADMIN_PASSWORD ?? E2E_DEFAULT_ADMIN_PASSWORD

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  globalSetup: './e2e/global-setup.ts',
  globalTeardown: './e2e/global-teardown.ts',
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    // La mayoría de los specs arrancan con sesión ya iniciada (ver global-setup.ts) para
    // no agotar el rate limit de /api/auth/login corriendo toda la suite. auth.spec.ts
    // pisa esto con storageState vacío porque necesita probar el login/logout real.
    storageState: STORAGE_STATE_PATH,
  },
  // Modo aislado: backend y frontend propios (puertos 8100/5190, base SQLite temporal) para
  // no tocar la base de desarrollo. reuseExistingServer=false a propósito: si alguien ya
  // ocupa esos puertos, es mejor fallar que conectarse a un servidor con datos reales.
  webServer: ISOLATED
    ? [
        {
          command: 'node e2e/scripts/start-backend.mjs',
          url: `http://127.0.0.1:${E2E_API_PORT}/api/health`,
          reuseExistingServer: false,
          timeout: 120_000,
          env: {
            E2E_TMP_DIR,
            E2E_API_PORT: String(E2E_API_PORT),
            E2E_ADMIN_PASSWORD: adminPassword,
          },
        },
        {
          command: `npx vite --port ${E2E_WEB_PORT} --strictPort`,
          url: `http://localhost:${E2E_WEB_PORT}`,
          reuseExistingServer: false,
          timeout: 120_000,
          env: { E2E_API_TARGET: `http://127.0.0.1:${E2E_API_PORT}` },
        },
      ]
    : undefined,
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 430, height: 932 } },
    },
  ],
})
