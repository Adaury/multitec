import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, apiErrorMessage } from '../lib/api'
import type { PlatformCompany, PlatformCompanyDetail } from '../lib/types'
import { timeAgo } from '../lib/userAgent'
import { Badge, Button, Card, Field, Input } from '../components/ui'

interface Created {
  company: PlatformCompany
  admin_email: string
  temporary_password: string
}

/** Panel del dueño del sistema: lista las empresas, crea una nueva con su administrador y las suspende o reactiva. */
export function Plataforma() {
  const { id } = useParams()
  return id ? <CompanyDetail id={Number(id)} /> : <CompanyList />
}

function CompanyList() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', admin_name: '', admin_email: '', notes: '' })
  const [error, setError] = useState<string | null>(null)
  // La clave temporal se muestra una sola vez; el servidor no la guarda en claro.
  const [created, setCreated] = useState<Created | null>(null)

  const { data: companies, isLoading } = useQuery({
    queryKey: ['platform-companies'],
    queryFn: async () => (await api.get<PlatformCompany[]>('/platform/companies')).data,
  })

  const create = useMutation({
    mutationFn: async () =>
      (await api.post<Created>('/platform/companies', { ...form, notes: form.notes.trim() || null })).data,
    onSuccess: (data) => {
      setCreated(data)
      setShowForm(false)
      setForm({ name: '', admin_name: '', admin_email: '', notes: '' })
      setError(null)
      queryClient.invalidateQueries({ queryKey: ['platform-companies'] })
    },
    onError: (e) => setError(apiErrorMessage(e, 'No se pudo crear la empresa')),
  })

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">Plataforma</h1>
          <p className="text-sm text-gray-500">Las empresas que usan Multitec, cada una con sus datos separados.</p>
        </div>
        <Button className="!w-auto !px-4 !py-2.5 text-sm" onClick={() => setShowForm((v) => !v)}>
          {showForm ? 'Cancelar' : 'Nueva empresa'}
        </Button>
      </div>

      {created && (
        <Card testId="company-created">
          <p className="font-medium text-gray-900 dark:text-gray-100">Empresa «{created.company.name}» creada</p>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Entrégale estos datos a su administrador. La clave se muestra solo ahora y deberá cambiarla al entrar.
          </p>
          <dl className="mt-3 space-y-1 text-sm">
            <div className="flex gap-2">
              <dt className="text-gray-500">Correo:</dt>
              <dd className="font-mono">{created.admin_email}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-gray-500">Clave temporal:</dt>
              <dd className="font-mono" data-testid="temporary-password">
                {created.temporary_password}
              </dd>
            </div>
          </dl>
          <Button variant="secondary" className="mt-3 !w-auto !px-4 !py-2 text-sm" onClick={() => setCreated(null)}>
            Ya la anoté
          </Button>
        </Card>
      )}

      {showForm && (
        <Card>
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault()
              create.mutate()
            }}
          >
            <Field label="Nombre de la empresa">
              <Input required minLength={2} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </Field>
            <div className="grid gap-3 md:grid-cols-2">
              <Field label="Administrador (nombre)">
                <Input
                  required
                  minLength={2}
                  value={form.admin_name}
                  onChange={(e) => setForm({ ...form, admin_name: e.target.value })}
                />
              </Field>
              <Field label="Administrador (correo)">
                <Input
                  required
                  type="email"
                  value={form.admin_email}
                  onChange={(e) => setForm({ ...form, admin_email: e.target.value })}
                />
              </Field>
            </div>
            <Field label="Notas (opcional)">
              <Input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            </Field>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? 'Creando…' : 'Crear empresa y su administrador'}
            </Button>
          </form>
        </Card>
      )}

      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}
      <div className="grid gap-3 lg:grid-cols-2 2xl:grid-cols-3">
        {companies?.map((c) => (
          <Link key={c.id} to={`/plataforma/${c.id}`} data-testid={`company-${c.slug}`}>
            <Card className="transition hover:shadow-md">
              <div className="flex items-start justify-between gap-2">
                <p className="font-medium text-gray-900 dark:text-gray-100">{c.name}</p>
                <Badge tone={c.is_active ? 'green' : 'red'}>{c.is_active ? 'Activa' : 'Suspendida'}</Badge>
              </div>
              <p className="mt-1 text-xs text-gray-500">Desde {new Date(c.created_at).toLocaleDateString('es-DO')}</p>
              <div className="mt-3 flex gap-4 text-sm text-gray-600 dark:text-gray-400">
                <span>{c.users} usuarios</span>
                <span>{c.projects} proyectos</span>
                <span>{c.invoices} facturas</span>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  )
}

function CompanyDetail({ id }: { id: number }) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const [temporary, setTemporary] = useState<{ email: string; value: string } | null>(null)

  const { data: company, isLoading } = useQuery({
    queryKey: ['platform-company', id],
    queryFn: async () => (await api.get<PlatformCompanyDetail>(`/platform/companies/${id}`)).data,
  })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['platform-company', id] })
    queryClient.invalidateQueries({ queryKey: ['platform-companies'] })
  }

  const toggle = useMutation({
    mutationFn: async (action: 'suspend' | 'activate') => api.post(`/platform/companies/${id}/${action}`),
    onSuccess: () => {
      setError(null)
      refresh()
    },
    onError: (e) => setError(apiErrorMessage(e, 'No se pudo cambiar el estado')),
  })

  const resetAdmin = useMutation({
    mutationFn: async () =>
      (await api.post<{ email: string; temporary_password: string }>(`/platform/companies/${id}/reset-admin-password`))
        .data,
    onSuccess: (data) => {
      setError(null)
      setTemporary({ email: data.email, value: data.temporary_password })
    },
    onError: (e) => setError(apiErrorMessage(e, 'No se pudo restablecer la clave')),
  })

  if (isLoading || !company) return <p className="text-sm text-gray-500">Cargando…</p>

  return (
    <div className="space-y-5">
      <Link to="/plataforma" className="text-sm text-brand-blue">
        ← Todas las empresas
      </Link>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">{company.name}</h1>
          {company.notes && <p className="text-sm text-gray-500">{company.notes}</p>}
        </div>
        <Badge tone={company.is_active ? 'green' : 'red'}>{company.is_active ? 'Activa' : 'Suspendida'}</Badge>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          ['Usuarios', company.users],
          ['Proyectos', company.projects],
          ['Facturas', company.invoices],
          ['Archivos', `${company.storage_mb} MB`],
        ].map(([label, value]) => (
          <Card key={label}>
            <p className="text-xs text-gray-500">{label}</p>
            <p className="text-xl font-semibold text-gray-900 dark:text-gray-100">{value}</p>
          </Card>
        ))}
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {temporary && (
        <Card>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Clave temporal para <span className="font-mono">{temporary.email}</span> (se muestra una sola vez):
          </p>
          <p className="mt-1 font-mono text-lg" data-testid="temporary-password">
            {temporary.value}
          </p>
        </Card>
      )}

      <Card>
        <p className="mb-3 font-medium text-gray-900 dark:text-gray-100">Equipo</p>
        <ul className="divide-y divide-gray-100 dark:divide-gray-800">
          {company.team.map((u) => (
            <li key={u.id} className="flex items-center justify-between gap-3 py-2 text-sm">
              <div className="min-w-0">
                <p className="truncate text-gray-900 dark:text-gray-100">{u.name}</p>
                <p className="truncate text-xs text-gray-500">{u.email}</p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <span className="text-xs text-gray-500">
                  {u.last_login_at ? `Entró ${timeAgo(u.last_login_at)}` : 'Aún no ha entrado'}
                </span>
                <Badge tone={u.role === 'admin' ? 'blue' : 'gray'}>{u.role}</Badge>
              </div>
            </li>
          ))}
        </ul>
      </Card>

      <div className="flex flex-wrap gap-3">
        <Button
          variant="secondary"
          className="!w-auto !px-4 !py-2.5 text-sm"
          disabled={resetAdmin.isPending}
          onClick={() => {
            if (window.confirm('¿Generar una clave temporal nueva para el administrador de esta empresa?')) {
              resetAdmin.mutate()
            }
          }}
        >
          Restablecer clave del administrador
        </Button>
        {company.is_active ? (
          <Button
            variant="secondary"
            className="!w-auto !px-4 !py-2.5 text-sm !text-red-600"
            disabled={toggle.isPending}
            onClick={() => {
              if (window.confirm(`¿Suspender «${company.name}»? Nadie de esa empresa podrá entrar hasta reactivarla.`)) {
                toggle.mutate('suspend')
              }
            }}
          >
            Suspender empresa
          </Button>
        ) : (
          <Button className="!w-auto !px-4 !py-2.5 text-sm" disabled={toggle.isPending} onClick={() => toggle.mutate('activate')}>
            Reactivar empresa
          </Button>
        )}
      </div>
    </div>
  )
}
