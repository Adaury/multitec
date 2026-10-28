// Graba la guía en video: recorre la app (entorno aislado, datos de ejemplo) con cursor visible y subtítulos.
// Escribe out/admin.webm, out/tech.webm y out/timeline.json (cuándo empieza cada escena y qué tramos se aceleran).
import { createRequire } from 'node:module'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const require = createRequire(import.meta.url)
const { chromium, devices } = require('@playwright/test')
const here = path.dirname(fileURLToPath(import.meta.url))
const OUT = path.join(here, 'out')
fs.mkdirSync(OUT, { recursive: true })
const BASE = 'http://localhost:5480'
const API = 'http://127.0.0.1:8400'
const ADMIN = { email: 'admin@multitec.com', password: 'Guia-Video-2026x' }
const PHOTO = path.join(here, 'fachada.png')

const scenes = JSON.parse(fs.readFileSync(path.join(here, 'scenes.json'), 'utf8'))
const byId = Object.fromEntries(scenes.map((s) => [s.id, s]))

function wavSeconds(id) {
  const buf = fs.readFileSync(path.join(here, 'wav', `${id}.wav`))
  const byteRate = buf.readUInt32LE(28)
  const dataAt = buf.indexOf('data')
  return buf.readUInt32LE(dataAt + 4) / byteRate
}

const OVERLAY = `
(() => {
  if (window.__overlay) return; window.__overlay = true;
  const css = \`
  #__cap{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);width:max-content;max-width:88%;background:rgba(10,20,40,.9);color:#fff;
    font:600 24px/1.35 system-ui,'Segoe UI',sans-serif;padding:14px 24px;border-radius:14px;z-index:2147483647;text-align:center;
    box-shadow:0 6px 24px rgba(0,0,0,.4);pointer-events:none;opacity:0;transition:opacity .25s}
  #__cap.on{opacity:1}
  #__cap.fast{background:rgba(180,90,0,.92)}
  #__cur{position:fixed;left:-50px;top:-50px;width:26px;height:26px;margin:-13px 0 0 -13px;border-radius:50%;background:rgba(255,80,60,.55);
    border:3px solid #fff;z-index:2147483646;pointer-events:none;box-shadow:0 0 0 2px rgba(255,80,60,.7)}
  .__rip{position:fixed;width:20px;height:20px;margin:-10px 0 0 -10px;border-radius:50%;border:4px solid #ff503c;z-index:2147483645;
    pointer-events:none;animation:__r .6s ease-out forwards}
  @keyframes __r{to{transform:scale(4);opacity:0}}
  @media (max-width:600px){#__cap{font-size:15px;padding:9px 13px;bottom:auto;top:56px;max-width:94%}}\`;
  const mount = () => {
    const style = document.createElement('style'); style.textContent = css; document.head.append(style);
    const cap = document.createElement('div'); cap.id = '__cap'; document.body.append(cap);
    const cur = document.createElement('div'); cur.id = '__cur'; document.body.append(cur);
    window.__cap = (text, fast) => { cap.textContent = text; cap.className = (text ? 'on ' : '') + (fast ? 'fast' : '') };
    document.addEventListener('mousemove', (e) => { cur.style.left = e.clientX + 'px'; cur.style.top = e.clientY + 'px' }, true);
    document.addEventListener('mousedown', (e) => {
      const r = document.createElement('div'); r.className = '__rip'; r.style.left = e.clientX + 'px'; r.style.top = e.clientY + 'px';
      document.body.append(r); setTimeout(() => r.remove(), 700)
    }, true);
  };
  if (document.body) mount(); else document.addEventListener('DOMContentLoaded', mount);
})();`

async function glide(page, loc) {
  // Al centro de la pantalla (no «lo justo»): con la barra superior fija y la de pestañas abajo, «lo justo» dejaba el botón
  // tapado y el clic caía en la barra.
  await loc.evaluate((el) => el.scrollIntoView({ block: 'center', inline: 'nearest' }))
  await page.waitForTimeout(350)
  const b = await loc.boundingBox()
  const x = b.x + b.width / 2
  const y = b.y + b.height / 2
  await page.mouse.move(x, y, { steps: 24 })
  return { x, y }
}
async function tap(page, loc) {
  const first = await glide(page, loc)
  await page.waitForTimeout(300)
  // La pantalla se puede mover mientras el cursor llega (fotos que cargan, listas que se redibujan): se vuelve a medir
  // justo antes de pulsar y, si el botón ya no está donde estaba el cursor, el cursor lo sigue.
  const b = await loc.boundingBox()
  if (b) {
    const x = b.x + b.width / 2
    const y = b.y + b.height / 2
    if (Math.abs(x - first.x) > 2 || Math.abs(y - first.y) > 2) {
      await page.mouse.move(x, y, { steps: 12 })
      await page.waitForTimeout(200)
    }
  }
  await page.mouse.down()
  await page.waitForTimeout(90)
  await page.mouse.up()
  await page.waitForTimeout(550)
}
async function typeInto(page, loc, text, delay = 42) {
  await tap(page, loc)
  await loc.fill('') // por si ya había algo
  await loc.pressSequentially(text, { delay }) // escribe EN ese campo, no donde haya quedado el foco
  await page.waitForTimeout(250)
}
async function tapAt(page, x, y) {
  await page.mouse.move(x, y, { steps: 20 })
  await page.waitForTimeout(250)
  await page.mouse.down()
  await page.waitForTimeout(80)
  await page.mouse.up()
  await page.waitForTimeout(450)
}

class Recorder {
  constructor(page, name) {
    this.page = page
    this.name = name
    this.t0 = Date.now()
    this.timeline = { scenes: [], fast: [] }
  }
  now() {
    return (Date.now() - this.t0) / 1000
  }
  async scene(id, fn) {
    const start = this.now()
    const need = wavSeconds(id)
    this.timeline.scenes.push({ id, start })
    await this.page.evaluate((t) => window.__cap && window.__cap(t, false), byId[id].text).catch(() => {})
    try {
      await fn()
    } catch (e) {
      console.log(`  ! escena ${id}: ${String(e.message).split('\n')[0]}`)
    }
    const spent = this.now() - start
    if (spent < need + 0.9) await this.page.waitForTimeout((need + 0.9 - spent) * 1000)
    console.log(`  escena ${id}: ${(this.now() - start).toFixed(1)} s (narración ${need.toFixed(1)} s)`)
  }
  /** Tramo de espera que se acelera en el video final. */
  async fast(label, fn) {
    const start = this.now()
    await this.page.evaluate((t) => window.__cap && window.__cap(t, true), `⏩ ${label}`).catch(() => {})
    try {
      await fn()
    } finally {
      this.timeline.fast.push({ start, end: this.now() })
    }
    await this.page.evaluate((t) => window.__cap && window.__cap(t, false), byId[this.timeline.scenes.at(-1).id].text).catch(() => {})
  }
}

async function api(token, method, url, body) {
  const res = await fetch(API + url, {
    method,
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  return res.json().catch(() => ({}))
}
async function loginToken() {
  const res = await fetch(`${API}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username: ADMIN.email, password: ADMIN.password }),
  })
  return (await res.json()).access_token
}

const browser = await chromium.launch()
const timelines = {}

// ======================================================================= ADMIN (escritorio)
console.log('Grabando: administrador (escritorio)')
const adminCtx = await browser.newContext({
  viewport: { width: 1280, height: 720 },
  recordVideo: { dir: path.join(OUT, 'raw-admin'), size: { width: 1280, height: 720 } },
  locale: 'es-DO',
})
await adminCtx.addInitScript(OVERLAY)
const page = await adminCtx.newPage()
const rec = new Recorder(page, 'admin')
if (process.env.DEBUG_NET) {
  page.on('request', (r) => r.method() !== 'GET' && console.log('   >', r.method(), r.url().replace(BASE, '').slice(0, 90)))
  page.on('response', (r) => r.status() >= 400 && console.log('   <', r.status(), r.url().replace(BASE, '').slice(0, 90)))
  page.on('console', (m) => m.type() === 'error' && console.log('   console:', m.text().slice(0, 160)))
}
await page.goto(BASE + '/login')
await page.waitForTimeout(800)

let project = null
let techAccount = null

await rec.scene('intro', async () => {
  await page.mouse.move(640, 360)
  await page.waitForTimeout(2500)
})

await rec.scene('login', async () => {
  await typeInto(page, page.locator('input[type="email"]'), ADMIN.email)
  await typeInto(page, page.locator('input[type="password"]'), ADMIN.password, 30)
  await tap(page, page.locator('button[type="submit"]'))
  await page.getByRole('button', { name: 'Salir' }).waitFor({ timeout: 20000 })
})

await rec.scene('inicio', async () => {
  await page.waitForTimeout(1500)
  await page.mouse.move(700, 300, { steps: 30 })
  await page.mouse.wheel(0, 250)
  await page.waitForTimeout(1500)
  await page.mouse.wheel(0, -250)
})

await rec.scene('cliente', async () => {
  await page.goto(BASE + '/clientes')
  await tap(page, page.locator('button:has-text("+ Nuevo")'))
  await typeInto(page, page.locator('label:has-text("Nombre") input').first(), 'Colmado Don Pepe')
  await typeInto(page, page.locator('label:has-text("Teléfono") input').first(), '809-555-0142')
  await typeInto(page, page.locator('label:has-text("Dirección") textarea, label:has-text("Dirección") input').first(), 'Calle Duarte 45, Santiago de los Caballeros')
  await tap(page, page.locator('button:has-text("Guardar cliente")'))
  await page.getByText('Colmado Don Pepe').first().waitFor({ timeout: 15000 })
})

await rec.scene('proyecto', async () => {
  await page.goto(BASE + '/proyectos')
  await tap(page, page.locator('button:has-text("+ Nuevo")'))
  const combo = page.locator('input[role="combobox"]')
  await typeInto(page, combo, 'Colmado')
  await tap(page, page.getByRole('option', { name: /Colmado Don Pepe/ }).first())
  await typeInto(page, page.locator('label:has-text("Descripción") textarea').first(), 'Cámaras de seguridad y grabador para el colmado')
  await tap(page, page.locator('button:has-text("Crear proyecto")'))
  const link = page.locator('a', { hasText: 'Cámaras de seguridad y grabador' }).first()
  await tap(page, link)
  await page.waitForURL(/\/proyectos\/\d+/, { timeout: 15000 })
  project = Number(page.url().match(/proyectos\/(\d+)/)[1])
})

await rec.scene('levantamiento', async () => {
  await tap(page, page.getByRole('button', { name: 'Datos', exact: true }))
  await tap(page, page.getByRole('button', { name: 'Levantamiento', exact: true }))
  await typeInto(
    page,
    page.locator('label:has-text("Notas") textarea').first(),
    'Colmado con dos ventanas al frente y una puerta. Instalar 3 cámaras (entrada, caja y almacén), un NVR de 8 canales y un switch PoE. El cuarto del grabador queda a unos 12 metros.',
    22,
  )
  await tap(page, page.locator('button:has-text("Guardar levantamiento")'))
  await page.waitForTimeout(800)
  await page.setInputFiles('input[type="file"][accept="image/*"]', PHOTO)
  await page.getByRole('button', { name: 'Marcar equipos en la foto' }).waitFor({ timeout: 20000 })
})

await rec.scene('marcar', async () => {
  await tap(page, page.getByRole('button', { name: 'Marcar equipos en la foto' }))
  const surface = page.getByTestId('marker-surface')
  await page.getByAltText('Foto del levantamiento').evaluate((img) => img.decode?.())
  await page.waitForTimeout(600)
  const b = await surface.boundingBox()
  const at = (fx, fy) => [b.x + b.width * fx, b.y + b.height * fy]
  // 3 cámaras
  await tap(page, page.getByRole('radio', { name: 'Cámara' }))
  for (const [fx, fy] of [[0.5, 0.4], [0.3, 0.45], [0.78, 0.45]]) await tapAt(page, ...at(fx, fy))
  // 1 grabador y 1 switch
  await tap(page, page.getByRole('radio', { name: 'NVR / DVR' }))
  await tapAt(page, ...at(0.9, 0.62))
  await tap(page, page.getByRole('radio', { name: 'Switch' }))
  await tapAt(page, ...at(0.82, 0.62))
  await page.waitForTimeout(1200)
  await tap(page, page.getByRole('button', { name: 'Guardar puntos' }))
})

await rec.scene('ia', async () => {
  await page.waitForLoadState('networkidle').catch(() => {})
  await page.waitForTimeout(800)
  for (let attempt = 0; attempt < 3; attempt++) {
    await tap(page, page.getByRole('button', { name: /Generar cotización con IA/ }))
    const started = await page
      .getByRole('status')
      .getByText(/Armando la cotización/)
      .waitFor({ timeout: 6000 })
      .then(() => true, () => false)
    if (started) break
  }
  // La barra de «Armando la cotización…» confirma que el servidor arrancó el trabajo; si no sale, se avisa en vez de esperar 6 min
  await page.getByRole('status').getByText(/Armando la cotización/).waitFor({ timeout: 20000 })
  await rec.fast('La IA está armando la cotización…', async () => {
    await page.getByRole('status').getByText(/Cotización lista/).waitFor({ timeout: 360000 })
  })
  await tap(page, page.getByRole('link', { name: 'Ver y ajustar la cotización' }))
})

if (process.env.STOP_AFTER === 'ia') {
  await page.screenshot({ path: path.join(OUT, 'debug-ia.png') })
  console.log('Parado tras la escena ia. URL:', page.url())
  await browser.close()
  process.exit(0)
}

await rec.scene('cotizacion', async () => {
  await page.waitForURL(/tab=cotizacion/, { timeout: 15000 }).catch(() => {})
  const card = page.locator('button:has-text("COT-")').first()
  await tap(page, card)
  await page.waitForTimeout(1500)
  await page.mouse.wheel(0, 380)
  await page.waitForTimeout(1500)
})

await rec.scene('precios', async () => {
  // El catálogo sube de precio (lo hace oficina en el Catálogo; aquí se simula para mostrar el botón)
  const token = await loginToken()
  const quotes = await api(token, 'GET', `/api/projects/${project}/quotes`)
  const line = (quotes[0]?.items ?? []).find((i) => i.product_id)
  if (line) await api(token, 'PUT', `/api/catalog/${line.product_id}`, { price: Number(line.unit_price) + 350 })
  await page.mouse.wheel(0, -200)
  await tap(page, page.getByRole('button', { name: 'Actualizar precios' }).first())
  await page.getByTestId('quote-pricing').first().getByText(/→/).first().waitFor({ timeout: 15000 })
  await page.waitForTimeout(2500)
  await tap(page, page.getByRole('button', { name: /Aplicar precios nuevos/ }))
  await page.waitForTimeout(1500)
})

await rec.scene('comparar', async () => {
  await tap(page, page.getByRole('button', { name: /Comparar con otra cotización/ }))
  await typeInto(page, page.getByPlaceholder(/Competidor, Proveedor X/), 'Competidor')
  await typeInto(
    page,
    page.getByLabel('…o pega el texto de la cotización'),
    'COTIZACION 2045 - Seguridad Total SRL\n3 Camara domo IP 4MP  RD$ 4,100.00\n1 NVR 8 canales con disco 2TB  RD$ 17,500.00\n1 Switch PoE 8 puertos  RD$ 6,200.00\n1 Mano de obra instalacion  RD$ 9,000.00\nTotal RD$ 54,590.00',
    14,
  )
  await tap(page, page.getByRole('button', { name: 'Subir y comparar' }))
  await rec.fast('Leyendo y comparando la cotización…', async () => {
    await page.getByTestId('comparison-result').waitFor({ timeout: 240000 })
  })
  await page.getByTestId('comparison-result').scrollIntoViewIfNeeded()
  await page.waitForTimeout(2500)
  await page.mouse.wheel(0, 420)
  await page.waitForTimeout(2500)
})

await rec.scene('mapa', async () => {
  const token = await loginToken()
  await api(token, 'PUT', `/api/projects/${project}`, { address: 'Calle Duarte 45, Santiago de los Caballeros' })
  await page.goto(`${BASE}/proyectos/${project}`)
  await page.waitForTimeout(1200)
  const showMap = page.getByRole('button', { name: /Ver mapa/ })
  if (await showMap.count()) await tap(page, showMap.first())
  await page.locator('iframe[title="Mapa de la ubicación"]').first().waitFor({ timeout: 25000 })
  await page.waitForTimeout(2500)
  await tap(page, page.getByRole('button', { name: /Cómo llegar/ }).first())
  await page.waitForTimeout(3000)
})

await rec.scene('plataforma', async () => {
  await page.goto(BASE + '/plataforma')
  await page.waitForTimeout(2200)
  await tap(page, page.getByRole('button', { name: 'Crear demo para técnicos' }))
  await tap(page, page.getByLabel('Técnicos de prueba'))
  await page.keyboard.press('Control+A')
  await page.keyboard.type('2', { delay: 80 })
  await tap(page, page.getByRole('button', { name: 'Crear empresa demo' }))
  await page.getByTestId('demo-created').waitFor({ timeout: 30000 })
})

await rec.scene('demo', async () => {
  await page.getByTestId('demo-created').scrollIntoViewIfNeeded()
  await page.waitForTimeout(1500)
  const row = page.getByTestId('demo-account').filter({ hasText: 'tecnico' }).first()
  await tap(page, row.getByRole('button', { name: 'Editar clave' }))
  await typeInto(page, row.getByLabel(/Nueva clave de/), 'Tecnico-Demo-2026')
  await tap(page, row.getByRole('button', { name: 'Guardar' }))
  await page.waitForTimeout(1200)
  techAccount = {
    email: (await row.locator('p.font-mono').first().innerText()).trim(),
    password: 'Tecnico-Demo-2026',
  }
  await glide(page, page.getByRole('button', { name: 'Descargar archivo' }))
  await page.waitForTimeout(1500)
  await glide(page, row.getByRole('link', { name: 'Enviar por WhatsApp' }))
  await page.waitForTimeout(1800)
})

timelines.admin = rec.timeline
await adminCtx.close()
console.log('Técnico:', techAccount?.email)

// ======================================================================= TÉCNICO (iPhone)
console.log('Grabando: técnico (iPhone)')
const iphone = devices['iPhone 14']
const techCtx = await browser.newContext({
  ...iphone,
  viewport: { width: 390, height: 844 },
  recordVideo: { dir: path.join(OUT, 'raw-tech'), size: { width: 390, height: 844 } },
  locale: 'es-DO',
})
await techCtx.addInitScript(OVERLAY)
const tpage = await techCtx.newPage()
const trec = new Recorder(tpage, 'tech')
await tpage.goto(BASE + '/login')
await tpage.waitForTimeout(800)

await trec.scene('tecnico', async () => {
  await typeInto(tpage, tpage.locator('input[type="email"]'), techAccount.email, 30)
  await typeInto(tpage, tpage.locator('input[type="password"]'), techAccount.password, 30)
  await tap(tpage, tpage.locator('button[type="submit"]'))
  await tpage.waitForURL(/\/perfil/, { timeout: 20000 })
  await tpage.waitForTimeout(1500)
  await typeInto(tpage, tpage.getByLabel('Contraseña actual'), techAccount.password, 30)
  await typeInto(tpage, tpage.getByLabel('Nueva contraseña (mínimo 10 caracteres)'), 'MiClaveTecnico-77', 30)
  await typeInto(tpage, tpage.getByLabel('Confirmar nueva contraseña'), 'MiClaveTecnico-77', 30)
  await tap(tpage, tpage.getByRole('button', { name: 'Cambiar contraseña' }))
  await tpage.getByText(/Contraseña actualizada/).waitFor({ timeout: 15000 })
  await tpage.waitForTimeout(1500)
})

await trec.scene('tecnico2', async () => {
  await tpage.goto(BASE + '/')
  await tpage.waitForTimeout(2200)
  await tap(tpage, tpage.getByRole('link', { name: /Proyectos/ }).last())
  await tpage.waitForTimeout(1500)
  const first = tpage.locator('a[href^="/proyectos/"]').first()
  await tap(tpage, first)
  await tpage.waitForTimeout(2500)
  await tpage.mouse.wheel(0, 500)
  await tpage.waitForTimeout(1500)
})

await trec.scene('fin', async () => {
  await tpage.goto(BASE + '/')
  await tpage.waitForTimeout(1500)
})
timelines.tech = trec.timeline
await techCtx.close()
await browser.close()

// El video de cada contexto queda con nombre aleatorio: se renombra.
for (const [name, dir] of [['admin', 'raw-admin'], ['tech', 'raw-tech']]) {
  const f = fs.readdirSync(path.join(OUT, dir)).find((x) => x.endsWith('.webm'))
  fs.renameSync(path.join(OUT, dir, f), path.join(OUT, `${name}.webm`))
}
fs.writeFileSync(path.join(OUT, 'timeline.json'), JSON.stringify(timelines, null, 2))
console.log('Listo. Línea de tiempo:', JSON.stringify(timelines.admin.fast), JSON.stringify(timelines.tech.fast))
