import { isAxiosError } from 'axios'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuthStore } from '../lib/authStore'
import { Button, Card, Field, Input } from '../components/ui'
import type { CurrentUser } from '../lib/types'

export function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
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
      const refreshToken = data.refresh_token as string
      const { data: user } = await api.get<CurrentUser>('/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      })
      setSession(token, refreshToken, user)
      navigate('/')
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 429) {
        setError('Demasiados intentos. Espera un minuto e intenta de nuevo.')
      } else if (isAxiosError(err) && err.response?.status === 401) {
        setError('Correo o contraseña incorrectos')
      } else {
        setError('Ocurrió un error al iniciar sesión. Intenta de nuevo.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-brand-bg px-5 dark:bg-gray-950">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-blue text-2xl font-bold text-white">
            M
          </div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">Multitec ERP</h1>
          <p className="text-sm text-gray-500">Seguridad electrónica</p>
        </div>
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
              <Input
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </Field>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <Button type="submit" disabled={loading}>
              {loading ? 'Ingresando…' : 'Ingresar'}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  )
}
