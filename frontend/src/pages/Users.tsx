import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { ManagedUser, Role } from '../lib/types'
import { useAuthStore } from '../lib/authStore'
import { Badge, Button, Card, Field, Input } from '../components/ui'

const ROLE_LABELS: Record<Role, string> = {
  admin: 'Administrador',
  oficina: 'Oficina',
  tecnico: 'Técnico',
}

function emptyForm() {
  return { name: '', email: '', password: '', role: 'oficina' as Role }
}

export function Users() {
  const currentUser = useAuthStore((s) => s.user)
  const queryClient = useQueryClient()
  const isAdmin = currentUser?.role === 'admin'

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(emptyForm())
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [resetPasswordValue, setResetPasswordValue] = useState('')

  const { data: users, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: async () => (await api.get<ManagedUser[]>('/users')).data,
    enabled: isAdmin,
  })

  const createUser = useMutation({
    mutationFn: async () => (await api.post('/users', form)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setShowForm(false)
      setForm(emptyForm())
      setError(null)
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? 'Error al crear el usuario'),
  })

  const updateUser = useMutation({
    mutationFn: async ({ id, data }: { id: number; data: Partial<ManagedUser> & { password?: string } }) =>
      (await api.put(`/users/${id}`, data)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setError(null)
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? 'Error al actualizar el usuario'),
  })

  if (!isAdmin) {
    return (
      <div className="py-4">
        <Card>
          <p className="text-sm text-gray-600 dark:text-gray-400">Solo un administrador puede gestionar usuarios.</p>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-4 py-4 md:space-y-6 md:py-8">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900 md:text-2xl dark:text-gray-100">Usuarios</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-full bg-brand-blue px-4 py-2 text-sm font-medium text-white"
        >
          {showForm ? 'Cancelar' : '+ Nuevo'}
        </button>
      </div>

      {showForm && (
        <Card className="md:max-w-2xl">
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault()
              createUser.mutate()
            }}
          >
            <div className="grid gap-3 md:grid-cols-2">
              <Field label="Nombre">
                <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </Field>
              <Field label="Correo">
                <Input
                  type="email"
                  required
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                />
              </Field>
              <Field label="Contraseña (mínimo 8 caracteres)">
                <Input
                  type="password"
                  required
                  minLength={8}
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                />
              </Field>
              <Field label="Rol">
                <select
                  className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
                  value={form.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value as Role })}
                >
                  <option value="oficina">Oficina</option>
                  <option value="tecnico">Técnico</option>
                  <option value="admin">Administrador</option>
                </select>
              </Field>
            </div>
            {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
            <Button type="submit" disabled={createUser.isPending}>
              {createUser.isPending ? 'Guardando…' : 'Crear usuario'}
            </Button>
          </form>
        </Card>
      )}

      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {users?.map((u) => {
          const isSelf = u.id === currentUser?.id
          const isEditing = editingId === u.id
          return (
            <Card key={u.id} className="space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900 dark:text-gray-100">
                    {u.name} {isSelf && <span className="text-xs text-gray-400">(tú)</span>}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">{u.email}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone={u.is_active ? 'green' : 'red'}>{u.is_active ? 'Activo' : 'Inactivo'}</Badge>
                  <Badge tone="blue">{ROLE_LABELS[u.role]}</Badge>
                </div>
              </div>

              {!isEditing && (
                <div className="flex flex-wrap gap-2">
                  <button
                    className="rounded-full bg-brand-gray px-3 py-1.5 text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                    onClick={() => {
                      setEditingId(u.id)
                      setResetPasswordValue('')
                    }}
                  >
                    Editar
                  </button>
                  {!isSelf && (
                    <button
                      className="rounded-full bg-brand-gray px-3 py-1.5 text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                      onClick={() => updateUser.mutate({ id: u.id, data: { is_active: !u.is_active } })}
                    >
                      {u.is_active ? 'Desactivar' : 'Activar'}
                    </button>
                  )}
                </div>
              )}

              {isEditing && (
                <div className="space-y-2 border-t border-gray-100 pt-2 dark:border-gray-800">
                  <Field label="Rol">
                    <select
                      className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 disabled:opacity-50 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
                      value={u.role}
                      disabled={isSelf}
                      onChange={(e) => updateUser.mutate({ id: u.id, data: { role: e.target.value as Role } })}
                    >
                      <option value="oficina">Oficina</option>
                      <option value="tecnico">Técnico</option>
                      <option value="admin">Administrador</option>
                    </select>
                  </Field>
                  {isSelf && (
                    <p className="text-xs text-gray-400">No puedes cambiar tu propio rol de administrador.</p>
                  )}
                  <Field label="Nueva contraseña (dejar en blanco para no cambiar)">
                    <Input
                      type="password"
                      minLength={8}
                      value={resetPasswordValue}
                      onChange={(e) => setResetPasswordValue(e.target.value)}
                    />
                  </Field>
                  {editingId === u.id && updateUser.isError && (
                    <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
                  )}
                  <div className="flex gap-2">
                    <Button
                      variant="secondary"
                      className="w-auto px-4"
                      onClick={() => {
                        if (resetPasswordValue) {
                          updateUser.mutate({ id: u.id, data: { password: resetPasswordValue } })
                        }
                        setEditingId(null)
                      }}
                    >
                      Guardar contraseña
                    </Button>
                    <Button variant="ghost" className="w-auto px-4" onClick={() => setEditingId(null)}>
                      Listo
                    </Button>
                  </div>
                </div>
              )}
            </Card>
          )
        })}
        {users?.length === 0 && <p className="text-sm text-gray-500">Aún no hay usuarios.</p>}
      </div>
    </div>
  )
}
