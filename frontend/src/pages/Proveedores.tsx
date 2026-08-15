import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Supplier, SupplierPurchase } from '../lib/types'
import { formatDOP } from '../lib/format'
import { Button, Card, Field, Input, Textarea } from '../components/ui'

interface SupplierForm {
  name: string
  rnc: string
  phone: string
  email: string
  address: string
  notes: string
}

const EMPTY_FORM: SupplierForm = { name: '', rnc: '', phone: '', email: '', address: '', notes: '' }

function supplierToForm(supplier: Supplier): SupplierForm {
  return {
    name: supplier.name,
    rnc: supplier.rnc ?? '',
    phone: supplier.phone ?? '',
    email: supplier.email ?? '',
    address: supplier.address ?? '',
    notes: supplier.notes ?? '',
  }
}

function supplierFormPayload(form: SupplierForm) {
  return {
    name: form.name,
    rnc: form.rnc || null,
    phone: form.phone || null,
    email: form.email || null,
    address: form.address || null,
    notes: form.notes || null,
  }
}

function SupplierFormFields({ form, setForm }: { form: SupplierForm; setForm: (form: SupplierForm) => void }) {
  return (
    <>
      <div className="grid gap-3 md:grid-cols-2">
        <Field label="Nombre">
          <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <Field label="RNC (opcional)">
          <Input value={form.rnc} onChange={(e) => setForm({ ...form, rnc: e.target.value })} />
        </Field>
        <Field label="Teléfono (opcional)">
          <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        </Field>
        <Field label="Correo (opcional)">
          <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </Field>
      </div>
      <Field label="Dirección (opcional)">
        <Input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
      </Field>
      <Field label="Notas (opcional)">
        <Textarea rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
      </Field>
    </>
  )
}

export function Proveedores() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<SupplierForm>(EMPTY_FORM)
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const { data: suppliers, isLoading } = useQuery({
    queryKey: ['suppliers'],
    queryFn: async () => (await api.get<Supplier[]>('/suppliers')).data,
  })

  const createSupplier = useMutation({
    mutationFn: async () => (await api.post('/suppliers', supplierFormPayload(form))).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['suppliers'] })
      setForm(EMPTY_FORM)
      setShowForm(false)
      setError(null)
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? 'No se pudo crear el proveedor'),
  })

  return (
    <div className="space-y-4 py-4 md:space-y-6 md:py-8">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900 md:text-2xl dark:text-gray-100">Proveedores</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-full bg-brand-blue px-4 py-2 text-sm font-medium text-white"
        >
          {showForm ? 'Cancelar' : '+ Agregar'}
        </button>
      </div>
      <p className="text-sm text-gray-500 dark:text-gray-400">
        A quién se le compran los materiales de un proyecto — se elige al marcar un material
        "Comprado" en la pestaña Compras, junto con el precio real pagado.
      </p>

      {showForm && (
        <Card className="space-y-3 md:max-w-xl">
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault()
              createSupplier.mutate()
            }}
          >
            <SupplierFormFields form={form} setForm={setForm} />
            {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
            <Button type="submit" disabled={createSupplier.isPending || !form.name}>
              {createSupplier.isPending ? 'Guardando…' : 'Agregar proveedor'}
            </Button>
          </form>
        </Card>
      )}

      {isLoading && <p className="text-sm text-gray-500 dark:text-gray-400">Cargando…</p>}

      <div className="grid items-start gap-3 md:grid-cols-2 xl:grid-cols-3">
        {suppliers?.map((supplier) => (
          <SupplierCard
            key={supplier.id}
            supplier={supplier}
            expanded={expandedId === supplier.id}
            onToggle={() => setExpandedId(expandedId === supplier.id ? null : supplier.id)}
          />
        ))}
      </div>
      {suppliers?.length === 0 && (
        <p className="text-sm text-gray-500 dark:text-gray-400">Aún no hay proveedores registrados.</p>
      )}
    </div>
  )
}

function SupplierCard({
  supplier,
  expanded,
  onToggle,
}: {
  supplier: Supplier
  expanded: boolean
  onToggle: () => void
}) {
  const queryClient = useQueryClient()
  const [isEditing, setIsEditing] = useState(false)
  const [form, setForm] = useState<SupplierForm>(() => supplierToForm(supplier))
  const [error, setError] = useState<string | null>(null)

  const { data: purchases } = useQuery({
    queryKey: ['supplier-purchases', supplier.id],
    queryFn: async () => (await api.get<SupplierPurchase[]>(`/suppliers/${supplier.id}/materials`)).data,
    enabled: expanded,
  })

  const updateSupplier = useMutation({
    mutationFn: async () => (await api.put(`/suppliers/${supplier.id}`, supplierFormPayload(form))).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['suppliers'] })
      setIsEditing(false)
      setError(null)
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? 'No se pudo guardar el proveedor'),
  })

  function startEditing() {
    setForm(supplierToForm(supplier))
    setIsEditing(true)
  }

  return (
    <Card>
      <button className="w-full text-left" onClick={onToggle}>
        <p className="font-medium text-gray-900 dark:text-gray-100">{supplier.name}</p>
        <p className="text-xs text-gray-400">
          {[supplier.rnc, supplier.phone, supplier.email].filter(Boolean).join(' · ') || 'Sin datos de contacto'}
        </p>
      </button>

      {expanded && isEditing && (
        <div className="mt-3 space-y-3 border-t border-gray-100 pt-3 dark:border-gray-800">
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault()
              updateSupplier.mutate()
            }}
          >
            <SupplierFormFields form={form} setForm={setForm} />
            {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
            <div className="flex gap-2">
              <Button className="!w-auto flex-1" type="submit" disabled={updateSupplier.isPending || !form.name}>
                {updateSupplier.isPending ? 'Guardando…' : 'Guardar'}
              </Button>
              <Button
                className="!w-auto flex-1"
                type="button"
                variant="secondary"
                onClick={() => setIsEditing(false)}
                disabled={updateSupplier.isPending}
              >
                Cancelar
              </Button>
            </div>
          </form>
        </div>
      )}

      {expanded && !isEditing && (
        <div className="mt-3 space-y-3 border-t border-gray-100 pt-3 dark:border-gray-800">
          {supplier.address && <p className="text-xs text-gray-500 dark:text-gray-400">{supplier.address}</p>}
          {supplier.notes && <p className="text-xs italic text-gray-400 dark:text-gray-500">{supplier.notes}</p>}
          <button className="text-xs text-brand-blue hover:underline" onClick={startEditing}>
            Editar
          </button>

          <div>
            <p className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">Historial de compras</p>
            {purchases && purchases.length > 0 && (
              <ul className="space-y-1 text-xs text-gray-600 dark:text-gray-400">
                {purchases.map((p) => (
                  <li key={p.id} className="flex justify-between gap-2">
                    <span>
                      {p.project_code} — {p.quantity} × {p.description}
                    </span>
                    <span className="shrink-0 text-gray-700 dark:text-gray-300">
                      {p.purchase_price != null ? formatDOP(p.purchase_price) : '—'}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            {purchases && purchases.length === 0 && (
              <p className="text-xs text-gray-400">Aún no hay compras registradas a este proveedor.</p>
            )}
          </div>
        </div>
      )}
    </Card>
  )
}
