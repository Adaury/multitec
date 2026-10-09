import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { api, downloadFile } from '../lib/api'
import type { Client, ClientInput, Project } from '../lib/types'
import { PROJECT_STATUS_LABELS } from '../lib/types'
import { useAuthStore } from '../lib/authStore'
import { Badge, Button, Card, Field, Modal, Textarea } from '../components/ui'
import { ClientFormFields } from '../components/ClientFormFields'
import { ClientCombobox } from '../components/ClientCombobox'
import { IntakeAssistant } from '../components/IntakeAssistant'
import { SURVEY_TYPES } from '../lib/surveyTypes'

function emptyClient(): ClientInput {
  return { name: '', company: '', rnc: '', phone: '', email: '', address: '', location_url: '', notes: '' }
}

export function Projects() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [showForm, setShowForm] = useState(searchParams.get('nuevo') === '1')
  const [clientId, setClientId] = useState('')
  const [description, setDescription] = useState('')
  const [surveyType, setSurveyType] = useState('')
  const [showClientModal, setShowClientModal] = useState(false)
  // El cliente nuevo lo llena por defecto el asistente (pregunta nombre, teléfono y tipo).
  const [manualClient, setManualClient] = useState(false)
  const [newClient, setNewClient] = useState<ClientInput>(emptyClient())
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

  /** Abre el alta de cliente con el asistente; `typed` es lo que ya se escribió en el buscador. */
  function openNewClient(typed: string) {
    setNewClient({ ...emptyClient(), name: typed })
    setManualClient(false)
    setShowClientModal(true)
  }

  const createProject = useMutation({
    mutationFn: async () =>
      (
        await api.post('/projects', {
          client_id: Number(clientId),
          description: description || null,
          survey_type: surveyType || null,
        })
      ).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      setShowForm(false)
      setClientId('')
      setDescription('')
      setSurveyType('')
      setSearchParams({})
    },
  })

  const createClient = useMutation({
    mutationFn: async (payload: ClientInput) => (await api.post<Client>('/clients', payload)).data,
    onSuccess: (client) => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      setClientId(String(client.id))
      setShowClientModal(false)
      setNewClient(emptyClient())
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
            <div className="block text-left">
              <span className="mb-1 block text-sm font-medium text-gray-600 dark:text-gray-400">Cliente</span>
              <div className="flex items-start gap-2">
                <div className="min-w-0 flex-1">
                  <ClientCombobox
                    clients={clients ?? []}
                    value={clientId ? Number(clientId) : null}
                    onSelect={(c) => setClientId(String(c.id))}
                    onCreateNew={openNewClient}
                  />
                </div>
                <button
                  type="button"
                  onClick={() => openNewClient('')}
                  className="shrink-0 rounded-xl bg-brand-gray px-4 py-3 text-sm font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                >
                  + Nuevo
                </button>
              </div>
            </div>
            <Field label="Tipo de levantamiento">
              <select
                className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
                value={surveyType}
                onChange={(e) => setSurveyType(e.target.value)}
              >
                <option value="">Sin especificar</option>
                {SURVEY_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
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

      <Modal open={showClientModal} onClose={() => setShowClientModal(false)} title="Nuevo cliente">
        {manualClient ? (
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault()
              createClient.mutate(newClient)
            }}
          >
            <ClientFormFields form={newClient} setForm={setNewClient} />
            {createClient.isError && (
              <p className="text-sm text-red-600 dark:text-red-400">No se pudo crear el cliente.</p>
            )}
            <Button type="submit" disabled={createClient.isPending}>
              {createClient.isPending ? 'Guardando…' : 'Guardar cliente'}
            </Button>
            <button type="button" onClick={() => setManualClient(false)} className="text-sm text-brand-blue">
              🤖 Que el asistente me pregunte
            </button>
          </form>
        ) : (
          <div className="space-y-3">
            <IntakeAssistant
              initialName={newClient.name}
              busy={createClient.isPending}
              onComplete={(intake) => {
                if (intake.survey_type) setSurveyType(intake.survey_type)
                createClient.mutate({ ...newClient, name: intake.name, phone: intake.phone || null })
              }}
              onManual={() => setManualClient(true)}
            />
            {createClient.isError && (
              <p className="text-sm text-red-600 dark:text-red-400">No se pudo crear el cliente.</p>
            )}
          </div>
        )}
      </Modal>

      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {projects?.map((project) => (
          <Link key={project.id} to={`/proyectos/${project.id}`}>
            <Card className="active:scale-[0.98]">
              <div className="flex items-center justify-between">
                <p className="font-medium text-gray-900 dark:text-gray-100">{project.code}</p>
                <Badge>{PROJECT_STATUS_LABELS[project.status] ?? project.status}</Badge>
              </div>
              {project.survey_type && <p className="mt-1 text-xs font-medium text-brand-blue">{project.survey_type}</p>}
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
