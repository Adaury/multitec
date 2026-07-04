import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Category } from '../lib/types'
import { Button, Card, Field, Input } from '../components/ui'

interface CategoryNode {
  category: Category
  children: CategoryNode[]
}

function buildTree(categories: Category[]): CategoryNode[] {
  const byParent = new Map<number | null, Category[]>()
  for (const c of categories) {
    const list = byParent.get(c.parent_id) ?? []
    list.push(c)
    byParent.set(c.parent_id, list)
  }
  const toNode = (c: Category): CategoryNode => ({
    category: c,
    children: (byParent.get(c.id) ?? []).map(toNode),
  })
  return (byParent.get(null) ?? []).map(toNode)
}

export function Categorias() {
  const queryClient = useQueryClient()
  const [newParentId, setNewParentId] = useState<number | null>(null)
  const [newName, setNewName] = useState('')
  const [newPrefix, setNewPrefix] = useState('')
  const [error, setError] = useState<string | null>(null)

  const { data: categories, isLoading } = useQuery({
    queryKey: ['categories'],
    queryFn: async () => (await api.get<Category[]>('/categories')).data,
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['categories'] })

  const createCategory = useMutation({
    mutationFn: async () =>
      (
        await api.post('/categories', {
          name: newName,
          parent_id: newParentId,
          code_prefix: newPrefix || null,
        })
      ).data,
    onSuccess: () => {
      invalidate()
      setNewName('')
      setNewPrefix('')
      setError(null)
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? 'No se pudo crear la categoría'),
  })

  const deleteCategory = useMutation({
    mutationFn: async (id: number) => (await api.delete(`/categories/${id}`)).data,
    onSuccess: invalidate,
    onError: (err: any) => setError(err?.response?.data?.detail ?? 'No se pudo eliminar la categoría'),
  })

  const tree = categories ? buildTree(categories) : []

  return (
    <div className="space-y-4 py-4 md:space-y-6 md:py-8">
      <h1 className="text-xl font-semibold text-gray-900 md:text-2xl dark:text-gray-100">Clasificaciones</h1>
      <p className="text-sm text-gray-500 dark:text-gray-400">
        Categorías y subcategorías del catálogo — se administran aquí, sin tocar código. El
        prefijo de código (ej. "CAM") es opcional: si no lo pones, el producto hereda el de
        la categoría padre más cercana que sí lo tenga.
      </p>

      <Card className="md:max-w-xl">
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault()
            createCategory.mutate()
          }}
        >
          <div className="grid gap-3 md:grid-cols-2">
            <Field label="Nombre">
              <Input required value={newName} onChange={(e) => setNewName(e.target.value)} />
            </Field>
            <Field label="Prefijo de código (opcional)">
              <Input
                value={newPrefix}
                onChange={(e) => setNewPrefix(e.target.value.toUpperCase())}
                maxLength={10}
                placeholder="ej: CAM"
              />
            </Field>
          </div>
          <Field label="Categoría padre (vacío = categoría raíz)">
            <select
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
              value={newParentId ?? ''}
              onChange={(e) => setNewParentId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">(raíz)</option>
              {categories?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </Field>
          {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
          <Button type="submit" disabled={createCategory.isPending || !newName}>
            {createCategory.isPending ? 'Guardando…' : '+ Agregar categoría'}
          </Button>
        </form>
      </Card>

      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}

      <div className="space-y-2">
        {tree.map((node) => (
          <CategoryTreeItem
            key={node.category.id}
            node={node}
            depth={0}
            onDelete={(id) => deleteCategory.mutate(id)}
          />
        ))}
      </div>
    </div>
  )
}

function CategoryTreeItem({
  node,
  depth,
  onDelete,
}: {
  node: CategoryNode
  depth: number
  onDelete: (id: number) => void
}) {
  const [expanded, setExpanded] = useState(depth === 0)
  const hasChildren = node.children.length > 0

  return (
    <div style={{ marginLeft: depth * 16 }}>
      <Card className="flex items-center justify-between py-2">
        <button
          className="flex flex-1 items-center gap-2 text-left"
          onClick={() => hasChildren && setExpanded((v) => !v)}
        >
          {hasChildren && <span className="text-xs text-gray-400">{expanded ? '▾' : '▸'}</span>}
          <span className="font-medium text-gray-900 dark:text-gray-100">{node.category.name}</span>
          {node.category.code_prefix && (
            <span className="rounded-full bg-brand-gray px-2 py-0.5 text-[10px] text-gray-500 dark:bg-gray-800 dark:text-gray-400">
              {node.category.code_prefix}
            </span>
          )}
        </button>
        <button
          className="text-xs text-red-600 hover:underline dark:text-red-400"
          onClick={() => {
            if (confirm(`¿Eliminar "${node.category.name}"?`)) onDelete(node.category.id)
          }}
        >
          Eliminar
        </button>
      </Card>
      {expanded && hasChildren && (
        <div className="mt-2 space-y-2">
          {node.children.map((child) => (
            <CategoryTreeItem key={child.category.id} node={child} depth={depth + 1} onDelete={onDelete} />
          ))}
        </div>
      )}
    </div>
  )
}
