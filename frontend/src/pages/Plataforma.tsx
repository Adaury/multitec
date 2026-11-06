import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, apiErrorMessage } from '../lib/api'
import type { CompanyState, PlatformCompany, PlatformCompanyDetail, PlatformSummary } from '../lib/types'
import { enterSupport } from '../lib/support'
import { LifeBuoy, MessageCircle } from 'lucide-react'
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

const STATE_LABEL: Record<CompanyState, string> = {
  activa: 'Activa',
  prueba: 'En prueba',
  vencida: 'Prueba vencida',
  atrasada: 'Pago atrasado',
  cortada: 'Cortada por pago',
  suspendida: 'Suspendida',
}
const STATE_TONE: Record<CompanyState, 'green' | 'blue' | 'amber' | 'red'> = {
  activa: 'green',
  prueba: 'blue',
  vencida: 'amber',
  atrasada: 'amber',
  cortada: 'red',
  suspendida: 'red',
}

const money = (n: number) => `RD$${n.toLocaleString('es-DO', { maximumFractionDigits: 0 })}`
const waLink = (phone: string | null, text: string) =>
  phone ? `https://wa.me/${phone.replace(/\D/g, '').replace(/^(8[024]9)/, '1$1')}?text=${encodeURIComponent(text)}` : null

function StateBadge({ company }: { company: PlatformCompany }) {
  return <Badge tone={STATE_TONE[company.state]}>{STATE_LABEL[company.state]}</Badge>
}

function trialText(company: PlatformCompany): string | null {
  if (company.days_left === null) return null
  const what = company.paid_until ? 'Pagado hasta' : 'Prueba'
  if (company.days_left < 0) return `${what}: venció hace ${-company.days_left} días`
  if (company.days_left === 0) return `${what}: vence hoy`
  return `${what}: vence en ${company.days_left} días`
}

/** Portada del panel: cómo va el negocio, solicitudes nuevas y lo que vence pronto. */
function SummaryPanel() {
  const queryClient = useQueryClient()
  const { data } = useQuery({
    queryKey: ['platform-summary'],
    queryFn: async () => (await api.get<PlatformSummary>('/platform/summary')).data,
  })
  const reviewed = useMutation({
    mutationFn: async (id: number) => api.post(`/platform/companies/${id}/reviewed`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['platform-summary'] }),
  })
  if (!data) return null
  const tiles: [string, string | number][] = [
    ['En prueba', data.by_state.prueba ?? 0],
    ['Pagando', data.paying_companies],
    ['Atrasadas o cortadas', (data.by_state.atrasada ?? 0) + (data.by_state.cortada ?? 0) + (data.by_state.vencida ?? 0)],
    ['Cobrado este mes', money(data.collected_this_month)],
    ['Mensualidades al mes', money(data.expected_monthly)],
  ]
  return (
    <div className="space-y-3" data-testid="platform-summary">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        {tiles.map(([label, value]) => (
          <Card key={label}>
            <p className="text-xs text-gray-500">{label}</p>
            <p className="text-xl font-semibold text-gray-900 dark:text-gray-100">{value}</p>
          </Card>
        ))}
      </div>
      {data.new_requests.length > 0 && (
        <Card>
          <p className="mb-2 font-medium text-gray-900 dark:text-gray-100">Solicitudes nuevas ({data.new_requests.length})</p>
          <ul className="divide-y divide-gray-100 dark:divide-gray-800">
            {data.new_requests.map((r) => {
              const wa = waLink(r.contact_phone, `Hola ${r.contact_name ?? ''}, te escribimos de Multitec por el registro de ${r.name}.`)
              return (
                <li key={r.id} className="flex flex-wrap items-center gap-2 py-2 text-sm">
                  <Link to={`/plataforma/${r.id}`} className="min-w-0 flex-1">
                    <span className="block font-medium text-gray-900 dark:text-gray-100">{r.name}</span>
                    <span className="block truncate text-xs text-gray-500">
                      {r.contact_name} · {r.contact_email} · {r.contact_phone} · {timeAgo(r.created_at)}
                    </span>
                  </Link>
                  {wa && (
                    <a href={wa} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 rounded-full bg-emerald-600 px-3 py-1 text-xs font-semibold text-white">
                      <MessageCircle className="h-3.5 w-3.5" aria-hidden="true" /> WhatsApp
                    </a>
                  )}
                  <button type="button" onClick={() => reviewed.mutate(r.id)} className="rounded-full bg-brand-gray px-3 py-1 text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-200">
                    Marcar vista
                  </button>
                </li>
              )
            })}
          </ul>
        </Card>
      )}
      {data.expiring.length > 0 && (
        <Card>
          <p className="mb-2 font-medium text-gray-900 dark:text-gray-100">Vencen pronto</p>
          <ul className="flex flex-wrap gap-2 text-sm">
            {data.expiring.map((c) => (
              <li key={c.id}>
                <Link to={`/plataforma/${c.id}`} className="inline-flex items-center gap-2 rounded-full bg-amber-50 px-3 py-1 text-amber-900 ring-1 ring-amber-200 dark:bg-amber-950/40 dark:text-amber-200 dark:ring-amber-900">
                  {c.name} · {c.days_left !== null && c.days_left < 0 ? `venció hace ${-c.days_left} d` : `${c.days_left} d`}
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
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
          <h1 className="text-2xl font-semibold text-gray-900 sr-only dark:text-gray-100">Plataforma</h1>
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

      <SummaryPanel />

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
                  {c.source === 'registro' && <span className="ml-1 text-xs font-normal text-brand-blue">· se registró sola</span>}
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
          <h1 className="text-2xl font-semibold text-gray-900 md:text-3xl md:font-bold md:tracking-tight dark:text-gray-100">{company.name}</h1>
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

      {company.id !== 1 && <ContactAndSupport company={company} />}
      {company.id !== 1 && <Billing company={company} onChange={refresh} />}

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


/** Contacto de la empresa y «Entrar como soporte» (1 hora, solo lectura salvo que se permitan cambios). */
function ContactAndSupport({ company }: { company: PlatformCompanyDetail }) {
  const [allowChanges, setAllowChanges] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const start = useMutation({
    mutationFn: async () =>
      (
        await api.post<{ access_token: string; company_id: number; company_name: string }>(
          `/platform/companies/${company.id}/support-session`,
          { allow_changes: allowChanges },
        )
      ).data,
    onSuccess: (s) => enterSupport(s.access_token, s.company_id, s.company_name),
    onError: (e) => setError(apiErrorMessage(e, 'No se pudo abrir la sesión de soporte')),
  })
  const wa = waLink(company.contact_phone, `Hola ${company.contact_name ?? ''}, te escribimos de Multitec.`)
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <Card>
        <p className="mb-2 font-medium text-gray-900 dark:text-gray-100">Contacto</p>
        <p className="text-sm text-gray-700 dark:text-gray-300">{company.contact_name ?? '—'}</p>
        <p className="text-sm text-gray-500">{company.contact_email ?? ''}</p>
        <p className="text-sm text-gray-500">{company.contact_phone ?? ''}</p>
        {wa && (
          <a href={wa} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-emerald-600 px-3 py-1 text-sm font-semibold text-white">
            <MessageCircle className="h-4 w-4" aria-hidden="true" /> Escribir por WhatsApp
          </a>
        )}
      </Card>
      <Card>
        <p className="mb-2 flex items-center gap-1.5 font-medium text-gray-900 dark:text-gray-100">
          <LifeBuoy className="h-4 w-4 text-brand-blue" aria-hidden="true" /> Soporte
        </p>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Entra a la empresa como su administrador durante 1 hora. Queda anotado en su auditoría.
        </p>
        <label className="mt-2 flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
          <input type="checkbox" checked={allowChanges} onChange={(e) => setAllowChanges(e.target.checked)} className="h-4 w-4 rounded" />
          Permitir cambios (si no, solo lectura)
        </label>
        {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
        <Button
          className="mt-3 !w-auto !px-4 !py-2.5 text-sm"
          disabled={start.isPending}
          onClick={() => {
            const msg = allowChanges
              ? `¿Entrar a «${company.name}» con permiso para CAMBIAR datos?`
              : `¿Entrar a «${company.name}» en solo lectura?`
            if (window.confirm(msg)) start.mutate()
          }}
        >
          Entrar como soporte
        </Button>
      </Card>
    </div>
  )
}

const KIND_LABEL = { instalacion: 'Instalación y explicación', mensualidad: 'Mensualidad' } as const

/** Cobros: tarifas de la empresa, «pagado hasta» y registrar un pago recibido. */
function Billing({ company, onChange }: { company: PlatformCompanyDetail; onChange: () => void }) {
  const today = new Date().toISOString().slice(0, 10)
  const emptyPayment = {
    kind: (company.setup_paid_at ? 'mensualidad' : 'instalacion') as 'instalacion' | 'mensualidad',
    amount: String(company.setup_paid_at ? company.monthly_fee : company.setup_fee),
    months: company.setup_paid_at ? '1' : '1',
    method: 'transferencia',
    reference: '',
    paid_at: today,
  }
  const [payment, setPayment] = useState(emptyPayment)
  const [fees, setFees] = useState({ setup: String(company.setup_fee), monthly: String(company.monthly_fee) })
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState<string | null>(null)

  const pay = useMutation({
    mutationFn: async () =>
      api.post(`/platform/companies/${company.id}/payments`, {
        kind: payment.kind,
        amount: Number(payment.amount),
        months: Number(payment.months),
        method: payment.method,
        reference: payment.reference.trim() || null,
        paid_at: payment.paid_at || null,
      }),
    onSuccess: () => {
      setError(null)
      setSaved('Pago registrado.')
      setPayment({ ...emptyPayment, kind: 'mensualidad', amount: String(company.monthly_fee) })
      onChange()
    },
    onError: (e) => setError(apiErrorMessage(e, 'No se pudo registrar el pago')),
  })
  const saveFees = useMutation({
    mutationFn: async () => api.put(`/platform/companies/${company.id}`, { setup_fee: Number(fees.setup), monthly_fee: Number(fees.monthly) }),
    onSuccess: () => {
      setSaved('Tarifas guardadas.')
      onChange()
    },
    onError: (e) => setError(apiErrorMessage(e, 'No se pudieron guardar las tarifas')),
  })

  return (
    <Card testId="billing">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-medium text-gray-900 dark:text-gray-100">Cobros</p>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          {company.setup_paid_at ? '✓ Instalación pagada' : 'Instalación pendiente'} ·{' '}
          {company.paid_until ? `Pagado hasta ${new Date(company.paid_until).toLocaleDateString('es-DO')}` : 'Sin mensualidades aún'}
        </p>
      </div>

      <form
        className="grid grid-cols-2 gap-3 md:grid-cols-6"
        onSubmit={(e) => {
          e.preventDefault()
          pay.mutate()
        }}
      >
        <Field label="Concepto">
          <select
            value={payment.kind}
            onChange={(e) => {
              const kind = e.target.value as 'instalacion' | 'mensualidad'
              setPayment({ ...payment, kind, amount: String(kind === 'instalacion' ? company.setup_fee : company.monthly_fee) })
            }}
            className="w-full rounded-2xl border border-gray-200 bg-white px-3 py-3 text-base dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
          >
            <option value="instalacion">{KIND_LABEL.instalacion}</option>
            <option value="mensualidad">{KIND_LABEL.mensualidad}</option>
          </select>
        </Field>
        <Field label="Monto (RD$)">
          <Input type="number" min={1} step="0.01" required value={payment.amount} onChange={(e) => setPayment({ ...payment, amount: e.target.value })} />
        </Field>
        <Field label="Meses de servicio">
          <Input type="number" min={0} max={36} required value={payment.months} onChange={(e) => setPayment({ ...payment, months: e.target.value })} />
        </Field>
        <Field label="Forma de pago">
          <select
            value={payment.method}
            onChange={(e) => setPayment({ ...payment, method: e.target.value })}
            className="w-full rounded-2xl border border-gray-200 bg-white px-3 py-3 text-base dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
          >
            {['transferencia', 'deposito', 'efectivo', 'tarjeta', 'otro'].map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Referencia">
          <Input value={payment.reference} maxLength={120} onChange={(e) => setPayment({ ...payment, reference: e.target.value })} />
        </Field>
        <Field label="Fecha">
          <Input type="date" value={payment.paid_at} max={today} onChange={(e) => setPayment({ ...payment, paid_at: e.target.value })} />
        </Field>
        <div className="col-span-2 md:col-span-6">
          <Button type="submit" className="!w-auto !px-5 !py-2.5 text-sm" disabled={pay.isPending}>
            {pay.isPending ? 'Guardando…' : 'Registrar pago'}
          </Button>
        </div>
      </form>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      {saved && <p className="mt-2 text-sm text-emerald-700" role="status">{saved}</p>}

      {company.payments.length > 0 && (
        <ul className="mt-4 divide-y divide-gray-100 text-sm dark:divide-gray-800">
          {company.payments.map((p) => (
            <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <span className="text-gray-900 dark:text-gray-100">
                {KIND_LABEL[p.kind]}
                {p.months > 0 && ` · ${p.months} mes(es)`}
                <span className="block text-xs text-gray-500">
                  {new Date(p.paid_at + 'T12:00:00').toLocaleDateString('es-DO')} · {p.method}
                  {p.reference ? ` · ${p.reference}` : ''}
                </span>
              </span>
              <span className="font-semibold text-gray-900 dark:text-gray-100">{money(p.amount)}</span>
            </li>
          ))}
        </ul>
      )}

      <form
        className="mt-4 flex flex-wrap items-end gap-2 border-t border-gray-100 pt-4 dark:border-gray-800"
        onSubmit={(e) => {
          e.preventDefault()
          saveFees.mutate()
        }}
      >
        <Field label="Instalación (RD$)">
          <Input type="number" min={0} value={fees.setup} onChange={(e) => setFees({ ...fees, setup: e.target.value })} />
        </Field>
        <Field label="Mensualidad (RD$)">
          <Input type="number" min={0} value={fees.monthly} onChange={(e) => setFees({ ...fees, monthly: e.target.value })} />
        </Field>
        <Button type="submit" variant="secondary" className="!w-auto !px-4 !py-3 text-sm" disabled={saveFees.isPending}>
          Guardar tarifas
        </Button>
      </form>
    </Card>
  )
}
