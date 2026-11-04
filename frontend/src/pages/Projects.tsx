import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Calculator,
  CircleCheck,
  ClipboardList,
  FileText,
  FolderOpen,
  HardHat,
  Ruler,
  type LucideIcon,
} from 'lucide-react'
import { api, downloadFile } from '../lib/api'
import type { Client, ClientInput, Project } from '../lib/types'
import { PROJECT_STATUS_LABELS } from '../lib/types'
import { useAuthStore } from '../lib/authStore'
import { Badge, Button, Card, Field, Modal, Textarea } from '../components/ui'
import { EmptyState, FilterChips, SearchBox, normalize } from '../components/ListTools'
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

  const [statusFilter, setStatusFilter] = useState<StatusFilter>('activos')
  const [search, setSearch] = useState('')
  const clientNames = useMemo(() => new Map((clients ?? []).map((c) => [c.id, c.name])), [clients])
  const query = normalize(search.trim())
  const visible = (projects ?? []).filter((p) => {
    if (statusFilter === 'activos' && p.status === 'cerrado') return false
    if (statusFilter !== 'activos' && statusFilter !== 'todos' && p.status !== statusFilter) return false
    if (!query) return true
    return [clientNames.get(p.client_id), p.code, p.description, p.survey_type].some((f) => normalize(f).includes(query))
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
      <div className="flex items-center justify-between md:justify-end">
        <h1 className="text-xl font-semibold text-gray-900 md:sr-only dark:text-gray-100">Proyectos</h1>
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

      {projects && projects.length > 0 && (
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <FilterChips<StatusFilter>
            value={statusFilter}
            onChange={setStatusFilter}
            label="Filtrar por etapa"
            options={[
              { key: 'activos', label: 'En curso', count: projects.filter((p) => p.status !== 'cerrado').length },
              ...STAGES.map((stage) => ({
                key: stage as StatusFilter,
                label: PROJECT_STATUS_LABELS[stage],
                count: projects.filter((p) => p.status === stage).length,
              })).filter((option) => option.count > 0),
              { key: 'todos', label: 'Todos', count: projects.length },
            ]}
          />
          <SearchBox value={search} onChange={setSearch} placeholder="Buscar por cliente, código…" label="Buscar proyecto" />
        </div>
      )}

      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 md:gap-4 xl:grid-cols-3">
        {visible.map((project) => (
          <ProjectCard key={project.id} project={project} clientName={clientNames.get(project.client_id)} />
        ))}
        {projects?.length === 0 && (
          <EmptyState icon={FolderOpen}>Aún no hay proyectos. Toca «+ Nuevo» para crear el primero.</EmptyState>
        )}
        {projects && projects.length > 0 && visible.length === 0 && (
          <EmptyState icon={FolderOpen}>No hay proyectos con este filtro.</EmptyState>
        )}
      </div>
    </div>
  )
}

// Etapas en el orden en que avanza un trabajo.
const STAGES = ['levantamiento', 'ingenieria', 'presupuesto', 'cotizacion', 'ejecucion', 'cerrado'] as const
type StatusFilter = 'activos' | 'todos' | (typeof STAGES)[number]

const STAGE_STYLE: Record<string, { icon: LucideIcon; tone: string; bar: string }> = {
  levantamiento: { icon: ClipboardList, tone: 'bg-blue-50 text-brand-blue dark:bg-blue-950 dark:text-blue-300', bar: 'bg-brand-blue' },
  ingenieria: { icon: Ruler, tone: 'bg-violet-50 text-violet-700 dark:bg-violet-950 dark:text-violet-300', bar: 'bg-violet-500' },
  presupuesto: { icon: Calculator, tone: 'bg-cyan-50 text-cyan-700 dark:bg-cyan-950 dark:text-cyan-300', bar: 'bg-cyan-500' },
  cotizacion: { icon: FileText, tone: 'bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300', bar: 'bg-amber-500' },
  ejecucion: { icon: HardHat, tone: 'bg-orange-50 text-orange-700 dark:bg-orange-950 dark:text-orange-300', bar: 'bg-orange-500' },
  cerrado: { icon: CircleCheck, tone: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300', bar: 'bg-emerald-500' },
}

function ProjectCard({ project, clientName }: { project: Project; clientName?: string }) {
  const style = STAGE_STYLE[project.status] ?? STAGE_STYLE.levantamiento
  const Icon = style.icon
  const step = Math.max(0, STAGES.indexOf(project.status as (typeof STAGES)[number]))
  const date = new Date(`${project.date}T12:00:00`).toLocaleDateString('es-DO', { day: 'numeric', month: 'short', year: 'numeric' })
  return (
    <Link
      to={`/proyectos/${project.id}`}
      className="group flex flex-col gap-3 rounded-3xl bg-white p-5 shadow-sm ring-1 ring-black/5 transition hover:-translate-y-0.5 hover:shadow-md active:scale-[0.98] dark:bg-gray-900 dark:ring-white/10"
    >
      <div className="flex items-start gap-3">
        <span className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl ${style.tone}`}>
          <Icon className="h-6 w-6" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-base font-semibold text-gray-900 dark:text-gray-100">{clientName ?? project.code}</p>
          <p className="text-xs text-gray-400">
            {project.code} · {date}
          </p>
        </div>
        <Badge tone={project.status === 'cerrado' ? 'green' : project.status === 'cotizacion' ? 'amber' : 'blue'}>
          {PROJECT_STATUS_LABELS[project.status] ?? project.status}
        </Badge>
      </div>
      {project.survey_type && <p className="text-xs font-medium text-brand-blue dark:text-blue-300">{project.survey_type}</p>}
      {project.description && <p className="line-clamp-2 text-sm text-gray-600 dark:text-gray-400">{project.description}</p>}
      {/* Avance: una rayita por etapa, llenas hasta la actual. */}
      <div className="mt-auto flex gap-1" aria-label={`Etapa ${step + 1} de ${STAGES.length}`} role="img">
        {STAGES.map((stage, index) => (
          <span key={stage} className={`h-1.5 flex-1 rounded-full ${index <= step ? style.bar : 'bg-gray-100 dark:bg-gray-800'}`} />
        ))}
      </div>
    </Link>
  )
}
