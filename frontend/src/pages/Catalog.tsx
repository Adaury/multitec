import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type {
  CalculationParameter,
  CatalogRule,
  Category,
  Product,
  StockMovement,
  StockMovementType,
  TechnicalRule,
  TechnicalRuleActionType,
} from '../lib/types'
import { Badge, Button, Card, Field, Input, Textarea } from '../components/ui'

interface CategoryOption {
  category: Category
  depth: number
}

function flattenCategories(categories: Category[]): CategoryOption[] {
  const byParent = new Map<number | null, Category[]>()
  for (const c of categories) {
    const list = byParent.get(c.parent_id) ?? []
    list.push(c)
    byParent.set(c.parent_id, list)
  }
  const options: CategoryOption[] = []
  const walk = (parentId: number | null, depth: number) => {
    for (const c of byParent.get(parentId) ?? []) {
      options.push({ category: c, depth })
      walk(c.id, depth + 1)
    }
  }
  walk(null, 0)
  return options
}

interface ProductForm {
  category_id: string
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
}

function emptyForm(): ProductForm {
  return {
    category_id: '',
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

  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: async () => (await api.get<Category[]>('/categories')).data,
  })
  const categoryOptions = categories ? flattenCategories(categories) : []

  const createProduct = useMutation({
    mutationFn: async (payload: ProductForm) =>
      (
        await api.post('/catalog', {
          ...payload,
          category_id: Number(payload.category_id),
          tags: splitTags(payload.tags),
          synonyms: splitTags(payload.synonyms),
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
                  required
                  className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
                  value={form.category_id}
                  onChange={(e) => setForm({ ...form, category_id: e.target.value })}
                >
                  <option value="" disabled>
                    Selecciona una categoría…
                  </option>
                  {categoryOptions.map(({ category, depth }) => (
                    <option key={category.id} value={category.id}>
                      {'  '.repeat(depth)}
                      {depth > 0 ? '– ' : ''}
                      {category.name}
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
              {product.code} · {product.category_path ?? product.category_name ?? 'Sin categoría'}
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
        <div className="mt-3 space-y-4 border-t border-gray-100 pt-3 dark:border-gray-800">
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

          <RulesEditor productId={product.id} />
        </div>
      )}
    </Card>
  )
}

const ACTION_TYPE_LABELS: Record<TechnicalRuleActionType, string> = {
  add_accessory: 'Agregar accesorio',
  set_calculation_parameter: 'Ajustar cálculo',
  flag_engineering_note: 'Nota de ingeniería',
}

function describeAccessoryRule(quantity: number, tag: string, perSourceUnits: number | null): string {
  return perSourceUnits
    ? `Agregar ${quantity} "${tag}" por cada ${perSourceUnits} de este`
    : `Agregar ${quantity} "${tag}" fijo`
}

function RulesEditor({ productId }: { productId: number }) {
  const queryClient = useQueryClient()
  const [actionType, setActionType] = useState<TechnicalRuleActionType>('add_accessory')

  // Campos de "Agregar accesorio"
  const [targetTag, setTargetTag] = useState('')
  const [proportional, setProportional] = useState(false)
  const [perSourceUnits, setPerSourceUnits] = useState('1')
  const [ruleQuantity, setRuleQuantity] = useState('1')

  // Campos de "Ajustar cálculo"
  const [parameterKey, setParameterKey] = useState('')
  const [parameterValue, setParameterValue] = useState('')

  // Campos de "Nota de ingeniería"
  const [engineeringNote, setEngineeringNote] = useState('')

  const [error, setError] = useState<string | null>(null)

  // Mecanismo original — se mantiene intacto, sin migrar (§ ai-engine-architecture.md,
  // Motor 4). Las reglas nuevas se crean todas vía /technical-rules; estas solo se
  // siguen listando/borrando para no perder de vista reglas ya existentes.
  const { data: legacyRules } = useQuery({
    queryKey: ['catalog-rules', productId],
    queryFn: async () => (await api.get<CatalogRule[]>(`/catalog/${productId}/rules`)).data,
  })

  const { data: technicalRules } = useQuery({
    queryKey: ['technical-rules', productId],
    queryFn: async () => (await api.get<TechnicalRule[]>(`/catalog/${productId}/technical-rules`)).data,
  })

  const { data: calculationParameters } = useQuery({
    queryKey: ['calculation-parameters'],
    queryFn: async () => (await api.get<CalculationParameter[]>('/calculation-parameters')).data,
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['catalog-rules', productId] })
    queryClient.invalidateQueries({ queryKey: ['technical-rules', productId] })
  }

  const createRule = useMutation({
    mutationFn: async () => {
      const payload =
        actionType === 'add_accessory'
          ? {
              action_type: 'add_accessory' as const,
              target_tag: targetTag,
              per_source_units: proportional ? Number(perSourceUnits) : null,
              quantity: Number(ruleQuantity),
            }
          : actionType === 'set_calculation_parameter'
            ? {
                action_type: 'set_calculation_parameter' as const,
                parameter_key: parameterKey,
                value: Number(parameterValue),
              }
            : { action_type: 'flag_engineering_note' as const, engineering_note: engineeringNote }
      return (await api.post(`/catalog/${productId}/technical-rules`, payload)).data
    },
    onSuccess: () => {
      invalidate()
      setTargetTag('')
      setProportional(false)
      setPerSourceUnits('1')
      setRuleQuantity('1')
      setParameterKey('')
      setParameterValue('')
      setEngineeringNote('')
      setError(null)
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? 'No se pudo crear la regla'),
  })

  const deleteLegacyRule = useMutation({
    mutationFn: async (ruleId: number) => (await api.delete(`/catalog/rules/${ruleId}`)).data,
    onSuccess: invalidate,
  })

  const deleteTechnicalRule = useMutation({
    mutationFn: async (ruleId: number) => (await api.delete(`/catalog/technical-rules/${ruleId}`)).data,
    onSuccess: invalidate,
  })

  function describeTechnicalRule(r: TechnicalRule): string {
    if (r.action_type === 'add_accessory') {
      return describeAccessoryRule(r.quantity, r.target_tag ?? '', r.per_source_units)
    }
    if (r.action_type === 'set_calculation_parameter') {
      const param = calculationParameters?.find((p) => p.key === r.parameter_key)
      return `Ajustar "${param?.description ?? r.parameter_key}" a ${r.value}`
    }
    return `Nota de ingeniería: "${r.engineering_note}"`
  }

  const canSubmit =
    (actionType === 'add_accessory' && !!targetTag) ||
    (actionType === 'set_calculation_parameter' && !!parameterKey && parameterValue !== '') ||
    (actionType === 'flag_engineering_note' && !!engineeringNote)

  return (
    <div>
      <p className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">
        Reglas — qué hacer automáticamente cuando se usa este producto
      </p>
      {((legacyRules && legacyRules.length > 0) || (technicalRules && technicalRules.length > 0)) && (
        <ul className="mb-2 space-y-1 text-xs text-gray-600 dark:text-gray-400">
          {legacyRules?.map((r) => (
            <li key={`legacy-${r.id}`} className="flex items-center justify-between">
              <span>{describeAccessoryRule(r.quantity, r.target_tag, r.per_source_units)}</span>
              <button
                className="text-red-600 hover:underline dark:text-red-400"
                onClick={() => deleteLegacyRule.mutate(r.id)}
              >
                Eliminar
              </button>
            </li>
          ))}
          {technicalRules?.map((r) => (
            <li key={`technical-${r.id}`} className="flex items-center justify-between">
              <span>{describeTechnicalRule(r)}</span>
              <button
                className="text-red-600 hover:underline dark:text-red-400"
                onClick={() => deleteTechnicalRule.mutate(r.id)}
              >
                Eliminar
              </button>
            </li>
          ))}
        </ul>
      )}
      <form
        className="space-y-2"
        onSubmit={(e) => {
          e.preventDefault()
          createRule.mutate()
        }}
      >
        <div className="grid grid-cols-3 gap-2">
          {(Object.keys(ACTION_TYPE_LABELS) as TechnicalRuleActionType[]).map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => setActionType(type)}
              className={`rounded-xl px-2 py-2 text-xs font-medium ${
                actionType === type
                  ? 'bg-brand-blue text-white'
                  : 'bg-brand-gray text-gray-500 dark:bg-gray-800 dark:text-gray-400'
              }`}
            >
              {ACTION_TYPE_LABELS[type]}
            </button>
          ))}
        </div>

        {actionType === 'add_accessory' && (
          <>
            <Field label='Tag del accesorio a sugerir — ej: "nvr", "poe-switch", "disco-duro"'>
              <Input required value={targetTag} onChange={(e) => setTargetTag(e.target.value)} />
            </Field>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setProportional(false)}
                className={`flex-1 rounded-xl px-3 py-2 text-sm font-medium ${
                  !proportional
                    ? 'bg-brand-blue text-white'
                    : 'bg-brand-gray text-gray-500 dark:bg-gray-800 dark:text-gray-400'
                }`}
              >
                Fijo
              </button>
              <button
                type="button"
                onClick={() => setProportional(true)}
                className={`flex-1 rounded-xl px-3 py-2 text-sm font-medium ${
                  proportional
                    ? 'bg-brand-blue text-white'
                    : 'bg-brand-gray text-gray-500 dark:bg-gray-800 dark:text-gray-400'
                }`}
              >
                Proporcional
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {proportional && (
                <Field label="Por cada X de este producto">
                  <Input
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={perSourceUnits}
                    onChange={(e) => setPerSourceUnits(e.target.value)}
                  />
                </Field>
              )}
              <Field label="Cantidad a agregar">
                <Input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={ruleQuantity}
                  onChange={(e) => setRuleQuantity(e.target.value)}
                />
              </Field>
            </div>
          </>
        )}

        {actionType === 'set_calculation_parameter' && (
          <>
            <Field label="Parámetro a ajustar mientras este producto esté presente">
              <select
                required
                className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
                value={parameterKey}
                onChange={(e) => setParameterKey(e.target.value)}
              >
                <option value="" disabled>
                  Selecciona un parámetro…
                </option>
                {calculationParameters?.map((p) => (
                  <option key={p.key} value={p.key}>
                    {p.description ?? p.key}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Nuevo valor">
              <Input
                type="number"
                step="0.0001"
                required
                value={parameterValue}
                onChange={(e) => setParameterValue(e.target.value)}
              />
            </Field>
          </>
        )}

        {actionType === 'flag_engineering_note' && (
          <Field label="Nota a agregar al borrador de ingeniería">
            <Textarea required rows={2} value={engineeringNote} onChange={(e) => setEngineeringNote(e.target.value)} />
          </Field>
        )}

        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
        <Button type="submit" disabled={createRule.isPending || !canSubmit}>
          {createRule.isPending ? 'Guardando…' : '+ Agregar regla'}
        </Button>
      </form>
    </div>
  )
}
