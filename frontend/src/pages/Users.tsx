import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, apiErrorMessage } from '../lib/api'
import type { ManagedUser, Role, Workload } from '../lib/types'
import { useAuthStore } from '../lib/authStore'
import { timeAgo } from '../lib/userAgent'
import { SessionList } from '../components/SessionList'
import { Badge, Button, Card, Field, Input } from '../components/ui'

const ROLE_LABELS: Record<Role, string> = {
  admin: 'Administrador',
  oficina: 'Oficina',
  tecnico: 'Técnico',
}

function emptyForm() {
  return { name: '', email: '', password: '', role: 'oficina' as Role, phone: '', zone: '', skills: '', vehicle: '' }
}

type Profile = Pick<ManagedUser, 'phone' | 'zone' | 'skills' | 'vehicle'>

/** Los campos de la ficha vacíos viajan como null para poder borrarlos. */
function blankToNull(value: string): string | null {
  return value.trim() ? value.trim() : null
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
  const [editName, setEditName] = useState('')
  const [editEmail, setEditEmail] = useState('')
  const [editProfile, setEditProfile] = useState({ phone: '', zone: '', skills: '', vehicle: '' })
  const [sessionsFor, setSessionsFor] = useState<number | null>(null)
  // La clave temporal se muestra una sola vez; el servidor no la guarda en claro.
  const [temporary, setTemporary] = useState<{ id: number; value: string } | null>(null)

  const { data: users, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: async () => (await api.get<ManagedUser[]>('/users')).data,
    enabled: isAdmin,
  })

  // Cuánto trabajo tiene cada uno hoy, para repartir visitas sin sobrecargar a nadie.
  const { data: workload } = useQuery({
    queryKey: ['team-workload'],
    queryFn: async () => (await api.get<Workload[]>('/users/workload')).data,
    enabled: isAdmin,
  })
  const workloadById = new Map(workload?.map((w) => [w.user_id, w]))

  const resetPassword = useMutation({
    mutationFn: async (id: number) =>
      (await api.post<{ temporary_password: string }>(`/users/${id}/reset-password`)).data.temporary_password,
    onSuccess: (value, id) => setTemporary({ id, value }),
    onError: (err: unknown) => setError(apiErrorMessage(err, 'No se pudo restablecer la contraseña')),
  })

  const createUser = useMutation({
    mutationFn: async () =>
      (
        await api.post('/users', {
          ...form,
          phone: blankToNull(form.phone),
          zone: blankToNull(form.zone),
          skills: blankToNull(form.skills),
          vehicle: blankToNull(form.vehicle),
        })
      ).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setShowForm(false)
      setForm(emptyForm())
      setError(null)
    },
    onError: (err: any) => setError(apiErrorMessage(err, 'Error al crear el usuario')),
  })

  const updateUser = useMutation({
    mutationFn: async ({ id, data }: { id: number; data: Partial<Profile> & Partial<ManagedUser> & { password?: string } }) =>
      (await api.put(`/users/${id}`, data)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setError(null)
    },
    onError: (err: any) => setError(apiErrorMessage(err, 'Error al actualizar el usuario')),
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
              <Field label="Contraseña (mínimo 10 caracteres)">
                <Input
                  type="password"
                  required
                  minLength={10}
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
              <Field label="Teléfono (opcional)">
                <Input type="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
              </Field>
              <Field label="Zona que cubre (opcional)">
                <Input value={form.zone} onChange={(e) => setForm({ ...form, zone: e.target.value })} />
              </Field>
              <Field label="Especialidades (opcional)">
                <Input
                  placeholder="CCTV, redes, alarmas"
                  value={form.skills}
                  onChange={(e) => setForm({ ...form, skills: e.target.value })}
                />
              </Field>
              <Field label="Vehículo o placa (opcional)">
                <Input value={form.vehicle} onChange={(e) => setForm({ ...form, vehicle: e.target.value })} />
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

              {(u.phone || u.zone || u.skills || u.vehicle) && (
                <ul className="space-y-0.5 text-xs text-gray-600 dark:text-gray-400">
                  {u.phone && <li>Tel. {u.phone}</li>}
                  {u.zone && <li>Zona: {u.zone}</li>}
                  {u.skills && <li>Especialidades: {u.skills}</li>}
                  {u.vehicle && <li>Vehículo: {u.vehicle}</li>}
                </ul>
              )}
              <p className="text-xs text-gray-400">Último acceso: {timeAgo(u.last_login_at)}</p>
              {u.role === 'tecnico' && workloadById.get(u.id) && (
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Hoy: {workloadById.get(u.id)!.visits_total} {workloadById.get(u.id)!.visits_total === 1 ? 'visita' : 'visitas'}
                  {' · '}
                  {workloadById.get(u.id)!.open_tickets} tickets abiertos
                </p>
              )}

              {temporary?.id === u.id && (
                <div
                  role="status"
                  className="space-y-1 rounded-xl bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-200"
                >
                  <p>
                    Clave temporal de {u.name}: <strong className="select-all font-mono text-base">{temporary.value}</strong>
                  </p>
                  <p className="text-xs">
                    Anótala o envíasela ahora: no se vuelve a mostrar. Tendrá que cambiarla al entrar, y sus sesiones
                    abiertas se cerraron.
                  </p>
                  <button className="text-xs underline" onClick={() => setTemporary(null)}>
                    Ya la anoté
                  </button>
                </div>
              )}

              {!isEditing && (
                <div className="flex flex-wrap gap-2">
                  <button
                    className="rounded-full bg-brand-gray px-3 py-1.5 text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                    onClick={() => {
                      setEditingId(u.id)
                      setResetPasswordValue('')
                      setEditName(u.name)
                      setEditEmail(u.email)
                      setEditProfile({ phone: u.phone ?? '', zone: u.zone ?? '', skills: u.skills ?? '', vehicle: u.vehicle ?? '' })
                      setError(null)
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
                  {!isSelf && (
                    <button
                      className="rounded-full bg-brand-gray px-3 py-1.5 text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                      disabled={resetPassword.isPending}
                      onClick={() => {
                        if (
                          window.confirm(
                            `¿Restablecer la contraseña de ${u.name}? Se genera una clave temporal y se cierran sus sesiones abiertas.`,
                          )
                        )
                          resetPassword.mutate(u.id)
                      }}
                    >
                      Restablecer clave
                    </button>
                  )}
                  <button
                    className="rounded-full bg-brand-gray px-3 py-1.5 text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                    onClick={() => setSessionsFor(sessionsFor === u.id ? null : u.id)}
                  >
                    {sessionsFor === u.id ? 'Ocultar sesiones' : 'Sesiones'}
                  </button>
                </div>
              )}

              {sessionsFor === u.id && !isEditing && (
                <div className="border-t border-gray-100 pt-2 dark:border-gray-800">
                  <SessionList
                    listPath={`/users/${u.id}/sessions`}
                    closeOne={(sessionId) => api.delete(`/users/${u.id}/sessions/${sessionId}`)}
                    closeAll={() => api.post(`/users/${u.id}/sessions/revoke-all`)}
                    closeAllLabel={`Cerrar todas las sesiones de ${u.name}`}
                  />
                </div>
              )}

              {isEditing && (
                <div className="space-y-2 border-t border-gray-100 pt-2 dark:border-gray-800">
                  <Field label="Nombre">
                    <Input value={editName} onChange={(e) => setEditName(e.target.value)} />
                  </Field>
                  <Field label="Correo (con el que entra)">
                    <Input
                      type="email"
                      autoCapitalize="none"
                      value={editEmail}
                      onChange={(e) => setEditEmail(e.target.value)}
                    />
                  </Field>
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
                  <div className="grid gap-2 sm:grid-cols-2">
                    <Field label="Teléfono">
                      <Input
                        type="tel"
                        value={editProfile.phone}
                        onChange={(e) => setEditProfile({ ...editProfile, phone: e.target.value })}
                      />
                    </Field>
                    <Field label="Zona que cubre">
                      <Input
                        value={editProfile.zone}
                        onChange={(e) => setEditProfile({ ...editProfile, zone: e.target.value })}
                      />
                    </Field>
                    <Field label="Especialidades">
                      <Input
                        placeholder="CCTV, redes, alarmas"
                        value={editProfile.skills}
                        onChange={(e) => setEditProfile({ ...editProfile, skills: e.target.value })}
                      />
                    </Field>
                    <Field label="Vehículo o placa">
                      <Input
                        value={editProfile.vehicle}
                        onChange={(e) => setEditProfile({ ...editProfile, vehicle: e.target.value })}
                      />
                    </Field>
                  </div>
                  <Field label="Nueva contraseña (dejar en blanco para no cambiar)">
                    <Input
                      type="password"
                      minLength={10}
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
                      className="!w-auto px-4"
                      onClick={() => {
                        const data: Partial<Profile> & Partial<ManagedUser> & { password?: string } = {}
                        if (editName.trim() && editName !== u.name) data.name = editName.trim()
                        if (editEmail.trim() && editEmail.trim().toLowerCase() !== u.email) data.email = editEmail.trim()
                        for (const field of ['phone', 'zone', 'skills', 'vehicle'] as const) {
                          const next = blankToNull(editProfile[field])
                          if (next !== (u[field] ?? null)) data[field] = next
                        }
                        if (resetPasswordValue) data.password = resetPasswordValue
                        if (Object.keys(data).length === 0) {
                          setEditingId(null)
                          return
                        }
                        // Se cierra solo si salió bien: un error (por ejemplo, correo ya usado) debe verse aquí.
                        updateUser.mutate({ id: u.id, data }, { onSuccess: () => setEditingId(null) })
                      }}
                    >
                      Guardar cambios
                    </Button>
                    <Button variant="ghost" className="!w-auto px-4" onClick={() => setEditingId(null)}>
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
