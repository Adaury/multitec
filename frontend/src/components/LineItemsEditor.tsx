import { useState } from 'react'
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
  return { product_id: null, description: '', quantity: 1, unit_price: 0 }
}

export function LineItemsEditor({ items, onChange, products, mode }: Props) {
  // Notas al vuelo, solo para recordar algo mientras se arma el documento — nunca se
  // mandan al backend (no forman parte de LineItemInput), así que no hace falta guardarlas.
  const [quickNotes, setQuickNotes] = useState<string[]>(() => items.map(() => ''))

  const subtotal = round2(items.reduce((sum, item) => sum + item.quantity * item.unit_price, 0))
  const itbis = round2(subtotal * ITBIS_RATE)
  const total = mode === 'quote' ? round2(subtotal + itbis) : subtotal

  function updateItem(index: number, patch: Partial<LineItemInput>) {
    const next = items.slice()
    next[index] = { ...next[index], ...patch }
    onChange(next)
  }

  function updateQuickNote(index: number, value: string) {
    const next = quickNotes.slice()
    next[index] = value
    setQuickNotes(next)
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

  function addItem() {
    onChange([...items, emptyLine()])
    setQuickNotes([...quickNotes, ''])
  }

  function removeItem(index: number) {
    onChange(items.filter((_, i) => i !== index))
    setQuickNotes(quickNotes.filter((_, i) => i !== index))
  }

  return (
    <div className="space-y-3">
      {items.map((item, index) => (
        <div key={index} className="space-y-2 rounded-2xl bg-brand-gray p-3">
          <div className="flex items-center gap-2">
            <select
              className="flex-1 rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm"
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
          <p className="text-right text-xs text-gray-500">{formatDOP(round2(item.quantity * item.unit_price))}</p>
          <Input
            placeholder="Nota rápida (no se guarda)"
            value={quickNotes[index] ?? ''}
            onChange={(e) => updateQuickNote(index, e.target.value)}
          />
        </div>
      ))}

      <Button type="button" variant="secondary" onClick={addItem}>
        + Agregar línea
      </Button>

      <div className="space-y-1 rounded-2xl bg-white p-4 ring-1 ring-black/5">
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

function Row({ label, value, strong = false }: { label: string; value: number; strong?: boolean }) {
  return (
    <div className={`flex justify-between ${strong ? 'text-base font-semibold text-gray-900' : 'text-sm text-gray-500'}`}>
      <span>{label}</span>
      <span>{formatDOP(value)}</span>
    </div>
  )
}

function round2(n: number): number {
  return Math.round(n * 100) / 100
}
