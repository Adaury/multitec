import { useRef, useState } from 'react'
import { FileSpreadsheet } from 'lucide-react'
import { api, apiErrorMessage, downloadFile } from '../lib/api'
import { useAuthStore } from '../lib/authStore'
import type { LineItemInput, Product } from '../lib/types'
import { ITBIS_RATE, formatDOP } from '../lib/format'
import { Button, IconButton, Input } from './ui'

interface Props {
  items: LineItemInput[]
  onChange: (items: LineItemInput[]) => void
  products: Product[]
  mode: 'budget' | 'quote'
}

function emptyLine(): LineItemInput {
  return { product_id: null, description: '', quantity: 1, unit_price: 0, note: '' }
}

export function LineItemsEditor({ items, onChange, products, mode }: Props) {
  const subtotal = round2(items.reduce((sum, item) => sum + item.quantity * item.unit_price, 0))
  const itbis = round2(subtotal * ITBIS_RATE)
  const total = mode === 'quote' ? round2(subtotal + itbis) : subtotal

  function updateItem(index: number, patch: Partial<LineItemInput>) {
    const next = items.slice()
    next[index] = { ...next[index], ...patch }
    onChange(next)
  }

  function selectProduct(index: number, productId: string) {
    if (!productId) {
      updateItem(index, { product_id: null })
      return
    }
    const product = products.find((p) => p.id === Number(productId))
    if (!product) return
    updateItem(index, { product_id: product.id, description: product.name, unit_price: product.price })
  }

  function removeItem(index: number) {
    onChange(items.filter((_, i) => i !== index))
  }

  return (
    <div className="space-y-3">
      {items.map((item, index) => (
        <div key={index} className="space-y-2 rounded-2xl bg-brand-gray p-3 dark:bg-gray-800">
          <div className="flex items-center gap-2">
            <select
              className="min-w-0 flex-1 rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
              value={item.product_id ?? ''}
              onChange={(e) => selectProduct(index, e.target.value)}
            >
              <option value="">Texto libre…</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.code} · {p.name}
                </option>
              ))}
            </select>
            <IconButton type="button" onClick={() => removeItem(index)} aria-label="Eliminar línea">
              ✕
            </IconButton>
          </div>
          <Input
            placeholder="Descripción"
            value={item.description}
            onChange={(e) => updateItem(index, { description: e.target.value })}
          />
          <div className="grid grid-cols-2 gap-2">
            <Input
              type="number"
              min="0"
              step="0.01"
              placeholder="Cantidad"
              value={item.quantity}
              onChange={(e) => updateItem(index, { quantity: Number(e.target.value) })}
            />
            <Input
              type="number"
              min="0"
              step="0.01"
              placeholder="Precio unitario"
              value={item.unit_price}
              onChange={(e) => updateItem(index, { unit_price: Number(e.target.value) })}
            />
          </div>
          <p className="text-right text-xs text-gray-500 dark:text-gray-400">
            {formatDOP(round2(item.quantity * item.unit_price))}
          </p>
          <Input
            placeholder="Nota rápida (sale impresa en el PDF)"
            value={item.note ?? ''}
            onChange={(e) => updateItem(index, { note: e.target.value })}
          />
        </div>
      ))}

      <Button type="button" variant="secondary" onClick={() => onChange([...items, emptyLine()])}>
        + Agregar línea
      </Button>

      <LoadFromFiles items={items} onChange={onChange} />

      <div className="space-y-1 rounded-2xl bg-white p-4 ring-1 ring-black/5 dark:bg-gray-900 dark:ring-white/10">
        {mode === 'quote' ? (
          <>
            <Row label="Subtotal" value={subtotal} />
            <Row label="ITBIS (18%)" value={itbis} />
            <Row label="Total" value={total} strong />
          </>
        ) : (
          <Row label="Total del presupuesto" value={total} strong />
        )}
      </div>
    </div>
  )
}

interface ParsedItems {
  items: LineItemInput[]
  warnings: string[]
  matched: number
}

/** Cargar partidas desde uno o varios archivos (Excel o CSV): la lista de materiales que mandó un proveedor,
 * una cotización descargada para corregirla, o la lista de alarma y ferretería. Se agregan a las líneas que ya
 * hay; las que se encuentran en el catálogo quedan enlazadas a su producto. */
function LoadFromFiles({ items, onChange }: { items: LineItemInput[]; onChange: (items: LineItemInput[]) => void }) {
  const role = useAuthStore((s) => s.user?.role)
  const inputRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [warnings, setWarnings] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  if (role !== 'admin' && role !== 'oficina') return null

  async function load(files: File[]) {
    if (files.length === 0) return
    setBusy(true)
    setError(null)
    setMessage(null)
    setWarnings([])
    try {
      const form = new FormData()
      for (const f of files) form.append('files', f)
      const { data } = await api.post<ParsedItems>('/line-items/parse', form, { timeout: 60_000 })
      // Las líneas vacías que se dejaron abiertas no se conservan al cargar el archivo.
      const kept = items.filter((i) => i.description.trim() || i.product_id)
      onChange([...kept, ...data.items.map((i) => ({ ...i, note: i.note ?? '' }))])
      setMessage(
        `Se agregaron ${data.items.length} partida(s)` +
          (data.items.length ? ` · ${data.matched} encontrada(s) en el catálogo` : ''),
      )
      setWarnings(data.warnings)
    } catch (err) {
      setError(apiErrorMessage(err, 'No se pudo leer el archivo'))
    } finally {
      setBusy(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <div className="space-y-2 rounded-2xl border-2 border-dashed border-gray-200 p-3 dark:border-gray-700">
      <div className="flex flex-wrap items-center gap-2">
        <FileSpreadsheet className="h-5 w-5 text-brand-blue" aria-hidden="true" />
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={busy}
          className="rounded-full bg-brand-blue px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {busy ? 'Leyendo…' : 'Cargar partidas desde archivo'}
        </button>
        <button
          type="button"
          onClick={() => downloadFile('/line-items/template?format=xlsx', 'plantilla_partidas.xlsx')}
          className="text-sm font-medium text-brand-blue hover:underline"
        >
          ⬇ Plantilla
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".csv,text/csv,.xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          aria-label="Archivos de partidas (Excel o CSV)"
          className="hidden"
          onChange={(e) => void load(Array.from(e.target.files ?? []))}
        />
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400">
        Excel o CSV, uno o varios a la vez, con las columnas Código, Descripción, Cantidad, Precio y Nota.
      </p>
      {message && (
        <p role="status" className="text-sm font-medium text-emerald-700 dark:text-emerald-400">
          ✓ {message}
        </p>
      )}
      {warnings.length > 0 && (
        <ul className="space-y-0.5 text-xs text-amber-700 dark:text-amber-400">
          {warnings.slice(0, 8).map((w) => (
            <li key={w}>• {w}</li>
          ))}
          {warnings.length > 8 && <li>… y {warnings.length - 8} aviso(s) más</li>}
        </ul>
      )}
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </div>
  )
}

function Row({ label, value, strong = false }: { label: string; value: number; strong?: boolean }) {
  return (
    <div
      className={
        strong
          ? 'flex justify-between text-base font-semibold text-gray-900 dark:text-gray-100'
          : 'flex justify-between text-sm text-gray-500 dark:text-gray-400'
      }
    >
      <span>{label}</span>
      <span>{formatDOP(value)}</span>
    </div>
  )
}

function round2(n: number): number {
  return Math.round(n * 100) / 100
}
