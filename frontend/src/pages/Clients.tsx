import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api, downloadFile } from '../lib/api'
import type { Client, ClientInput } from '../lib/types'
import { useAuthStore } from '../lib/authStore'
import { Button, Card } from '../components/ui'
import { ClientFormFields } from '../components/ClientFormFields'

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
  const role = useAuthStore((s) => s.user?.role)
  const canExport = role === 'admin' || role === 'oficina'

  const createClient = useMutation({
    mutationFn: async (payload: ClientInput) => (await api.post('/clients', payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      setShowForm(false)
      setForm(emptyClient())
    },
  })

  return (
    <div className="space-y-4 py-4 md:space-y-6 md:py-8">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900 md:text-2xl dark:text-gray-100">Clientes</h1>
        <div className="flex gap-2">
          {canExport && (
            <button
              onClick={() => downloadFile('/clients/export', 'clientes.csv')}
              className="rounded-full bg-brand-gray px-4 py-2 text-sm font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300"
            >
              Exportar CSV
            </button>
          )}
          <button
            onClick={() => setShowForm((v) => !v)}
            className="rounded-full bg-brand-blue px-4 py-2 text-sm font-medium text-white"
          >
            {showForm ? 'Cancelar' : '+ Nuevo'}
          </button>
        </div>
      </div>

      {showForm && (
        <Card className="md:max-w-2xl">
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault()
              createClient.mutate(form)
            }}
          >
            <ClientFormFields form={form} setForm={setForm} />
            <Button type="submit" disabled={createClient.isPending}>
              {createClient.isPending ? 'Guardando…' : 'Guardar cliente'}
            </Button>
          </form>
        </Card>
      )}

      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {clients?.map((client) => (
          <Card key={client.id} className="cursor-pointer active:scale-[0.98]">
            <button className="w-full text-left" onClick={() => navigate(`/clientes/${client.id}`)}>
              <p className="font-medium text-gray-900 dark:text-gray-100">{client.name}</p>
              {client.company && <p className="text-sm text-gray-500 dark:text-gray-400">{client.company}</p>}
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
