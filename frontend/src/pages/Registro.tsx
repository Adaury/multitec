import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { CalendarCheck2, Camera, CheckCircle2, ClipboardList, Users } from 'lucide-react'
import { api, apiErrorMessage } from '../lib/api'
import { useAuthStore } from '../lib/authStore'
import { Button, Card, Field, Input } from '../components/ui'
import type { CurrentUser } from '../lib/types'
import { platformMoney, type SitePlan } from '../lib/platformMoney'

interface SignupInfo {
  enabled: boolean
  trial_days: number
  currency: string
  setup_fee: number
  monthly_fee: number
  contact_phone: string
  plans: SitePlan[]
}

const FEATURES = [
  { icon: ClipboardList, text: 'Levantamientos con fotos y voz desde el celular' },
  { icon: Camera, text: 'Cotizaciones con IA y catálogo de cámaras, alarmas y cercos' },
  { icon: Users, text: 'Técnicos, visitas y tickets en un solo lugar' },
  { icon: CalendarCheck2, text: 'Facturas con NCF, compras 606 y reportes' },
]

/** Página pública: una empresa se registra sola y empieza su prueba gratis. */
export function Registro() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const setSession = useAuthStore((s) => s.setSession)
  const [planId, setPlanId] = useState<number | null>(null)
  const { data: info } = useQuery({
    queryKey: ['signup-info'],
    queryFn: async () => (await api.get<SignupInfo>('/signup/info')).data,
  })
  const [form, setForm] = useState({ company_name: '', admin_name: '', email: '', phone: '', website: '' })
  const [accept, setAccept] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Empresa ya creada: la clave temporal se muestra una sola vez y hay que cambiarla al entrar.
  const [created, setCreated] = useState<{ email: string; temporary_password: string } | null>(null)
  const [copied, setCopied] = useState(false)
  // ¿El correo está disponible? Se consulta al servidor mientras se escribe (con una pausa para no saturarlo).
  const [emailState, setEmailState] = useState<'idle' | 'checking' | 'available' | 'taken'>('idle')
  useEffect(() => {
    const email = form.email.trim().toLowerCase()
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) {
      setEmailState('idle')
      return
    }
    setEmailState('checking')
    let cancelled = false
    const timer = window.setTimeout(async () => {
      try {
        const { data } = await api.get<{ valid: boolean; available: boolean }>('/signup/check-email', { params: { email } })
        if (!cancelled) setEmailState(data.available ? 'available' : 'taken')
      } catch {
        if (!cancelled) setEmailState('idle') // sin respuesta: no se bloquea, el registro lo vuelve a validar
      }
    }, 500)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [form.email])
  // Plan: el que viene de la página de precios (?plan=), si no el destacado.
  useEffect(() => {
    if (!info || planId !== null || info.plans.length === 0) return
    const wanted = Number(params.get('plan'))
    const chosen = info.plans.find((p) => p.id === wanted) ?? info.plans.find((p) => p.highlighted) ?? info.plans[0]
    setPlanId(chosen.id)
  }, [info, params, planId])
  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: e.target.value })

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const { data } = await api.post<{ email: string; temporary_password: string }>(
        '/signup',
        { ...form, plan_id: planId, accept_terms: accept },
        { timeout: 120_000 },
      )
      // El sistema generó una clave temporal: se muestra una vez y se cambia al entrar.
      setCreated({ email: data.email, temporary_password: data.temporary_password })
    } catch (err) {
      setError(apiErrorMessage(err, 'No se pudo completar el registro. Intenta de nuevo.'))
    } finally {
      setBusy(false)
    }
  }

  async function enter() {
    if (!created) return
    setError(null)
    setBusy(true)
    try {
      const login = new URLSearchParams({ username: created.email, password: created.temporary_password })
      const { data } = await api.post('/auth/login', login, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })
      const { data: user } = await api.get<CurrentUser>('/auth/me', { headers: { Authorization: `Bearer ${data.access_token}` } })
      setSession(data.access_token, user)
      navigate('/perfil') // la clave es temporal: ahí se cambia antes de seguir
    } catch (err) {
      setError(apiErrorMessage(err, 'No se pudo entrar. Inicia sesión con tu correo y la clave temporal.'))
    } finally {
      setBusy(false)
    }
  }

  async function copyPassword() {
    if (!created) return
    try {
      await navigator.clipboard.writeText(created.temporary_password)
      setCopied(true)
    } catch {
      /* sin portapapeles: la clave está seleccionable en pantalla */
    }
  }

  const days = info?.trial_days ?? 45

  if (info && !info.enabled) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-brand-bg px-5 dark:bg-gray-950">
        <Card className="max-w-sm text-center">
          <p className="text-gray-700 dark:text-gray-300">El registro de empresas no está disponible en este momento.</p>
          <Link to="/login" className="mt-3 inline-block font-semibold text-brand-blue">
            Iniciar sesión
          </Link>
        </Card>
      </div>
    )
  }

  if (created) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-brand-bg px-5 py-8 dark:bg-gray-950">
        <Card className="w-full max-w-md space-y-4" testId="signup-created">
          <p className="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
            <CheckCircle2 className="h-6 w-6 text-emerald-600" aria-hidden="true" /> Tu empresa está lista
          </p>
          <p className="text-sm text-gray-700 dark:text-gray-300">
            Entra con <strong>{created.email}</strong> y esta clave temporal. Se muestra <strong>una sola vez</strong>: cópiala o
            anótala. Al entrar, el sistema te pedirá cambiarla por una tuya antes de seguir.
          </p>
          <div className="flex items-center gap-2 rounded-2xl bg-brand-gray p-3 dark:bg-gray-800">
            <code className="min-w-0 flex-1 select-all break-all text-lg font-bold text-gray-900 dark:text-gray-100">{created.temporary_password}</code>
            <button
              type="button"
              onClick={() => void copyPassword()}
              className="shrink-0 rounded-xl bg-white px-3 py-2 text-sm font-semibold text-brand-blue shadow-sm dark:bg-gray-900"
            >
              {copied ? 'Copiada' : 'Copiar'}
            </button>
          </div>
          {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
          <Button type="button" onClick={() => void enter()} disabled={busy}>
            {busy ? 'Entrando…' : 'Entrar y cambiar mi clave'}
          </Button>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-dvh bg-brand-bg px-5 py-8 dark:bg-gray-950">
      <div className="mx-auto grid w-full max-w-5xl gap-6 lg:grid-cols-2 lg:items-start">
        <div className="space-y-5 lg:sticky lg:top-8">
          <div className="flex items-center gap-3">
            <img src="/brand/multitec-logo-negro.png" alt="Multitec" className="h-14 w-auto shrink-0 dark:hidden" />
            <img src="/brand/multitec-logo-blanco.png" alt="Multitec" className="hidden h-14 w-auto shrink-0 dark:block" />
            <div>
              <p className="text-2xl font-extrabold tracking-tight text-gray-900 dark:text-gray-100">Multitec ERP</p>
              <p className="text-sm text-gray-500">Para empresas de seguridad electrónica</p>
            </div>
          </div>
          <h1 className="text-3xl font-extrabold leading-tight tracking-tight text-gray-900 md:text-4xl dark:text-gray-100">
            Prueba Multitec <span className="text-brand-blue">{days} días gratis</span>
          </h1>
          <ul className="space-y-2">
            {FEATURES.map((f) => (
              <li key={f.text} className="flex items-center gap-3 text-gray-700 dark:text-gray-300">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white text-brand-blue shadow-sm ring-1 ring-black/5 dark:bg-gray-900">
                  <f.icon className="h-5 w-5" aria-hidden="true" />
                </span>
                {f.text}
              </li>
            ))}
          </ul>
          {info && info.plans.length > 0 && (
            <fieldset className="space-y-2" data-testid="plan-picker">
              <legend className="mb-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
                Elige tu plan (después de los {days} días gratis)
              </legend>
              {info.plans.map((plan) => (
                <label
                  key={plan.id}
                  className={`flex cursor-pointer items-center gap-3 rounded-2xl bg-white p-4 shadow-sm ring-2 transition dark:bg-gray-900 ${
                    planId === plan.id ? 'ring-brand-blue' : 'ring-transparent'
                  }`}
                >
                  <input
                    type="radio"
                    name="plan"
                    checked={planId === plan.id}
                    onChange={() => setPlanId(plan.id)}
                    className="h-4 w-4 accent-brand-blue"
                  />
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-2 font-semibold text-gray-900 dark:text-gray-100">
                      {plan.name}
                      {plan.highlighted && (
                        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-bold text-amber-800">Más popular</span>
                      )}
                    </span>
                    <span className="block text-xs text-gray-500">
                      {plan.max_users ? `Hasta ${plan.max_users} usuarios` : 'Usuarios ilimitados'} · instalación{' '}
                      {platformMoney(plan.setup_price, info.currency)} una vez
                    </span>
                  </span>
                  <span className="text-right">
                    <span className="block text-xl font-extrabold text-gray-900 dark:text-gray-100">
                      {platformMoney(plan.monthly_price, info.currency)}
                    </span>
                    <span className="text-xs text-gray-500">/mes</span>
                  </span>
                </label>
              ))}
              <p className="flex items-center gap-1.5 text-xs text-gray-500">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-hidden="true" /> Sin tarjeta para empezar. Precios en
                dólares; puedes pagar en pesos a la tasa del día.{' '}
                <Link to="/web#precios" className="font-semibold text-brand-blue hover:underline">
                  Ver qué incluye cada plan
                </Link>
              </p>
            </fieldset>
          )}
        </div>

        <Card>
          <form onSubmit={submit} className="space-y-4">
            <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">Crea la cuenta de tu empresa</p>
            <Field label="Nombre de la empresa">
              <Input required minLength={2} maxLength={120} value={form.company_name} onChange={set('company_name')} />
            </Field>
            <Field label="Tu nombre">
              <Input required minLength={2} maxLength={120} autoComplete="name" value={form.admin_name} onChange={set('admin_name')} />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Correo (será tu usuario)">
                <Input required type="email" autoComplete="email" value={form.email} onChange={set('email')} />
                {emailState !== 'idle' && (
                  <p
                    role="status"
                    data-testid="email-status"
                    className={`mt-1 text-xs font-medium ${
                      emailState === 'available'
                        ? 'text-emerald-700 dark:text-emerald-400'
                        : emailState === 'taken'
                          ? 'text-red-600 dark:text-red-400'
                          : 'text-gray-500'
                    }`}
                  >
                    {emailState === 'checking' && 'Revisando si está disponible…'}
                    {emailState === 'available' && '✓ Usuario disponible'}
                    {emailState === 'taken' && 'Ya existe una cuenta con ese correo. Inicia sesión o usa otro correo.'}
                  </p>
                )}
              </Field>
              <Field label="Teléfono / WhatsApp">
                <Input required type="tel" minLength={7} maxLength={30} autoComplete="tel" value={form.phone} onChange={set('phone')} />
              </Field>
            </div>
            <p className="rounded-2xl bg-brand-gray px-4 py-3 text-sm text-gray-700 dark:bg-gray-800 dark:text-gray-300">
              Al registrarte el sistema te genera una <strong>clave temporal</strong>. La verás una sola vez y la cambias por una tuya al
              entrar.
            </p>
            {/* Trampa para robots: oculto para las personas. */}
            <div className="hidden" aria-hidden="true">
              <label>
                Sitio web
                <input tabIndex={-1} autoComplete="off" value={form.website} onChange={set('website')} />
              </label>
            </div>
            <label className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
              <input type="checkbox" required checked={accept} onChange={(e) => setAccept(e.target.checked)} className="mt-0.5 h-4 w-4 rounded" />
              <span>
                Acepto los{' '}
                <Link to="/terminos" target="_blank" className="font-semibold text-brand-blue hover:underline">
                  términos del servicio y la política de privacidad
                </Link>
                .
              </span>
            </label>
            {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
            <Button type="submit" disabled={busy || !accept || emailState === 'taken'}>
              {busy ? 'Preparando tu empresa…' : `Empezar mis ${days} días gratis`}
            </Button>
            <p className="text-center text-sm text-gray-600 dark:text-gray-400">
              ¿Ya tienes cuenta?{' '}
              <Link to="/login" className="font-semibold text-brand-blue hover:underline">
                Inicia sesión
              </Link>
            </p>
          </form>
        </Card>
      </div>
    </div>
  )
}
