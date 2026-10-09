import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, downloadFile } from '../lib/api'
import type { PurchaseInvoice, Supplier } from '../lib/types'
import { formatDOP } from '../lib/format'
import { Button, Card, Field, Input, Textarea } from '../components/ui'

const SELECT_CLASS =
  'w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100'

const EXPENSE_TYPES: Record<string, string> = {
  '01': '01 · Gastos de personal',
  '02': '02 · Trabajos, suministros y servicios',
  '03': '03 · Arrendamientos',
  '04': '04 · Activos fijos',
  '05': '05 · Representación',
  '06': '06 · Otras deducciones admitidas',
  '07': '07 · Gastos financieros',
  '08': '08 · Gastos extraordinarios',
  '09': '09 · Compras y gastos que forman parte del costo de venta',
  '10': '10 · Adquisiciones de activos',
  '11': '11 · Gastos de seguros',
}

const PAYMENT_TYPES: Record<string, string> = {
  '01': '01 · Efectivo',
  '02': '02 · Cheque / transferencia / depósito',
  '03': '03 · Tarjeta débito / crédito',
  '04': '04 · Compra a crédito',
  '05': '05 · Permuta',
  '06': '06 · Notas de crédito',
  '07': '07 · Mixto',
}

interface PurchaseForm {
  supplier_id: string
  ncf: string
  ncf_modified: string
  invoice_date: string
  payment_date: string
  expense_type: string
  payment_type: string
  services_amount: string
  goods_amount: string
  itbis_invoiced: string
  itbis_withheld: string
  isr_withheld: string
  notes: string
}

const today = () => new Date().toISOString().slice(0, 10)

const EMPTY_FORM: PurchaseForm = {
  supplier_id: '',
  ncf: '',
  ncf_modified: '',
  invoice_date: today(),
  payment_date: '',
  expense_type: '09',
  payment_type: '04',
  services_amount: '',
  goods_amount: '',
  itbis_invoiced: '',
  itbis_withheld: '',
  isr_withheld: '',
  notes: '',
}

function formPayload(form: PurchaseForm) {
  return {
    supplier_id: Number(form.supplier_id),
    ncf: form.ncf,
    ncf_modified: form.ncf_modified || null,
    invoice_date: form.invoice_date,
    payment_date: form.payment_date || null,
    expense_type: form.expense_type,
    payment_type: form.payment_type,
    services_amount: Number(form.services_amount) || 0,
    goods_amount: Number(form.goods_amount) || 0,
    itbis_invoiced: Number(form.itbis_invoiced) || 0,
    itbis_withheld: Number(form.itbis_withheld) || 0,
    isr_withheld: Number(form.isr_withheld) || 0,
    notes: form.notes || null,
  }
}

export function Compras() {
  const queryClient = useQueryClient()
  const now = new Date()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<PurchaseForm>(EMPTY_FORM)
  const [error, setError] = useState<string | null>(null)
  const [reportMonth, setReportMonth] = useState(now.getMonth() + 1)
  const [reportYear, setReportYear] = useState(now.getFullYear())

  const { data: invoices, isLoading } = useQuery({
    queryKey: ['purchase-invoices'],
    queryFn: async () => (await api.get<PurchaseInvoice[]>('/purchase-invoices')).data,
  })
  const { data: suppliers } = useQuery({
    queryKey: ['suppliers'],
    queryFn: async () => (await api.get<Supplier[]>('/suppliers')).data,
  })

  const createInvoice = useMutation({
    mutationFn: async () => (await api.post('/purchase-invoices', formPayload(form))).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase-invoices'] })
      setForm({ ...EMPTY_FORM, invoice_date: today() })
      setShowForm(false)
      setError(null)
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'No se pudo registrar la factura')
    },
  })

  const deleteInvoice = useMutation({
    mutationFn: async (id: number) => api.delete(`/purchase-invoices/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['purchase-invoices'] }),
  })

  const set = (patch: Partial<PurchaseForm>) => setForm({ ...form, ...patch })
  const total = (i: PurchaseInvoice) => Number(i.services_amount) + Number(i.goods_amount)

  return (
    <div className="space-y-4 py-4 md:space-y-6 md:py-8">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900 md:text-2xl dark:text-gray-100">Compras</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-full bg-brand-blue px-4 py-2 text-sm font-medium text-white"
        >
          {showForm ? 'Cancelar' : '+ Factura de compra'}
        </button>
      </div>
      <p className="text-sm text-gray-500 dark:text-gray-400">
        Facturas de proveedores con su NCF e ITBIS — son la base del reporte 606 (Compras) de la DGII.
      </p>

      <Card className="space-y-3 md:max-w-xl">
        <p className="text-sm font-medium text-gray-800 dark:text-gray-200">Reporte 606 (Compras) para la DGII</p>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Exporta las facturas del mes seleccionado (por fecha del comprobante). Proporcionalidad, ITBIS al costo,
          percepciones, ISC, otros impuestos y propina salen vacíos, y el ITBIS facturado se reporta como "por
          adelantar". <strong>Verifica el archivo contra la plantilla oficial vigente en dgii.gov.do antes de
          remitirlo.</strong>
        </p>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Mes">
            <select className={SELECT_CLASS} value={reportMonth} onChange={(e) => setReportMonth(Number(e.target.value))}>
              {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                <option key={m} value={m}>
                  {new Date(2000, m - 1, 1).toLocaleDateString('es-DO', { month: 'long' })}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Año">
            <Input type="number" value={reportYear} onChange={(e) => setReportYear(Number(e.target.value))} />
          </Field>
        </div>
        <Button
          variant="secondary"
          onClick={() =>
            downloadFile(
              `/reports/dgii-606?year=${reportYear}&month=${reportMonth}`,
              `606_${reportYear}${String(reportMonth).padStart(2, '0')}.csv`,
            )
          }
        >
          Descargar reporte 606
        </Button>
      </Card>

      {showForm && (
        <Card className="md:max-w-2xl">
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault()
              createInvoice.mutate()
            }}
          >
            <div className="grid gap-3 md:grid-cols-2">
              <Field label="Proveedor">
                <select
                  required
                  className={SELECT_CLASS}
                  value={form.supplier_id}
                  onChange={(e) => set({ supplier_id: e.target.value })}
                >
                  <option value="">Selecciona…</option>
                  {suppliers?.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                      {s.rnc ? ` (${s.rnc})` : ' — sin RNC'}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="NCF">
                <Input required minLength={11} maxLength={19} value={form.ncf} onChange={(e) => set({ ncf: e.target.value })} />
              </Field>
              <Field label="Fecha del comprobante">
                <Input required type="date" value={form.invoice_date} onChange={(e) => set({ invoice_date: e.target.value })} />
              </Field>
              <Field label="Fecha de pago (opcional)">
                <Input type="date" value={form.payment_date} onChange={(e) => set({ payment_date: e.target.value })} />
              </Field>
              <Field label="Tipo de gasto">
                <select className={SELECT_CLASS} value={form.expense_type} onChange={(e) => set({ expense_type: e.target.value })}>
                  {Object.entries(EXPENSE_TYPES).map(([code, label]) => (
                    <option key={code} value={code}>
                      {label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Forma de pago">
                <select className={SELECT_CLASS} value={form.payment_type} onChange={(e) => set({ payment_type: e.target.value })}>
                  {Object.entries(PAYMENT_TYPES).map(([code, label]) => (
                    <option key={code} value={code}>
                      {label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Monto en servicios">
                <Input type="number" min="0" step="0.01" value={form.services_amount} onChange={(e) => set({ services_amount: e.target.value })} />
              </Field>
              <Field label="Monto en bienes">
                <Input type="number" min="0" step="0.01" value={form.goods_amount} onChange={(e) => set({ goods_amount: e.target.value })} />
              </Field>
              <Field label="ITBIS facturado">
                <Input type="number" min="0" step="0.01" value={form.itbis_invoiced} onChange={(e) => set({ itbis_invoiced: e.target.value })} />
              </Field>
              <Field label="ITBIS retenido">
                <Input type="number" min="0" step="0.01" value={form.itbis_withheld} onChange={(e) => set({ itbis_withheld: e.target.value })} />
              </Field>
              <Field label="Retención de renta (ISR)">
                <Input type="number" min="0" step="0.01" value={form.isr_withheld} onChange={(e) => set({ isr_withheld: e.target.value })} />
              </Field>
              <Field label="NCF modificado (opcional)">
                <Input maxLength={19} value={form.ncf_modified} onChange={(e) => set({ ncf_modified: e.target.value })} />
              </Field>
            </div>
            <Field label="Notas (opcional)">
              <Textarea rows={2} value={form.notes} onChange={(e) => set({ notes: e.target.value })} />
            </Field>
            {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
            <Button type="submit" disabled={createInvoice.isPending || !form.supplier_id || !form.ncf}>
              {createInvoice.isPending ? 'Guardando…' : 'Registrar factura'}
            </Button>
          </form>
        </Card>
      )}

      {isLoading && <p className="text-sm text-gray-500 dark:text-gray-400">Cargando…</p>}

      <div className="grid items-start gap-3 md:grid-cols-2 xl:grid-cols-3">
        {invoices?.map((invoice) => (
          <Card key={invoice.id} className="space-y-1">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="font-medium text-gray-900 dark:text-gray-100">{invoice.supplier_name}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {invoice.ncf} · {invoice.invoice_date}
                </p>
              </div>
              <button
                className="text-xs text-red-600 dark:text-red-400"
                onClick={() => {
                  if (window.confirm(`¿Eliminar la factura ${invoice.ncf}?`)) deleteInvoice.mutate(invoice.id)
                }}
              >
                Eliminar
              </button>
            </div>
            <p className="text-sm text-gray-700 dark:text-gray-300">
              Total {formatDOP(total(invoice))} · ITBIS {formatDOP(Number(invoice.itbis_invoiced))}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">{PAYMENT_TYPES[invoice.payment_type]}</p>
          </Card>
        ))}
      </div>
      {invoices?.length === 0 && (
        <p className="text-sm text-gray-500 dark:text-gray-400">Aún no hay facturas de compra registradas.</p>
      )}
    </div>
  )
}
