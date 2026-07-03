import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { NCF_TYPE_LABELS, NCF_TYPES, type NcfSequence, type NcfType } from '../lib/types'
import { useAuthStore } from '../lib/authStore'
import { Badge, Button, Card, Field, Input } from '../components/ui'

function emptyForm() {
  return { ncf_type: 'B01' as NcfType, description: '', range_start: '', range_end: '', expires_at: '' }
}

export function Ncf() {
  const currentUser = useAuthStore((s) => s.user)
  const queryClient = useQueryClient()
  const isAdmin = currentUser?.role === 'admin'

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(emptyForm())
  const [error, setError] = useState<string | null>(null)

  const { data: sequences, isLoading } = useQuery({
    queryKey: ['ncf-sequences'],
    queryFn: async () => (await api.get<NcfSequence[]>('/ncf-sequences')).data,
    enabled: isAdmin,
  })

  const createSequence = useMutation({
    mutationFn: async () =>
      (
        await api.post('/ncf-sequences', {
          ...form,
          range_start: Number(form.range_start),
          range_end: Number(form.range_end),
        })
      ).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ncf-sequences'] })
      setShowForm(false)
      setForm(emptyForm())
      setError(null)
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? 'Error al crear la secuencia'),
  })

  const toggleActive = useMutation({
    mutationFn: async ({ id, active }: { id: number; active: boolean }) =>
      (await api.put(`/ncf-sequences/${id}`, { active })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['ncf-sequences'] }),
  })

  if (!isAdmin) {
    return (
      <div className="py-4">
        <Card>
          <p className="text-sm text-gray-600">Solo un administrador puede gestionar secuencias NCF.</p>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-4 py-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Secuencias NCF</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-full bg-brand-blue px-4 py-2 text-sm font-medium text-white"
        >
          {showForm ? 'Cancelar' : '+ Nueva'}
        </button>
      </div>
      <p className="text-sm text-gray-500">
        Rangos de Números de Comprobante Fiscal autorizados por la DGII. Al convertir una prefactura en factura se
        toma automáticamente el siguiente número del rango vigente correspondiente.
      </p>

      {showForm && (
        <Card>
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault()
              createSequence.mutate()
            }}
          >
            <Field label="Tipo de comprobante">
              <select
                className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base"
                value={form.ncf_type}
                onChange={(e) => setForm({ ...form, ncf_type: e.target.value as NcfType })}
              >
                {NCF_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {NCF_TYPE_LABELS[t]}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Descripción">
              <Input
                required
                placeholder="Ej. Autorización DGII julio 2026"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Desde">
                <Input
                  type="number"
                  required
                  min={1}
                  value={form.range_start}
                  onChange={(e) => setForm({ ...form, range_start: e.target.value })}
                />
              </Field>
              <Field label="Hasta">
                <Input
                  type="number"
                  required
                  min={1}
                  value={form.range_end}
                  onChange={(e) => setForm({ ...form, range_end: e.target.value })}
                />
              </Field>
            </div>
            <Field label="Vence">
              <Input
                type="date"
                required
                value={form.expires_at}
                onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
              />
            </Field>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <Button type="submit" disabled={createSequence.isPending}>
              {createSequence.isPending ? 'Guardando…' : 'Crear secuencia'}
            </Button>
          </form>
        </Card>
      )}

      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}

      <div className="space-y-3">
        {sequences?.map((seq) => {
          const expired = new Date(seq.expires_at) < new Date(new Date().toDateString())
          const exhausted = seq.next_number > seq.range_end
          return (
            <Card key={seq.id} className="space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">{NCF_TYPE_LABELS[seq.ncf_type]}</p>
                  <p className="text-sm text-gray-500">{seq.description}</p>
                </div>
                <div className="flex items-center gap-2">
                  {expired && <Badge tone="red">Vencida</Badge>}
                  {!expired && exhausted && <Badge tone="red">Agotada</Badge>}
                  {!expired && !exhausted && (
                    <Badge tone={seq.active ? 'green' : 'red'}>{seq.active ? 'Activa' : 'Inactiva'}</Badge>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm text-gray-600">
                <p>
                  Rango: {seq.range_start.toString().padStart(8, '0')}–{seq.range_end.toString().padStart(8, '0')}
                </p>
                <p>Próximo: {seq.next_number.toString().padStart(8, '0')}</p>
                <p>Vence: {seq.expires_at}</p>
              </div>
              <button
                className="rounded-full bg-brand-gray px-3 py-1.5 text-xs font-medium text-gray-700"
                onClick={() => toggleActive.mutate({ id: seq.id, active: !seq.active })}
              >
                {seq.active ? 'Desactivar' : 'Activar'}
              </button>
            </Card>
          )
        })}
        {sequences?.length === 0 && <p className="text-sm text-gray-500">Aún no hay secuencias NCF registradas.</p>}
      </div>
    </div>
  )
}
