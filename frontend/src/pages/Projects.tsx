import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { api, downloadFile } from '../lib/api'
import type { Client, Project } from '../lib/types'
import { PROJECT_STATUS_LABELS } from '../lib/types'
import { useAuthStore } from '../lib/authStore'
import { Badge, Button, Card, Field, Textarea } from '../components/ui'

export function Projects() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [showForm, setShowForm] = useState(searchParams.get('nuevo') === '1')
  const [clientId, setClientId] = useState('')
  const [description, setDescription] = useState('')
  const queryClient = useQueryClient()
  const role = useAuthStore((s) => s.user?.role)
  const canExport = role === 'admin' || role === 'oficina'

  const { data: projects, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => (await api.get<Project[]>('/projects')).data,
  })

  const { data: clients } = useQuery({
    queryKey: ['clients'],
    queryFn: async () => (await api.get<Client[]>('/clients')).data,
  })

  const createProject = useMutation({
    mutationFn: async () =>
      (await api.post('/projects', { client_id: Number(clientId), description: description || null })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      setShowForm(false)
      setClientId('')
      setDescription('')
      setSearchParams({})
    },
  })

  return (
    <div className="space-y-4 py-4 md:space-y-6 md:py-8">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900 md:text-2xl dark:text-gray-100">Proyectos</h1>
        <div className="flex gap-2">
          {canExport && (
            <button
              onClick={() => downloadFile('/projects/export', 'proyectos.csv')}
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
              if (!clientId) return
              createProject.mutate()
            }}
          >
            <Field label="Cliente">
              <select
                required
                className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
                value={clientId}
                onChange={(e) => setClientId(e.target.value)}
              >
                <option value="">Selecciona un cliente…</option>
                {clients?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Descripción">
              <Textarea value={description} onChange={(e) => setDescription(e.target.value)} />
            </Field>
            {clients?.length === 0 && (
              <p className="text-sm text-amber-600">Primero debes crear un cliente.</p>
            )}
            <Button type="submit" disabled={createProject.isPending || !clientId}>
              {createProject.isPending ? 'Creando…' : 'Crear proyecto'}
            </Button>
          </form>
        </Card>
      )}

      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {projects?.map((project) => (
          <Link key={project.id} to={`/proyectos/${project.id}`}>
            <Card className="active:scale-[0.98]">
              <div className="flex items-center justify-between">
                <p className="font-medium text-gray-900 dark:text-gray-100">{project.code}</p>
                <Badge>{PROJECT_STATUS_LABELS[project.status] ?? project.status}</Badge>
              </div>
              {project.description && (
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{project.description}</p>
              )}
              <p className="mt-1 text-xs text-gray-400">{project.date}</p>
            </Card>
          </Link>
        ))}
        {projects?.length === 0 && <p className="text-sm text-gray-500">Aún no hay proyectos.</p>}
      </div>
    </div>
  )
}
