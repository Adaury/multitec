import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, apiErrorMessage } from '../lib/api'
import { formatDOP } from '../lib/format'
import type { Quote } from '../lib/types'
import { Button } from './ui'

interface PriceChange {
  item_id: number
  description: string
  quantity: number
  old_price: number
  new_price: number
}

interface RepricePreview {
  changes: PriceChange[]
  total_old: number
  total_new: number
}

interface RepriceResult {
  quote: Quote
  created_new: boolean
  changes: PriceChange[]
}

/** Actualizar los precios de una cotización con los del catálogo: se ve qué cambia antes de aplicarlo. Una cotización
 * pendiente se corrige en su lugar; una ya aprobada o rechazada genera una versión nueva y la original queda como estaba.
 * También permite copiar una cotización cerrada como versión nueva para editarla línea a línea. */
export function QuotePricing({ quote, projectId }: { quote: Quote; projectId: number }) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const pending = quote.status === 'pendiente'

  const preview = useQuery({
    queryKey: ['quote-reprice', quote.id],
    queryFn: async () => (await api.get<RepricePreview>(`/quotes/${quote.id}/reprice-preview`)).data,
    enabled: open,
  })

  const done = (text: string) => {
    queryClient.invalidateQueries({ queryKey: ['quotes', projectId] })
    queryClient.invalidateQueries({ queryKey: ['quote-history', quote.id] })
    queryClient.invalidateQueries({ queryKey: ['quote-reprice', quote.id] })
    setOpen(false)
    setError(null)
    setMessage(text)
  }

  const apply = useMutation({
    mutationFn: async () => (await api.post<RepriceResult>(`/quotes/${quote.id}/reprice`)).data,
    onSuccess: (r) =>
      done(
        r.created_new
          ? `Se creó la cotización ${r.quote.code} con los precios nuevos. La original quedó igual.`
          : `Precios actualizados (${r.changes.length}).`,
      ),
    onError: (e) => setError(apiErrorMessage(e, 'No se pudieron actualizar los precios')),
  })

  const copy = useMutation({
    mutationFn: async () => (await api.post<Quote>(`/quotes/${quote.id}/new-version`)).data,
    onSuccess: (q) => done(`Se creó la cotización ${q.code} para que la edites.`),
    onError: (e) => setError(apiErrorMessage(e, 'No se pudo crear la nueva versión')),
  })

  return (
    <div className="space-y-2" data-testid="quote-pricing">
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" className="!w-auto flex-1" onClick={() => setOpen((v) => !v)}>
          Actualizar precios
        </Button>
        {!pending && (
          <Button variant="ghost" className="!w-auto flex-1" onClick={() => copy.mutate()} disabled={copy.isPending}>
            Crear nueva versión para editar
          </Button>
        )}
      </div>

      {open && (
        <div className="space-y-2 rounded-2xl bg-gray-50 p-3 text-sm dark:bg-gray-800/60">
          {preview.isLoading && <p className="text-gray-500">Revisando el catálogo…</p>}
          {preview.data && preview.data.changes.length === 0 && (
            <p className="text-gray-600 dark:text-gray-300">Los precios ya son los del catálogo.</p>
          )}
          {preview.data && preview.data.changes.length > 0 && (
            <>
              <ul className="space-y-1">
                {preview.data.changes.map((c) => (
                  <li key={c.item_id} className="flex items-baseline justify-between gap-3">
                    <span className="min-w-0 truncate text-gray-800 dark:text-gray-200">
                      {c.quantity} × {c.description}
                    </span>
                    <span className="shrink-0 text-xs text-gray-600 dark:text-gray-300">
                      {formatDOP(c.old_price)} → <strong>{formatDOP(c.new_price)}</strong>
                    </span>
                  </li>
                ))}
              </ul>
              <p className="text-xs text-gray-600 dark:text-gray-300">
                Total con ITBIS: {formatDOP(preview.data.total_old)} → <strong>{formatDOP(preview.data.total_new)}</strong>
              </p>
              {!pending && (
                <p className="text-xs text-amber-700 dark:text-amber-400">
                  Esta cotización ya no se puede editar: se creará una nueva con estos precios.
                </p>
              )}
              <Button onClick={() => apply.mutate()} disabled={apply.isPending}>
                {apply.isPending ? 'Actualizando…' : pending ? 'Aplicar precios nuevos' : 'Crear cotización con precios nuevos'}
              </Button>
            </>
          )}
        </div>
      )}
      {message && <p className="text-sm text-green-700 dark:text-green-400">{message}</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  )
}
