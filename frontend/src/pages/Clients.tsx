import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ChevronRight, FolderOpen, Hash, Mail, MapPin, MessageCircle, Phone, Users, type LucideIcon } from 'lucide-react'
import { api, downloadFile } from '../lib/api'
import type { Client, ClientInput, Project } from '../lib/types'
import { useAuthStore } from '../lib/authStore'
import { Button, Card } from '../components/ui'
import { ClientFormFields } from '../components/ClientFormFields'
import { Avatar, EmptyState, SearchBox, StatTile, normalize } from '../components/ListTools'

function useClients() {
  return useQuery({
    queryKey: ['clients'],
    queryFn: async () => (await api.get<Client[]>('/clients')).data,
  })
}

/** Mensaje del servidor (texto) si lo hay; los errores de validación (422) vienen como lista. */
function errorDetail(error: unknown): string | null {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : null
}

function emptyClient(): ClientInput {
  return { name: '', company: '', rnc: '', phone: '', email: '', address: '', location_url: '', notes: '' }
}

type ProjectCount = { total: number; active: number }

export function Clients() {
  const { data: clients, isLoading } = useClients()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<ClientInput>(emptyClient())
  const [search, setSearch] = useState('')
  const queryClient = useQueryClient()
  const role = useAuthStore((s) => s.user?.role)
  const canExport = role === 'admin' || role === 'oficina'

  // Los proyectos casi siempre ya están en caché (Inicio, Proyectos): sirven para contar los de cada cliente.
  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => (await api.get<Project[]>('/projects')).data,
  })
  const projectsByClient = useMemo(() => {
    const counts = new Map<number, ProjectCount>()
    for (const p of projects ?? []) {
      const row = counts.get(p.client_id) ?? { total: 0, active: 0 }
      row.total += 1
      if (p.status !== 'cerrado') row.active += 1
      counts.set(p.client_id, row)
    }
    return counts
  }, [projects])

  const createClient = useMutation({
    mutationFn: async (payload: ClientInput) => (await api.post('/clients', payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      setShowForm(false)
      setForm(emptyClient())
    },
  })

  const query = normalize(search.trim())
  const visible = (clients ?? []).filter(
    (c) => !query || [c.name, c.company, c.phone, c.email, c.rnc, c.address].some((field) => normalize(field).includes(query)),
  )
  const withActiveWork = (clients ?? []).filter((c) => (projectsByClient.get(c.id)?.active ?? 0) > 0).length

  return (
    <div className="space-y-4 py-4 md:space-y-6 md:py-8">
      <div className="flex items-center justify-between md:justify-end">
        <h1 className="text-xl font-semibold text-gray-900 md:sr-only dark:text-gray-100">Clientes</h1>
        <div className="flex shrink-0 gap-2">
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
        <Card className="md:mx-auto md:max-w-2xl">
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault()
              createClient.mutate(form)
            }}
          >
            <ClientFormFields form={form} setForm={setForm} />
            {createClient.isError && (
              <p className="text-sm text-red-600 dark:text-red-400">
                {errorDetail(createClient.error) ?? 'No se pudo guardar el cliente. Intenta de nuevo.'}
              </p>
            )}
            <Button type="submit" disabled={createClient.isPending}>
              {createClient.isPending ? 'Guardando…' : 'Guardar cliente'}
            </Button>
          </form>
        </Card>
      )}

      {clients && clients.length > 0 && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 md:gap-4">
          <StatTile icon={Users} label="Clientes" value={clients.length} tone="bg-blue-50 text-brand-blue dark:bg-blue-950 dark:text-blue-300" />
          <StatTile
            icon={FolderOpen}
            label="Con trabajos en curso"
            value={withActiveWork}
            tone="bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
          />
          <div className="col-span-2 flex items-center md:col-span-1">
            <SearchBox value={search} onChange={setSearch} placeholder="Buscar por nombre, teléfono, RNC…" label="Buscar cliente" />
          </div>
        </div>
      )}

      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 md:gap-4 xl:grid-cols-3">
        {visible.map((client) => (
          <ClientCard key={client.id} client={client} projects={projectsByClient.get(client.id)} />
        ))}
        {clients?.length === 0 && <EmptyState icon={Users}>Aún no hay clientes. Toca «+ Nuevo» para agregar el primero.</EmptyState>}
        {clients && clients.length > 0 && visible.length === 0 && (
          <EmptyState icon={Users}>Ningún cliente coincide con «{search}».</EmptyState>
        )}
      </div>
    </div>
  )
}

/** Solo dígitos, con el 1 de República Dominicana delante si es un número local de 10 dígitos. */
function whatsappNumber(phone: string): string {
  const digits = phone.replace(/\D/g, '')
  return digits.length === 10 ? `1${digits}` : digits
}

function ClientCard({ client, projects }: { client: Client; projects?: ProjectCount }) {
  const details: { icon: LucideIcon; text: string }[] = []
  if (client.phone) details.push({ icon: Phone, text: client.phone })
  if (client.email) details.push({ icon: Mail, text: client.email })
  if (client.address) details.push({ icon: MapPin, text: client.address })
  if (client.rnc) details.push({ icon: Hash, text: `RNC ${client.rnc}` })

  return (
    <div className="flex flex-col rounded-3xl bg-white shadow-sm ring-1 ring-black/5 transition hover:-translate-y-0.5 hover:shadow-md dark:bg-gray-900 dark:ring-white/10">
      <Link to={`/clientes/${client.id}`} className="group flex flex-1 flex-col gap-3 p-5">
        <div className="flex items-center gap-3">
          <Avatar name={client.name} />
          <div className="min-w-0 flex-1">
            <p className="truncate text-base font-semibold text-gray-900 dark:text-gray-100">{client.name}</p>
            {client.company && <p className="truncate text-sm text-gray-500 dark:text-gray-400">{client.company}</p>}
          </div>
          <ChevronRight
            className="h-5 w-5 shrink-0 text-gray-300 transition group-hover:translate-x-0.5 group-hover:text-brand-blue"
            aria-hidden="true"
          />
        </div>
        {details.length > 0 && (
          <ul className="space-y-1.5 text-sm text-gray-600 dark:text-gray-400">
            {details.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-2">
                <Icon className="h-4 w-4 shrink-0 text-gray-400" aria-hidden="true" />
                <span className="truncate">{text}</span>
              </li>
            ))}
          </ul>
        )}
      </Link>
      <div className="flex items-center gap-2 border-t border-gray-100 px-5 py-3 dark:border-gray-800">
        <span className="flex-1 text-xs font-medium text-gray-500 dark:text-gray-400">
          {projects
            ? `${projects.total} ${projects.total === 1 ? 'proyecto' : 'proyectos'}${projects.active ? ` · ${projects.active} en curso` : ''}`
            : 'Sin proyectos'}
        </span>
        {client.phone && (
          <>
            <a
              href={`tel:${client.phone}`}
              aria-label={`Llamar a ${client.name}`}
              title="Llamar"
              className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-50 text-brand-blue hover:bg-brand-blue hover:text-white dark:bg-blue-950 dark:text-blue-300"
            >
              <Phone className="h-4 w-4" aria-hidden="true" />
            </a>
            <a
              href={`https://wa.me/${whatsappNumber(client.phone)}`}
              target="_blank"
              rel="noreferrer"
              aria-label={`WhatsApp a ${client.name}`}
              title="WhatsApp"
              className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-50 text-emerald-700 hover:bg-emerald-600 hover:text-white dark:bg-emerald-950 dark:text-emerald-300"
            >
              <MessageCircle className="h-4 w-4" aria-hidden="true" />
            </a>
          </>
        )}
      </div>
    </div>
  )
}
