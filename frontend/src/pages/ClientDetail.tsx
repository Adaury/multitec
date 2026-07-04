import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import type { Client, Project } from '../lib/types'
import { PROJECT_STATUS_LABELS } from '../lib/types'
import { Badge, Card } from '../components/ui'

export function ClientDetail() {
  const { id } = useParams()
  const navigate = useNavigate()

  const { data: client } = useQuery({
    queryKey: ['clients', id],
    queryFn: async () => (await api.get<Client>(`/clients/${id}`)).data,
  })

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => (await api.get<Project[]>('/projects')).data,
  })

  const clientProjects = projects?.filter((p) => p.client_id === Number(id))

  if (!client) return <p className="py-4 text-sm text-gray-500">Cargando…</p>

  return (
    <div className="space-y-4 py-4 md:space-y-6 md:py-8">
      <button onClick={() => navigate(-1)} className="text-sm text-brand-blue">
        ← Volver
      </button>

      <div className="md:grid md:grid-cols-[320px_1fr] md:items-start md:gap-6">
        <Card>
          <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">{client.name}</p>
          {client.company && <p className="text-sm text-gray-500 dark:text-gray-400">{client.company}</p>}
          <div className="mt-3 space-y-1 text-sm text-gray-600 dark:text-gray-400">
            {client.rnc && <p>RNC: {client.rnc}</p>}
            {client.phone && <p>Tel: {client.phone}</p>}
            {client.email && <p>Correo: {client.email}</p>}
            {client.address && <p>Dirección: {client.address}</p>}
            {client.notes && <p>Notas: {client.notes}</p>}
          </div>
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
