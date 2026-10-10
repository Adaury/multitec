import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../lib/api'
import { useAuthStore } from '../lib/authStore'
import { assistantCallName } from '../lib/assistantName'
import type { CurrentUser, Role } from '../lib/types'
import { Badge, Button, Card, Field, Input } from '../components/ui'

const ROLE_LABELS: Record<Role, string> = {
  admin: 'Administrador',
  oficina: 'Oficina',
  tecnico: 'Técnico',
}

export function Profile() {
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)
  const setTokens = useAuthStore((s) => s.setTokens)

  const [name, setName] = useState(user?.name ?? '')
  const [alias, setAlias] = useState(user?.assistant_alias ?? '')
  // Lo que usa el asistente si dejas vacío el campo (se actualiza mientras escribes tu nombre).
  const defaultCall = assistantCallName({ name, assistant_alias: null })
  const [nameMsg, setNameMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [pwMsg, setPwMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const saveName = useMutation({
    mutationFn: async () => (await api.put<CurrentUser>('/auth/me', { name, assistant_alias: alias })).data,
    onSuccess: (data) => {
      setUser(data)
      setName(data.name)
      setAlias(data.assistant_alias ?? '')
      setNameMsg({ ok: true, text: 'Perfil actualizado' })
    },
    onError: (err: any) =>
      setNameMsg({ ok: false, text: err?.response?.data?.detail?.[0]?.msg ?? err?.response?.data?.detail ?? 'Error al guardar' }),
  })

  const changePassword = useMutation({
    mutationFn: async () =>
      (await api.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword })).data,
    onSuccess: (data) => {
      // Las demás sesiones se cierran; esta sigue activa con el par de tokens nuevo.
      setTokens(data.access_token, data.refresh_token)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setPwMsg({ ok: true, text: 'Contraseña actualizada. Se cerraron tus otras sesiones.' })
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail
      setPwMsg({ ok: false, text: typeof detail === 'string' ? detail : detail?.[0]?.msg ?? 'Error al cambiar la contraseña' })
    },
  })

  const mismatch = confirmPassword.length > 0 && newPassword !== confirmPassword

  return (
    <div className="space-y-4 py-4 md:space-y-6 md:py-8">
      <h1 className="text-xl font-semibold text-gray-900 md:text-2xl dark:text-gray-100">Mi perfil</h1>

      <Card className="space-y-3 md:max-w-xl">
        <div className="flex items-center justify-between gap-2">
          <p className="truncate text-sm text-gray-500 dark:text-gray-400">{user?.email}</p>
          {user && <Badge tone="blue">{ROLE_LABELS[user.role]}</Badge>}
        </div>
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault()
            setNameMsg(null)
            saveName.mutate()
          }}
        >
          <Field label="Nombre">
            <Input required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field label="Cómo te llama el asistente de IA">
            <Input
              maxLength={60}
              placeholder={defaultCall}
              value={alias}
              onChange={(e) => setAlias(e.target.value)}
            />
          </Field>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Ej. "Ing. Pérez". El asistente te saluda así al abrir un levantamiento. Si lo dejas vacío usa "
            {defaultCall}".
          </p>
          {nameMsg && (
            <p className={`text-sm ${nameMsg.ok ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
              {nameMsg.text}
            </p>
          )}
          <Button
            type="submit"
            disabled={
              saveName.isPending ||
              !name.trim() ||
              (name.trim() === user?.name && alias.trim() === (user?.assistant_alias ?? ''))
            }
          >
            {saveName.isPending ? 'Guardando…' : 'Guardar perfil'}
          </Button>
        </form>
      </Card>

      <Card className="md:max-w-xl">
        <h2 className="mb-3 text-base font-semibold text-gray-900 dark:text-gray-100">Cambiar contraseña</h2>
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault()
            if (mismatch) return
            setPwMsg(null)
            changePassword.mutate()
          }}
        >
          <Field label="Contraseña actual">
            <Input
              type="password"
              required
              autoComplete="current-password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
          </Field>
          <Field label="Nueva contraseña (mínimo 8 caracteres)">
            <Input
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
          </Field>
          <Field label="Confirmar nueva contraseña">
            <Input
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </Field>
          {mismatch && <p className="text-sm text-red-600 dark:text-red-400">Las contraseñas no coinciden</p>}
          {pwMsg && (
            <p className={`text-sm ${pwMsg.ok ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
              {pwMsg.text}
            </p>
          )}
          <Button type="submit" disabled={changePassword.isPending || mismatch}>
            {changePassword.isPending ? 'Guardando…' : 'Cambiar contraseña'}
          </Button>
        </form>
      </Card>
    </div>
  )
}
