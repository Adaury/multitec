import { deflateSync } from 'node:zlib'
import { expect, unique, type Page } from './fixtures'

/** Cliente de la API con la sesión del navegador: reutiliza el token que dejó el login. */
export async function apiClient(page: Page) {
  await page.goto('/')
  const token = await page.evaluate(() => localStorage.getItem('multitec_token'))
  const headers = { Authorization: `Bearer ${token}` }
  return {
    headers,
    async post(url: string, data?: unknown) {
      const res = await page.request.post(`/api${url}`, { headers, data })
      expect(res.ok(), `${url} -> ${res.status()} ${await res.text()}`).toBeTruthy()
      return res.json()
    },
    async get(url: string) {
      const res = await page.request.get(`/api${url}`, { headers })
      expect(res.ok(), `${url} -> ${res.status()} ${await res.text()}`).toBeTruthy()
      return res
    },
  }
}

/** Cliente → proyecto → presupuesto → cotización (pendiente). */
export async function createQuote(
  api: Awaited<ReturnType<typeof apiClient>>,
  clientName: string,
  phone?: string,
  rnc?: string,
) {
  const client = await api.post('/clients', { name: clientName, phone: phone ?? null, rnc: rnc ?? null })
  const project = await api.post('/projects', { client_id: client.id, description: unique('Proyecto') })
  const budget = await api.post(`/projects/${project.id}/budgets`, {
    items: [{ description: 'Cámara IP', quantity: 2, unit_price: 500 }],
  })
  const quote = await api.post(`/budgets/${budget.id}/convert-to-quote`)
  return { client, project, quote }
}

/** Factura emitida con NCF B01 (crédito fiscal): el cliente lleva RNC, así que sale en el 607. */
export async function issueInvoice(api: Awaited<ReturnType<typeof apiClient>>, clientName: string) {
  const nextYear = new Date()
  nextYear.setFullYear(nextYear.getFullYear() + 1)
  await api.post('/ncf-sequences', {
    ncf_type: 'B01',
    description: 'E2E',
    range_start: 1,
    range_end: 9999,
    expires_at: nextYear.toISOString().slice(0, 10),
  })
  const { project, quote } = await createQuote(api, clientName, undefined, '130000001')
  await api.post(`/quotes/${quote.id}/approve`)
  const preInvoice = await api.post(`/quotes/${quote.id}/generate-pre-invoice`)
  const invoice = await api.post(`/pre-invoices/${preInvoice.id}/convert-to-invoice`, {})
  return { project, invoice }
}

/** PNG válido (gris liso) generado en el momento, para subir como foto de levantamiento. */
export function makePng(width = 160, height = 120): Buffer {
  const crcTable = Array.from({ length: 256 }, (_, n) => {
    let c = n
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1
    return c >>> 0
  })
  const crc = (buf: Buffer) => {
    let c = 0xffffffff
    for (const byte of buf) c = crcTable[(c ^ byte) & 0xff] ^ (c >>> 8)
    return (c ^ 0xffffffff) >>> 0
  }
  const chunk = (type: string, data: Buffer) => {
    const body = Buffer.concat([Buffer.from(type), data])
    const out = Buffer.alloc(8 + data.length + 4)
    out.writeUInt32BE(data.length, 0)
    body.copy(out, 4)
    out.writeUInt32BE(crc(body), 8 + data.length)
    return out
  }
  const header = Buffer.alloc(13)
  header.writeUInt32BE(width, 0)
  header.writeUInt32BE(height, 4)
  header[8] = 8 // profundidad
  header[9] = 2 // RGB
  const row = Buffer.concat([Buffer.from([0]), Buffer.alloc(width * 3, 200)])
  const raw = Buffer.concat(Array.from({ length: height }, () => row))
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', header),
    chunk('IDAT', deflateSync(raw)),
    chunk('IEND', Buffer.alloc(0)),
  ])
}
