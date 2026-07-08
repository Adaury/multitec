import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import type { Client, ClientInput, Project } from '../lib/types'
import { PROJECT_STATUS_LABELS } from '../lib/types'
import { Badge, Button, Card } from '../components/ui'
import { ClientFormFields } from '../components/ClientFormFields'

function clientToForm(client: Client): ClientInput {
  return {
    name: client.name,
    company: client.company,
    rnc: client.rnc,
    phone: client.phone,
    email: client.email,
    address: client.address,
    location_url: client.location_url,
    notes: client.notes,
  }
}

export function ClientDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [isEditing, setIsEditing] = useState(false)
  const [form, setForm] = useState<ClientInput | null>(null)

  const { data: client } = useQuery({
    queryKey: ['clients', id],
    queryFn: async () => (await api.get<Client>(`/clients/${id}`)).data,
  })

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => (await api.get<Project[]>('/projects')).data,
  })

  const updateClient = useMutation({
    mutationFn: async () => (await api.put(`/clients/${id}`, form)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients', id] })
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      setIsEditing(false)
    },
  })

  const clientProjects = projects?.filter((p) => p.client_id === Number(id))

  if (!client) return <p className="py-4 text-sm text-gray-500">Cargando…</p>

  function startEditing() {
    setForm(clientToForm(client!))
    setIsEditing(true)
  }

  return (
    <div className="space-y-4 py-4 md:space-y-6 md:py-8">
      <button onClick={() => navigate(-1)} className="text-sm text-brand-blue">
        ← Volver
      </button>

      <div className="md:grid md:grid-cols-[320px_1fr] md:items-start md:gap-6">
        <Card>
          {isEditing && form ? (
            <form
              className="space-y-3"
              onSubmit={(e) => {
                e.preventDefault()
                updateClient.mutate()
              }}
            >
              <ClientFormFields form={form} setForm={setForm} />
              {updateClient.isError && (
                <p className="text-sm text-red-600 dark:text-red-400">No se pudo guardar el cliente.</p>
              )}
              <div className="flex gap-2">
                <Button className="!w-auto flex-1" type="submit" disabled={updateClient.isPending}>
                  {updateClient.isPending ? 'Guardando…' : 'Guardar cambios'}
                </Button>
                <Button
                  className="!w-auto flex-1"
                  type="button"
                  variant="secondary"
                  onClick={() => setIsEditing(false)}
                  disabled={updateClient.isPending}
                >
                  Cancelar
                </Button>
              </div>
            </form>
          ) : (
            <>
              <div className="flex items-center justify-between gap-2">
                <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">{client.name}</p>
                <button
                  onClick={startEditing}
                  className="shrink-0 rounded-full bg-brand-gray px-3 py-1 text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                >
                  Editar
                </button>
              </div>
              {client.company && <p className="text-sm text-gray-500 dark:text-gray-400">{client.company}</p>}
              <div className="mt-3 space-y-1 text-sm text-gray-600 dark:text-gray-400">
                {client.rnc && <p>RNC: {client.rnc}</p>}
                {client.phone && <p>Tel: {client.phone}</p>}
                {client.email && <p>Correo: {client.email}</p>}
                {client.address && <p>Dirección: {client.address}</p>}
                {client.notes && <p>Notas: {client.notes}</p>}
              </div>
              {client.location_url && (
                <a
                  href={client.location_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-3 inline-block rounded-full bg-brand-blue px-4 py-2 text-sm font-medium text-white"
                >
                  🧭 Iniciar trayecto
                </a>
              )}
            </>
          )}
        </Card>

        <div className="mt-4 md:mt-0">
          <h2 className="mb-2 text-lg font-semibold text-gray-900 dark:text-gray-100">Proyectos</h2>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {clientProjects?.map((project) => (
              <Link key={project.id} to={`/proyectos/${project.id}`}>
                <Card className="active:scale-[0.98]">
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-gray-900 dark:text-gray-100">{project.code}</p>
                    <Badge>{PROJECT_STATUS_LABELS[project.status] ?? project.status}</Badge>
                  </div>
                  {project.description && (
                    <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{project.description}</p>
                  )}
                </Card>
              </Link>
            ))}
            {clientProjects?.length === 0 && (
              <p className="text-sm text-gray-500">Este cliente aún no tiene proyectos.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
