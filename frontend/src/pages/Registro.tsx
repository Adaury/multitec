import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { CalendarCheck2, Camera, CheckCircle2, ClipboardList, Users } from 'lucide-react'
import { api, apiErrorMessage } from '../lib/api'
import { useAuthStore } from '../lib/authStore'
import { Button, Card, Field, Input } from '../components/ui'
import type { CurrentUser } from '../lib/types'

interface SignupInfo {
  enabled: boolean
  trial_days: number
  setup_fee: number
  monthly_fee: number
  contact_phone: string
}

const money = (n: number) => `RD$${n.toLocaleString('es-DO', { maximumFractionDigits: 0 })}`

const FEATURES = [
  { icon: ClipboardList, text: 'Levantamientos con fotos y voz desde el celular' },
  { icon: Camera, text: 'Cotizaciones con IA y catálogo de cámaras, alarmas y cercos' },
  { icon: Users, text: 'Técnicos, visitas y tickets en un solo lugar' },
  { icon: CalendarCheck2, text: 'Facturas con NCF, compras 606 y reportes' },
]

/** Página pública: una empresa se registra sola y empieza su prueba gratis. */
export function Registro() {
  const navigate = useNavigate()
  const setSession = useAuthStore((s) => s.setSession)
  const { data: info } = useQuery({
    queryKey: ['signup-info'],
    queryFn: async () => (await api.get<SignupInfo>('/signup/info')).data,
  })
  const [form, setForm] = useState({ company_name: '', admin_name: '', email: '', phone: '', password: '', website: '' })
  const [accept, setAccept] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: e.target.value })

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await api.post('/signup', { ...form, accept_terms: accept }, { timeout: 120_000 })
      // Entra directo con la clave que acaba de elegir.
      const login = new URLSearchParams({ username: form.email, password: form.password })
      const { data } = await api.post('/auth/login', login, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })
      const { data: user } = await api.get<CurrentUser>('/auth/me', { headers: { Authorization: `Bearer ${data.access_token}` } })
      setSession(data.access_token, user)
      navigate('/?bienvenida=1')
    } catch (err) {
      setError(apiErrorMessage(err, 'No se pudo completar el registro. Intenta de nuevo.'))
    } finally {
      setBusy(false)
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

  return (
    <div className="min-h-dvh bg-brand-bg px-5 py-8 dark:bg-gray-950">
      <div className="mx-auto grid w-full max-w-5xl gap-6 lg:grid-cols-2 lg:items-start">
        <div className="space-y-5 lg:sticky lg:top-8">
          <div className="flex items-center gap-3">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-blue to-blue-800 text-3xl font-extrabold text-white shadow-lg">
              M
            </div>
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
          {info && (
            <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-black/5 dark:bg-gray-900 dark:ring-white/10">
              <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">Después de la prueba</p>
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div>
                  <p className="text-2xl font-extrabold text-gray-900 dark:text-gray-100">{money(info.setup_fee)}</p>
                  <p className="text-xs text-gray-500">una sola vez: instalación y explicación</p>
                </div>
                <div>
                  <p className="text-2xl font-extrabold text-gray-900 dark:text-gray-100">
                    {money(info.monthly_fee)}
                    <span className="text-sm font-medium text-gray-500">/mes</span>
                  </p>
                  <p className="text-xs text-gray-500">soporte y uso de la plataforma</p>
                </div>
              </div>
              <p className="mt-3 flex items-center gap-1.5 text-xs text-gray-500">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-hidden="true" /> Sin tarjeta para empezar.
              </p>
            </div>
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
              <Field label="Correo">
                <Input required type="email" autoComplete="email" value={form.email} onChange={set('email')} />
              </Field>
              <Field label="Teléfono / WhatsApp">
                <Input required type="tel" minLength={7} maxLength={30} autoComplete="tel" value={form.phone} onChange={set('phone')} />
              </Field>
            </div>
            <Field label="Contraseña (mínimo 10 caracteres)">
              <div className="relative">
                <Input
                  required
                  minLength={10}
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                  className="pr-20"
                  value={form.password}
                  onChange={set('password')}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                  className="absolute inset-y-0 right-0 flex items-center px-4 text-sm font-medium text-brand-blue"
                >
                  {showPassword ? 'Ocultar' : 'Mostrar'}
                </button>
              </div>
            </Field>
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
            <Button type="submit" disabled={busy || !accept}>
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
