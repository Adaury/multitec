import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Product } from '../lib/types'
import { PRODUCT_CATEGORY_LABELS } from '../lib/types'
import { Button, Card, Field, Input, Textarea } from '../components/ui'

interface ProductForm {
  category: string
  name: string
  unit: string
  price: number
  notes: string
}

function emptyForm(): ProductForm {
  return { category: 'camara', name: '', unit: 'unidad', price: 0, notes: '' }
}

export function Catalog() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<ProductForm>(emptyForm())

  const { data: products, isLoading } = useQuery({
    queryKey: ['catalog'],
    queryFn: async () => (await api.get<Product[]>('/catalog')).data,
  })

  const createProduct = useMutation({
    mutationFn: async (payload: ProductForm) => (await api.post('/catalog', payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['catalog'] })
      setShowForm(false)
      setForm(emptyForm())
    },
  })

  return (
    <div className="space-y-4 py-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Catálogo</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-full bg-brand-blue px-4 py-2 text-sm font-medium text-white"
        >
          {showForm ? 'Cancelar' : '+ Nuevo'}
        </button>
      </div>

      {showForm && (
        <Card>
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault()
              createProduct.mutate(form)
            }}
          >
            <Field label="Categoría">
              <select
                className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base"
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
              >
                {Object.entries(PRODUCT_CATEGORY_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Nombre">
              <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </Field>
            <Field label="Unidad">
              <Input value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} />
            </Field>
            <Field label="Precio (RD$)">
              <Input
                type="number"
                step="0.01"
                min="0"
                value={form.price}
                onChange={(e) => setForm({ ...form, price: Number(e.target.value) })}
              />
            </Field>
            <Field label="Notas">
              <Textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            </Field>
            <Button type="submit" disabled={createProduct.isPending}>
              {createProduct.isPending ? 'Guardando…' : 'Guardar producto'}
            </Button>
          </form>
        </Card>
      )}

      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}

      <div className="space-y-3">
        {products?.map((product) => (
          <Card key={product.id}>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">{product.name}</p>
                <p className="text-xs text-gray-400">
                  {product.code} · {PRODUCT_CATEGORY_LABELS[product.category] ?? product.category}
                </p>
              </div>
              <p className="text-sm font-medium text-gray-700">
                RD$ {product.price.toLocaleString('es-DO', { minimumFractionDigits: 2 })}
              </p>
            </div>
          </Card>
        ))}
        {products?.length === 0 && <p className="text-sm text-gray-500">Aún no hay productos en el catálogo.</p>}
      </div>
    </div>
  )
}
