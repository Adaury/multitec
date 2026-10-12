import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Invoice } from '../lib/types'
import { Button, Field, Input } from './ui'

export const VOID_REASONS: Record<string, string> = {
  '01': '01 · Deterioro de factura preimpresa',
  '02': '02 · Errores de impresión (factura preimpresa)',
  '03': '03 · Impresión defectuosa',
  '04': '04 · Corrección de la información',
  '05': '05 · Cambio de productos',
  '06': '06 · Devolución de productos',
  '07': '07 · Omisión de productos',
  '08': '08 · Errores en secuencia de NCF',
  '09': '09 · Por cese de operaciones',
  '10': '10 · Pérdida o hurto de talonarios',
}

/** Anulación de una factura (solo admin): el NCF se reporta en el 608 y la venta sale del 607. */
export function InvoiceVoidForm({ invoice }: { invoice: Invoice }) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('04')
  const [note, setNote] = useState('')
  const [error, setError] = useState<string | null>(null)

  const voidInvoice = useMutation({
    mutationFn: async () =>
      (await api.post<Invoice>(`/invoices/${invoice.id}/void`, { reason_code: reason, note: note || null })).data,
    onSuccess: () => {
      setOpen(false)
      queryClient.invalidateQueries({ queryKey: ['invoices', invoice.project_id] })
      queryClient.invalidateQueries({ queryKey: ['invoice-history', invoice.id] })
    },
    onError: (err: { response?: { data?: { detail?: string } } }) =>
      setError(err.response?.data?.detail ?? 'No se pudo anular la factura.'),
  })

  if (!open) {
    return (
      <button className="text-xs font-medium text-red-600 dark:text-red-400" onClick={() => setOpen(true)}>
        Anular factura…
      </button>
    )
  }

  return (
    <div className="space-y-3 rounded-xl border border-red-200 p-3 dark:border-red-900">
      <p className="text-sm font-medium text-red-700 dark:text-red-400">
        Anular {invoice.code} (NCF {invoice.ncf})
      </p>
      <p className="text-xs text-gray-500 dark:text-gray-400">
        El NCF queda consumido y se reporta en el 608; la factura deja de contar en el 607 y en los totales. Para
        volver a facturar, genera una prefactura nueva desde la cotización aprobada.
      </p>
      <Field label="Tipo de anulación">
        <select
          className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        >
          {Object.entries(VOID_REASONS).map(([code, label]) => (
            <option key={code} value={code}>
              {label}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Nota (opcional)">
        <Input value={note} onChange={(e) => setNote(e.target.value)} maxLength={300} />
      </Field>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      <div className="flex gap-2">
        <Button variant="ghost" className="!w-auto flex-1" onClick={() => setOpen(false)}>
          Cancelar
        </Button>
        <Button className="!w-auto flex-1" onClick={() => voidInvoice.mutate()} disabled={voidInvoice.isPending}>
          {voidInvoice.isPending ? 'Anulando…' : 'Confirmar anulación'}
        </Button>
      </div>
    </div>
  )
}
