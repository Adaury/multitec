import { defineConfig, devices } from '@playwright/test'
import { STORAGE_STATE_PATH } from './e2e/fixtures'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  globalSetup: './e2e/global-setup.ts',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    // La mayoría de los specs arrancan con sesión ya iniciada (ver global-setup.ts) para
    // no agotar el rate limit de /api/auth/login corriendo toda la suite. auth.spec.ts
    // pisa esto con storageState vacío porque necesita probar el login/logout real.
    storageState: STORAGE_STATE_PATH,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 430, height: 932 } },
    },
  ],
})
