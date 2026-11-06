import { isAxiosError } from 'axios'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { LOGOUT_NOTICE_KEY, api } from '../lib/api'
import { safeStorage } from '../lib/safeStorage'
import { useAuthStore } from '../lib/authStore'
import { Button, Card, Field, Input } from '../components/ui'
import { TutorialesLogin } from '../components/TutorialesLogin'
import type { CurrentUser } from '../lib/types'

export function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  // Se lee una sola vez al llegar y se borra: si recarga la página ya no aparece.
  const [notice] = useState(() => safeStorage.get(LOGOUT_NOTICE_KEY))
  useEffect(() => {
    safeStorage.remove(LOGOUT_NOTICE_KEY)
  }, [])
  const setSession = useAuthStore((s) => s.setSession)
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const form = new URLSearchParams()
      form.set('username', email)
      form.set('password', password)
      const { data } = await api.post('/auth/login', form, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      const token = data.access_token as string
      const { data: user } = await api.get<CurrentUser>('/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      })
      setSession(token, user)
      navigate('/')
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 429) {
        setError('Demasiados intentos. Espera un minuto e intenta de nuevo.')
      } else if (isAxiosError(err) && err.response?.status === 401) {
        setError('Correo o contraseña incorrectos')
      } else if (isAxiosError(err) && err.response?.status === 403 && typeof err.response.data?.detail === 'string') {
        // Empresa suspendida, prueba terminada o mensualidad vencida: el servidor dice cuál.
        setError(err.response.data.detail)
      } else {
        setError('Ocurrió un error al iniciar sesión. Intenta de nuevo.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-brand-bg px-5 dark:bg-gray-950">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-5 flex h-24 w-24 items-center justify-center rounded-[1.75rem] bg-gradient-to-br from-brand-blue to-blue-800 text-5xl font-extrabold text-white shadow-lg">
            M
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-gray-900 dark:text-gray-100">Multitec ERP</h1>
          <p className="text-sm text-gray-500">Seguridad electrónica</p>
        </div>
        {notice && !error && (
          <p
            role="status"
            className={`mb-4 rounded-2xl px-4 py-3 text-center text-sm ring-1 ${
              notice === 'expired'
                ? 'bg-amber-50 text-amber-900 ring-amber-200 dark:bg-amber-950/40 dark:text-amber-200 dark:ring-amber-900'
                : 'bg-emerald-50 text-emerald-900 ring-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-200 dark:ring-emerald-900'
            }`}
          >
            {notice === 'expired'
              ? 'Tu sesión terminó. Vuelve a entrar para seguir trabajando.'
              : 'Cerraste sesión. Vuelve a entrar cuando quieras.'}
          </p>
        )}
        <Card>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Field label="Correo">
              <Input
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </Field>
            <Field label="Contraseña">
              <div className="relative">
                <Input
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  // Sin esto el teclado del celular pone mayúsculas, autocorrige o agrega espacios.
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                  required
                  className="pr-20"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                  aria-pressed={showPassword}
                  className="absolute inset-y-0 right-0 flex items-center px-4 text-sm font-medium text-brand-blue"
                >
                  {showPassword ? 'Ocultar' : 'Mostrar'}
                </button>
              </div>
            </Field>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <Button type="submit" disabled={loading}>
              {loading ? 'Ingresando…' : 'Ingresar'}
            </Button>
          </form>
        </Card>
        <p className="mt-4 text-center text-sm text-gray-600 dark:text-gray-400">
          ¿Tu empresa aún no usa Multitec?{' '}
          <Link to="/registro" className="font-semibold text-brand-blue hover:underline">
            Pruébalo gratis
          </Link>
          {' · '}
          <Link to="/web" className="font-semibold text-brand-blue hover:underline">
            Conoce Multitec
          </Link>
        </p>
        <TutorialesLogin />
      </div>
    </div>
  )
}
