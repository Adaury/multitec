import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, apiErrorMessage } from '../lib/api'
import type { PlatformCompany, PlatformCompanyDetail } from '../lib/types'
import { timeAgo } from '../lib/userAgent'
import { AccessList, type AccessAccount } from '../components/AccessList'
import { Badge, Button, Card, Field, Input } from '../components/ui'

interface Created {
  company: PlatformCompany
  admin_email: string
  admin_user_id: number
  temporary_password: string
}

interface DemoCreated {
  company: PlatformCompany
  accounts: AccessAccount[]
}

const STATE_LABEL: Record<PlatformCompany['state'], string> = {
  activa: 'Activa',
  prueba: 'En prueba',
  vencida: 'Prueba vencida',
  suspendida: 'Suspendida',
}
const STATE_TONE: Record<PlatformCompany['state'], 'green' | 'blue' | 'amber' | 'red'> = {
  activa: 'green',
  prueba: 'blue',
  vencida: 'amber',
  suspendida: 'red',
}

function StateBadge({ company }: { company: PlatformCompany }) {
  return <Badge tone={STATE_TONE[company.state]}>{STATE_LABEL[company.state]}</Badge>
}

function trialText(company: PlatformCompany): string | null {
  if (company.days_left === null) return null
  if (company.days_left < 0) return `Venció hace ${-company.days_left} días`
  if (company.days_left === 0) return 'Vence hoy'
  return `Vence en ${company.days_left} días`
}

/** Panel del dueño del sistema: lista las empresas, crea una nueva con su administrador (o una demo con técnicos de
 * prueba), controla su periodo de prueba y las suspende o reactiva. */
export function Plataforma() {
  const { id } = useParams()
  return id ? <CompanyDetail id={Number(id)} /> : <CompanyList />
}

function CompanyList() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [showDemo, setShowDemo] = useState(false)
  const emptyForm = { name: '', admin_name: '', admin_email: '', notes: '', trial_days: '', max_users: '' }
  const [form, setForm] = useState(emptyForm)
  const [demo, setDemo] = useState({ name: '', technicians: '3', days: '14' })
  const [error, setError] = useState<string | null>(null)
  // Las claves temporales se muestran una sola vez; el servidor no las guarda en claro.
  const [created, setCreated] = useState<Created | null>(null)
  const [demoCreated, setDemoCreated] = useState<DemoCreated | null>(null)

  const { data: companies, isLoading } = useQuery({
    queryKey: ['platform-companies'],
    queryFn: async () => (await api.get<PlatformCompany[]>('/platform/companies')).data,
  })
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['platform-companies'] })

  const create = useMutation({
    mutationFn: async () =>
      (
        await api.post<Created>('/platform/companies', {
          name: form.name,
          admin_name: form.admin_name,
          admin_email: form.admin_email,
          notes: form.notes.trim() || null,
          trial_days: form.trial_days ? Number(form.trial_days) : null,
          max_users: form.max_users ? Number(form.max_users) : null,
        })
      ).data,
    onSuccess: (data) => {
      setCreated(data)
      setDemoCreated(null)
      setShowForm(false)
      setForm(emptyForm)
      setError(null)
      refresh()
    },
    onError: (e) => setError(apiErrorMessage(e, 'No se pudo crear la empresa')),
  })

  const createDemo = useMutation({
    mutationFn: async () =>
      (
        await api.post<DemoCreated>('/platform/demos', {
          name: demo.name.trim() || null,
          technicians: Number(demo.technicians),
          days: Number(demo.days),
        })
      ).data,
    onSuccess: (data) => {
      setDemoCreated(data)
      setCreated(null)
      setShowDemo(false)
      setError(null)
      refresh()
    },
    onError: (e) => setError(apiErrorMessage(e, 'No se pudo crear la empresa demo')),
  })

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">Plataforma</h1>
          <p className="text-sm text-gray-500">Las empresas que usan Multitec, cada una con sus datos separados.</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            className="!w-auto !px-4 !py-2.5 text-sm"
            onClick={() => {
              setShowDemo((v) => !v)
              setShowForm(false)
            }}
          >
            {showDemo ? 'Cancelar' : 'Crear demo para técnicos'}
          </Button>
          <Button
            className="!w-auto !px-4 !py-2.5 text-sm"
            onClick={() => {
              setShowForm((v) => !v)
              setShowDemo(false)
            }}
          >
            {showForm ? 'Cancelar' : 'Nueva empresa'}
          </Button>
        </div>
      </div>

      {created && (
        <Card testId="company-created">
          <p className="font-medium text-gray-900 dark:text-gray-100">Empresa «{created.company.name}» creada</p>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Entrégale estos datos a su administrador. La clave se muestra solo ahora y deberá cambiarla al entrar.
          </p>
          <AccessList
            companyId={created.company.id}
            companyName={created.company.name}
            validity={trialText(created.company)}
            accounts={[
              {
                user_id: created.admin_user_id,
                name: 'Administrador',
                email: created.admin_email,
                role: 'admin',
                temporary_password: created.temporary_password,
              },
            ]}
          />
          <Button variant="secondary" className="mt-3 !w-auto !px-4 !py-2 text-sm" onClick={() => setCreated(null)}>
            Ya la anoté
          </Button>
        </Card>
      )}

      {demoCreated && (
        <Card testId="demo-created">
          <p className="font-medium text-gray-900 dark:text-gray-100">Demo «{demoCreated.company.name}» lista</p>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            {trialText(demoCreated.company)}. Cada quien cambia su clave al entrar. Las claves se muestran solo ahora.
          </p>
          <AccessList
            companyId={demoCreated.company.id}
            companyName={demoCreated.company.name}
            validity={trialText(demoCreated.company)}
            accounts={demoCreated.accounts}
          />
          <Button variant="secondary" className="mt-3 !w-auto !px-4 !py-2 text-sm" onClick={() => setDemoCreated(null)}>
            Ya las anoté
          </Button>
        </Card>
      )}

      {showDemo && (
        <Card>
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault()
              createDemo.mutate()
            }}
          >
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Crea una empresa de prueba con un administrador, técnicos con su clave temporal y 3 clientes y proyectos de
              ejemplo. Se bloquea sola cuando termina el plazo.
            </p>
            <div className="grid gap-3 md:grid-cols-3">
              <Field label="Nombre (opcional)">
                <Input value={demo.name} onChange={(e) => setDemo({ ...demo, name: e.target.value })} />
              </Field>
              <Field label="Técnicos de prueba">
                <Input
                  type="number"
                  min={1}
                  max={10}
                  value={demo.technicians}
                  onChange={(e) => setDemo({ ...demo, technicians: e.target.value })}
                />
              </Field>
              <Field label="Días de prueba">
                <Input
                  type="number"
                  min={1}
                  max={90}
                  value={demo.days}
                  onChange={(e) => setDemo({ ...demo, days: e.target.value })}
                />
              </Field>
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <Button type="submit" disabled={createDemo.isPending}>
              {createDemo.isPending ? 'Creando…' : 'Crear empresa demo'}
            </Button>
          </form>
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
            <div className="grid gap-3 md:grid-cols-2">
              <Field label="Días de prueba (vacío = sin vencimiento)">
                <Input
                  type="number"
                  min={1}
                  max={365}
                  value={form.trial_days}
                  onChange={(e) => setForm({ ...form, trial_days: e.target.value })}
                />
              </Field>
              <Field label="Máximo de usuarios (vacío = sin tope)">
                <Input
                  type="number"
                  min={1}
                  max={1000}
                  value={form.max_users}
                  onChange={(e) => setForm({ ...form, max_users: e.target.value })}
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
                <p className="font-medium text-gray-900 dark:text-gray-100">
                  {c.name} {c.is_demo && <span className="text-xs font-normal text-gray-500">(demo)</span>}
                </p>
                <StateBadge company={c} />
              </div>
              <p className="mt-1 text-xs text-gray-500">
                Desde {new Date(c.created_at).toLocaleDateString('es-DO')}
                {trialText(c) && ` · ${trialText(c)}`}
              </p>
              <div className="mt-3 flex gap-4 text-sm text-gray-600 dark:text-gray-400">
                <span>
                  {c.users}
                  {c.max_users ? `/${c.max_users}` : ''} usuarios
                </span>
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
  const [maxUsers, setMaxUsers] = useState('')

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

  const update = useMutation({
    mutationFn: async (changes: Record<string, unknown>) => api.put(`/platform/companies/${id}`, changes),
    onSuccess: () => {
      setError(null)
      setMaxUsers('')
      refresh()
    },
    onError: (e) => setError(apiErrorMessage(e, 'No se pudo guardar')),
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
          {trialText(company) && <p className="text-sm text-gray-500">{trialText(company)}</p>}
        </div>
        <StateBadge company={company} />
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          ['Usuarios', company.max_users ? `${company.users} de ${company.max_users}` : company.users],
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

      {company.id !== 1 && (
        <Card>
          <p className="mb-3 font-medium text-gray-900 dark:text-gray-100">Plan y periodo de prueba</p>
          <div className="flex flex-wrap items-center gap-2">
            {[7, 14, 30].map((days) => (
              <Button
                key={days}
                variant="secondary"
                className="!w-auto !px-4 !py-2 text-sm"
                disabled={update.isPending}
                onClick={() => update.mutate({ extend_days: days })}
              >
                +{days} días
              </Button>
            ))}
            {company.trial_ends_at && (
              <Button
                variant="secondary"
                className="!w-auto !px-4 !py-2 text-sm"
                disabled={update.isPending}
                onClick={() => update.mutate({ clear_trial: true })}
              >
                Quitar vencimiento
              </Button>
            )}
          </div>
          <form
            className="mt-3 flex items-end gap-2"
            onSubmit={(e) => {
              e.preventDefault()
              if (maxUsers) update.mutate({ max_users: Number(maxUsers) })
            }}
          >
            <Field label={`Máximo de usuarios${company.max_users ? ` (ahora ${company.max_users})` : ' (sin tope)'}`}>
              <Input type="number" min={1} max={1000} value={maxUsers} onChange={(e) => setMaxUsers(e.target.value)} />
            </Field>
            <Button type="submit" variant="secondary" className="!w-auto !px-4 !py-3 text-sm" disabled={!maxUsers}>
              Guardar
            </Button>
            {company.max_users && (
              <Button
                type="button"
                variant="ghost"
                className="!w-auto !px-4 !py-3 text-sm"
                onClick={() => update.mutate({ clear_max_users: true })}
              >
                Sin tope
              </Button>
            )}
          </form>
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
