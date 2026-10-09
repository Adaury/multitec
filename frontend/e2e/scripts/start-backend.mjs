// Backend aislado para los tests E2E locales: SQLite nueva en una carpeta temporal, admin
// sembrado con una contraseña desechable y SMTP apagado. NUNCA toca backend/.env ni la base
// real — las variables de entorno de este proceso pisan al .env (pydantic-settings les da
// prioridad). Lo lanza el bloque `webServer` de playwright.config.ts.
import { spawn, spawnSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const dirname = path.dirname(fileURLToPath(import.meta.url))
const backendDir = path.resolve(dirname, '../../../backend')

const tmpDir = process.env.E2E_TMP_DIR
const port = process.env.E2E_API_PORT
const adminPassword = process.env.E2E_ADMIN_PASSWORD
if (!tmpDir || !port || !adminPassword) {
  console.error('start-backend: faltan E2E_TMP_DIR / E2E_API_PORT / E2E_ADMIN_PASSWORD')
  process.exit(1)
}

// Corrida limpia: se borra lo que haya dejado una corrida anterior.
fs.rmSync(tmpDir, { recursive: true, force: true })
fs.mkdirSync(path.join(tmpDir, 'uploads'), { recursive: true })

const venvPython =
  process.platform === 'win32'
    ? path.join(backendDir, 'venv', 'Scripts', 'python.exe')
    : path.join(backendDir, 'venv', 'bin', 'python')
const python = process.env.E2E_PYTHON ?? (fs.existsSync(venvPython) ? venvPython : 'python')

const env = {
  ...process.env,
  DATABASE_URL: `sqlite:///${path.join(tmpDir, 'e2e.db').replace(/\\/g, '/')}`,
  UPLOAD_DIR: path.join(tmpDir, 'uploads'),
  JWT_SECRET: 'e2e-test-secret-not-for-production',
  ENVIRONMENT: 'development',
  ADMIN_EMAIL: 'admin@multitec.com',
  ADMIN_PASSWORD: adminPassword,
  // Sin SMTP ni claves reales: los correos solo se registran en el log (modo consola).
  SMTP_HOST: '',
  ANTHROPIC_API_KEY: '',
}

function run(args) {
  const result = spawnSync(python, args, { cwd: backendDir, env, stdio: 'inherit' })
  if (result.status !== 0) {
    console.error(`start-backend: falló "python ${args.join(' ')}"`)
    process.exit(result.status ?? 1)
  }
}

run(['-m', 'alembic', 'upgrade', 'head'])
run(['-m', 'app.db.seed'])

const server = spawn(python, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', port], {
  cwd: backendDir,
  env,
  stdio: 'inherit',
})
server.on('exit', (code) => process.exit(code ?? 0))
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => server.kill())
}
process.on('exit', () => server.kill())
