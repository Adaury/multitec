import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import type { Client, ClientInput } from '../lib/types'
import { Button, Card, Field, Input, Textarea } from '../components/ui'

function useClients() {
  return useQuery({
    queryKey: ['clients'],
    queryFn: async () => (await api.get<Client[]>('/clients')).data,
  })
}

function emptyClient(): ClientInput {
  return { name: '', company: '', rnc: '', phone: '', email: '', address: '', notes: '' }
}

export function Clients() {
  const { data: clients, isLoading } = useClients()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<ClientInput>(emptyClient())
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const createClient = useMutation({
    mutationFn: async (payload: ClientInput) => (await api.post('/clients', payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      setShowForm(false)
      setForm(emptyClient())
    },
  })

  return (
    <div className="space-y-4 py-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Clientes</h1>
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
              createClient.mutate(form)
            }}
          >
            <Field label="Nombre">
              <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </Field>
            <Field label="Empresa">
              <Input value={form.company ?? ''} onChange={(e) => setForm({ ...form, company: e.target.value })} />
            </Field>
            <Field label="RNC">
              <Input value={form.rnc ?? ''} onChange={(e) => setForm({ ...form, rnc: e.target.value })} />
            </Field>
            <Field label="Teléfono">
              <Input value={form.phone ?? ''} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </Field>
            <Field label="Correo">
              <Input type="email" value={form.email ?? ''} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </Field>
            <Field label="Dirección">
              <Textarea value={form.address ?? ''} onChange={(e) => setForm({ ...form, address: e.target.value })} />
            </Field>
            <Field label="Observaciones">
              <Textarea value={form.notes ?? ''} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            </Field>
            <Button type="submit" disabled={createClient.isPending}>
              {createClient.isPending ? 'Guardando…' : 'Guardar cliente'}
            </Button>
          </form>
        </Card>
      )}

      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}

      <div className="space-y-3">
        {clients?.map((client) => (
          <Card
            key={client.id}
            className="cursor-pointer active:scale-[0.98]"
          >
            <button className="w-full text-left" onClick={() => navigate(`/clientes/${client.id}`)}>
              <p className="font-medium text-gray-900">{client.name}</p>
              {client.company && <p className="text-sm text-gray-500">{client.company}</p>}
              <div className="mt-1 flex gap-3 text-xs text-gray-400">
                {client.rnc && <span>RNC {client.rnc}</span>}
                {client.phone && <span>{client.phone}</span>}
              </div>
            </button>
          </Card>
        ))}
        {clients?.length === 0 && <p className="text-sm text-gray-500">Aún no hay clientes.</p>}
      </div>
    </div>
  )
}
