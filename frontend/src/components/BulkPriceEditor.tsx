import { useMemo, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api, apiErrorMessage } from '../lib/api'
import type { Product } from '../lib/types'
import { Badge, Button, Input, Modal } from './ui'

/** Cambia los precios de varios productos de una vez: se edita en la tabla o se aplica un ajuste
 * por porcentaje a todos los que se ven, y solo se envían los que cambiaron. */
export function BulkPriceEditor({
  open,
  onClose,
  products,
}: {
  open: boolean
  onClose: () => void
  products: Product[]
}) {
  const queryClient = useQueryClient()
  const [edits, setEdits] = useState<Record<number, string>>({})
  const [percent, setPercent] = useState('')
  const [search, setSearch] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase()
    return q ? products.filter((p) => `${p.code} ${p.name}`.toLowerCase().includes(q)) : products
  }, [products, search])

  const changed = products.filter((p) => {
    const raw = edits[p.id]
    return raw !== undefined && raw !== '' && Number(raw) >= 0 && Number(raw) !== p.price
  })

  function applyPercent() {
    const pct = Number(percent)
    if (!percent.trim() || Number.isNaN(pct)) return
    const next = { ...edits }
    for (const p of visible) next[p.id] = String(Math.max(0, Math.round(p.price * (1 + pct / 100) * 100) / 100))
    setEdits(next)
  }

  function close() {
    setEdits({})
    setPercent('')
    setSearch('')
    setError(null)
    onClose()
  }

  async function save() {
    setBusy(true)
    setError(null)
    try {
      await api.put('/catalog/bulk-prices', {
        items: changed.map((p) => ({ id: p.id, price: Number(edits[p.id]) })),
      })
      await queryClient.invalidateQueries({ queryKey: ['catalog'] })
      close()
    } catch (err) {
      setError(apiErrorMessage(err, 'No se pudieron guardar los precios.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal open={open} onClose={close} title="Actualizar precios">
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <Input placeholder="Buscar producto…" value={search} onChange={(e) => setSearch(e.target.value)} />
          <Input
            type="number"
            step="any"
            placeholder="Ajuste % (ej. 10 o -5)"
            value={percent}
            onChange={(e) => setPercent(e.target.value)}
          />
          <Button type="button" onClick={applyPercent} disabled={!percent.trim()}>
            Aplicar a los que se ven
          </Button>
        </div>

        <div className="max-h-[50vh] overflow-y-auto">
          {visible.map((p) => (
            <div key={p.id} className="flex items-center gap-2 border-b border-gray-100 py-2 dark:border-gray-800">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-gray-900 dark:text-gray-100">{p.name}</p>
                <p className="text-xs text-gray-400">
                  {p.code} · actual RD$ {p.price.toLocaleString('es-DO', { minimumFractionDigits: 2 })}
                </p>
              </div>
              {p.price_estimated && <Badge tone="amber">Estimado</Badge>}
              <div className="w-32">
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={edits[p.id] ?? String(p.price)}
                  onChange={(e) => setEdits({ ...edits, [p.id]: e.target.value })}
                />
              </div>
            </div>
          ))}
          {visible.length === 0 && <p className="text-sm text-gray-500">Ningún producto coincide.</p>}
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}
        <Button type="button" onClick={save} disabled={busy || changed.length === 0}>
          {busy ? 'Guardando…' : `Guardar ${changed.length} cambio(s)`}
        </Button>
      </div>
    </Modal>
  )
}
