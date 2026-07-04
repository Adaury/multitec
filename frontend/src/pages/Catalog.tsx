import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Product, StockMovement, StockMovementType } from '../lib/types'
import { PRODUCT_CATEGORY_LABELS } from '../lib/types'
import { Badge, Button, Card, Field, Input, Textarea } from '../components/ui'

interface ProductForm {
  category: string
  name: string
  unit: string
  price: number
  notes: string
  brand: string
  model: string
  commercial_description: string
  technical_description: string
  tags: string
  synonyms: string
  suggests_tags: string
}

function emptyForm(): ProductForm {
  return {
    category: 'camara',
    name: '',
    unit: 'unidad',
    price: 0,
    notes: '',
    brand: '',
    model: '',
    commercial_description: '',
    technical_description: '',
    tags: '',
    synonyms: '',
    suggests_tags: '',
  }
}

function splitTags(value: string): string[] {
  return value
    .split(',')
    .map((t) => t.trim())
    .filter(Boolean)
}

export function Catalog() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<ProductForm>(emptyForm())
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const { data: products, isLoading } = useQuery({
    queryKey: ['catalog'],
    queryFn: async () => (await api.get<Product[]>('/catalog')).data,
  })

  const createProduct = useMutation({
    mutationFn: async (payload: ProductForm) =>
      (
        await api.post('/catalog', {
          ...payload,
          tags: splitTags(payload.tags),
          synonyms: splitTags(payload.synonyms),
          suggests_tags: splitTags(payload.suggests_tags),
        })
      ).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['catalog'] })
      setShowForm(false)
      setForm(emptyForm())
    },
  })

  return (
    <div className="space-y-4 py-4 md:space-y-6 md:py-8">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900 md:text-2xl dark:text-gray-100">Catálogo</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-full bg-brand-blue px-4 py-2 text-sm font-medium text-white"
        >
          {showForm ? 'Cancelar' : '+ Nuevo'}
        </button>
      </div>

      {showForm && (
        <Card className="md:max-w-2xl">
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault()
              createProduct.mutate(form)
            }}
          >
            <div className="grid gap-3 md:grid-cols-2">
              <Field label="Categoría">
                <select
                  className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
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
              <Field label="Marca">
                <Input value={form.brand} onChange={(e) => setForm({ ...form, brand: e.target.value })} />
              </Field>
              <Field label="Modelo">
                <Input value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} />
              </Field>
            </div>
            <Field label="Descripción comercial">
              <Textarea
                value={form.commercial_description}
                onChange={(e) => setForm({ ...form, commercial_description: e.target.value })}
              />
            </Field>
            <Field label="Descripción técnica">
              <Textarea
                value={form.technical_description}
                onChange={(e) => setForm({ ...form, technical_description: e.target.value })}
              />
            </Field>
            <Field label="Etiquetas (separadas por coma) — ej: camara, domo, ip, cctv">
              <Input value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} />
            </Field>
            <Field label="Sinónimos (separados por coma) — ej: camarita, ojo">
              <Input value={form.synonyms} onChange={(e) => setForm({ ...form, synonyms: e.target.value })} />
            </Field>
            <Field label="Sugiere al usarse (separado por coma) — ej: nvr, poe-switch">
              <Input
                value={form.suggests_tags}
                onChange={(e) => setForm({ ...form, suggests_tags: e.target.value })}
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

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {products?.map((product) => (
          <ProductCard
            key={product.id}
            product={product}
            expanded={expandedId === product.id}
            onToggle={() => setExpandedId(expandedId === product.id ? null : product.id)}
          />
        ))}
        {products?.length === 0 && <p className="text-sm text-gray-500">Aún no hay productos en el catálogo.</p>}
      </div>
    </div>
  )
}

function ProductCard({
  product,
  expanded,
  onToggle,
}: {
  product: Product
  expanded: boolean
  onToggle: () => void
}) {
  const queryClient = useQueryClient()
  const [movementType, setMovementType] = useState<StockMovementType>('entrada')
  const [quantity, setQuantity] = useState('')
  const [reason, setReason] = useState('')
  const [error, setError] = useState<string | null>(null)

  const { data: movements } = useQuery({
    queryKey: ['stock-movements', product.id],
    queryFn: async () => (await api.get<StockMovement[]>(`/products/${product.id}/stock-movements`)).data,
    enabled: expanded,
  })

  const registerMovement = useMutation({
    mutationFn: async () =>
      (
        await api.post(`/products/${product.id}/stock-movements`, {
          movement_type: movementType,
          quantity: Number(quantity),
          reason: reason || null,
        })
      ).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['catalog'] })
      queryClient.invalidateQueries({ queryKey: ['stock-movements', product.id] })
      setQuantity('')
      setReason('')
      setError(null)
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? 'Error al registrar el movimiento'),
  })

  return (
    <Card>
      <button className="w-full text-left" onClick={onToggle}>
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-gray-900 dark:text-gray-100">{product.name}</p>
            <p className="text-xs text-gray-400">
              {product.code} · {PRODUCT_CATEGORY_LABELS[product.category] ?? product.category}
              {product.brand && ` · ${product.brand}`}
              {product.model && ` ${product.model}`}
            </p>
            {product.tags.length > 0 && (
              <div className="mt-1 flex flex-wrap gap-1">
                {product.tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full bg-brand-gray px-2 py-0.5 text-[10px] text-gray-500 dark:bg-gray-800 dark:text-gray-400"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
          <div className="text-right">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
              RD$ {product.price.toLocaleString('es-DO', { minimumFractionDigits: 2 })}
            </p>
            <Badge tone={product.stock_quantity > 0 ? 'green' : 'gray'}>
              {product.stock_quantity.toLocaleString('es-DO')} {product.unit} en bodega
            </Badge>
          </div>
        </div>
      </button>

      {expanded && (
        <div className="mt-3 space-y-3 border-t border-gray-100 pt-3 dark:border-gray-800">
          <form
            className="space-y-2"
            onSubmit={(e) => {
              e.preventDefault()
              registerMovement.mutate()
            }}
          >
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setMovementType('entrada')}
                className={`flex-1 rounded-xl px-3 py-2 text-sm font-medium ${
                  movementType === 'entrada'
                    ? 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300'
                    : 'bg-brand-gray text-gray-500 dark:bg-gray-800 dark:text-gray-400'
                }`}
              >
                Entrada
              </button>
              <button
                type="button"
                onClick={() => setMovementType('salida')}
                className={`flex-1 rounded-xl px-3 py-2 text-sm font-medium ${
                  movementType === 'salida'
                    ? 'bg-red-50 text-red-600 dark:bg-red-950 dark:text-red-300'
                    : 'bg-brand-gray text-gray-500 dark:bg-gray-800 dark:text-gray-400'
                }`}
              >
                Salida
              </button>
            </div>
            <Field label="Cantidad">
              <Input
                type="number"
                step="0.01"
                min="0.01"
                required
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
              />
            </Field>
            <Field label="Motivo (opcional)">
              <Input value={reason} onChange={(e) => setReason(e.target.value)} />
            </Field>
            {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
            <Button type="submit" disabled={registerMovement.isPending || !quantity}>
              {registerMovement.isPending ? 'Guardando…' : 'Registrar movimiento'}
            </Button>
          </form>

          {movements && movements.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">Historial</p>
              <ul className="space-y-1 text-xs text-gray-600 dark:text-gray-400">
                {movements.map((m) => (
                  <li key={m.id} className="flex justify-between">
                    <span>
                      {new Date(m.created_at).toLocaleString('es-DO')} —{' '}
                      <span
                        className={
                          m.movement_type === 'entrada'
                            ? 'text-green-700 dark:text-green-400'
                            : 'text-red-600 dark:text-red-400'
                        }
                      >
                        {m.movement_type === 'entrada' ? '+' : '-'}
                        {m.quantity.toLocaleString('es-DO')}
                      </span>
                      {m.reason ? ` (${m.reason})` : ''}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {movements && movements.length === 0 && (
            <p className="text-xs text-gray-400">Aún no hay movimientos de stock.</p>
          )}
        </div>
      )}
    </Card>
  )
}
