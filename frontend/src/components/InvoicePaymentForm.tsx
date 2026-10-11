import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Invoice, PaymentMethod } from '../lib/types'
import { Button, Field, Input } from './ui'

export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  efectivo: 'Efectivo',
  cheque_transferencia: 'Cheque / transferencia / depósito',
  tarjeta: 'Tarjeta débito / crédito',
  credito: 'Venta a crédito',
  bonos: 'Bonos o certificados de regalo',
  permuta: 'Permuta',
  otras: 'Otra forma de pago',
}

/** Cómo se cobró la factura y qué retuvo el cliente (ITBIS / renta). Son los datos que el reporte
 * 607 de la DGII pide y que antes salían vacíos. Se llenan después de emitir la factura. */
export function InvoicePaymentForm({ invoice }: { invoice: Invoice }) {
  const queryClient = useQueryClient()
  const [method, setMethod] = useState<string>(invoice.payment_method ?? '')
  const [itbisWithheld, setItbisWithheld] = useState(invoice.itbis_withheld ? String(invoice.itbis_withheld) : '')
  const [isrWithheld, setIsrWithheld] = useState(invoice.isr_withheld ? String(invoice.isr_withheld) : '')
  const [retentionDate, setRetentionDate] = useState(invoice.retention_date ?? '')
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null)

  const hasRetention = Number(itbisWithheld) > 0 || Number(isrWithheld) > 0

  const save = useMutation({
    mutationFn: async () =>
      (
        await api.put<Invoice>(`/invoices/${invoice.id}/payment`, {
          payment_method: method || null,
          itbis_withheld: Number(itbisWithheld) || 0,
          isr_withheld: Number(isrWithheld) || 0,
          retention_date: hasRetention ? retentionDate || null : null,
        })
      ).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices', invoice.project_id] })
      queryClient.invalidateQueries({ queryKey: ['invoice-history', invoice.id] })
      setMessage({ ok: true, text: 'Guardado. Se usará en el reporte 607.' })
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail
      setMessage({ ok: false, text: typeof detail === 'string' ? detail : 'No se pudo guardar' })
    },
  })

  return (
    <form
      className="space-y-3 rounded-xl border border-gray-100 p-3 dark:border-gray-800"
      onSubmit={(e) => {
        e.preventDefault()
        setMessage(null)
        save.mutate()
      }}
    >
      <p className="text-sm font-medium text-gray-800 dark:text-gray-200">Cobro y retenciones (para el 607)</p>
      <Field label="Forma de pago">
        <select
          className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
          value={method}
          onChange={(e) => setMethod(e.target.value)}
        >
          <option value="">Sin definir</option>
          {(Object.keys(PAYMENT_METHOD_LABELS) as PaymentMethod[]).map((m) => (
            <option key={m} value={m}>
              {PAYMENT_METHOD_LABELS[m]}
            </option>
          ))}
        </select>
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="ITBIS retenido">
          <Input
            type="number"
            inputMode="decimal"
            min="0"
            step="0.01"
            value={itbisWithheld}
            onChange={(e) => setItbisWithheld(e.target.value)}
          />
        </Field>
        <Field label="Renta retenida (ISR)">
          <Input
            type="number"
            inputMode="decimal"
            min="0"
            step="0.01"
            value={isrWithheld}
            onChange={(e) => setIsrWithheld(e.target.value)}
          />
        </Field>
      </div>
      {hasRetention && (
        <Field label="Fecha de la retención">
          <Input required type="date" value={retentionDate} onChange={(e) => setRetentionDate(e.target.value)} />
        </Field>
      )}
      {message && (
        <p className={`text-sm ${message.ok ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
          {message.text}
        </p>
      )}
      <Button type="submit" variant="secondary" disabled={save.isPending}>
        {save.isPending ? 'Guardando…' : 'Guardar cobro y retenciones'}
      </Button>
    </form>
  )
}
