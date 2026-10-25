import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Cpu, Plus } from 'lucide-react'
import { api, apiErrorMessage } from '../lib/api'
import { useAuthStore } from '../lib/authStore'
import { ASSET_KIND_LABELS, type AssetKind, type ClientAsset, type Project } from '../lib/types'
import { Badge, Button, Card, Field, Input, Textarea } from './ui'

const KINDS = Object.keys(ASSET_KIND_LABELS) as AssetKind[]

interface Form {
  kind: AssetKind
  name: string
  brand: string
  model: string
  serial: string
  mac: string
  ip_address: string
  location: string
  installed_on: string
  warranty_until: string
  project_id: string
  notes: string
}

const EMPTY: Form = {
  kind: 'camara',
  name: '',
  brand: '',
  model: '',
  serial: '',
  mac: '',
  ip_address: '',
  location: '',
  installed_on: '',
  warranty_until: '',
  project_id: '',
  notes: '',
}

function toForm(a: ClientAsset): Form {
  return {
    kind: a.kind,
    name: a.name,
    brand: a.brand ?? '',
    model: a.model ?? '',
    serial: a.serial ?? '',
    mac: a.mac ?? '',
    ip_address: a.ip_address ?? '',
    location: a.location ?? '',
    installed_on: a.installed_on ?? '',
    warranty_until: a.warranty_until ?? '',
    project_id: a.project_id != null ? String(a.project_id) : '',
    notes: a.notes ?? '',
  }
}

/** Lo que se manda al servidor: los campos vacíos viajan como null para poder borrarlos. */
function toPayload(f: Form) {
  const text = (v: string) => (v.trim() ? v.trim() : null)
  return {
    kind: f.kind,
    name: f.name.trim(),
    brand: text(f.brand),
    model: text(f.model),
    serial: text(f.serial),
    mac: text(f.mac),
    ip_address: text(f.ip_address),
    location: text(f.location),
    installed_on: f.installed_on || null,
    warranty_until: f.warranty_until || null,
    project_id: f.project_id ? Number(f.project_id) : null,
    notes: text(f.notes),
  }
}

function WarrantyBadge({ asset }: { asset: ClientAsset }) {
  if (!asset.warranty_until || !asset.warranty_status) return null
  const days = Math.round((new Date(`${asset.warranty_until}T12:00:00`).getTime() - Date.now()) / 86_400_000)
  if (asset.warranty_status === 'vencida') return <Badge tone="red">Garantía vencida</Badge>
  if (asset.warranty_status === 'por_vencer')
    return <Badge tone="amber">Garantía vence en {Math.max(days, 0)} días</Badge>
  return <Badge tone="green">En garantía hasta {asset.warranty_until}</Badge>
}

/** Equipos instalados en un cliente: serial, MAC, ubicación y garantía. Al llegar una falla se sabe qué equipo es. */
export function ClientAssets({ clientId, projects }: { clientId: number; projects: Project[] }) {
  const queryClient = useQueryClient()
  const role = useAuthStore((s) => s.user?.role)
  const canDelete = role === 'admin' || role === 'oficina'
  const [editing, setEditing] = useState<number | 'new' | null>(null)
  const [form, setForm] = useState<Form>(EMPTY)
  const [error, setError] = useState<string | null>(null)

  const key = ['client-assets', clientId]
  const { data: assets } = useQuery({
    queryKey: key,
    queryFn: async () => (await api.get<ClientAsset[]>(`/clients/${clientId}/assets`)).data,
  })

  const save = useMutation({
    mutationFn: async () =>
      editing === 'new'
        ? (await api.post(`/clients/${clientId}/assets`, toPayload(form))).data
        : (await api.put(`/client-assets/${editing}`, toPayload(form))).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: key })
      setEditing(null)
      setError(null)
    },
    onError: (err: unknown) => setError(apiErrorMessage(err, 'No se pudo guardar el equipo')),
  })

  const remove = useMutation({
    mutationFn: async (id: number) => api.delete(`/client-assets/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: key }),
  })

  const set = (patch: Partial<Form>) => setForm((f) => ({ ...f, ...patch }))

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
          <Cpu className="h-5 w-5 text-brand-blue" aria-hidden="true" />
          Equipos instalados {assets && assets.length > 0 && <span className="text-sm text-gray-400">({assets.length})</span>}
        </h2>
        {editing === null && (
          <button
            onClick={() => {
              setForm(EMPTY)
              setError(null)
              setEditing('new')
            }}
            className="flex items-center gap-1 rounded-full bg-brand-blue px-3 py-1.5 text-sm font-medium text-white"
          >
            <Plus className="h-4 w-4" aria-hidden="true" /> Agregar equipo
          </button>
        )}
      </div>

      {editing !== null && (
        <Card>
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault()
              save.mutate()
            }}
          >
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Tipo">
                <select
                  className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
                  value={form.kind}
                  onChange={(e) => set({ kind: e.target.value as AssetKind })}
                >
                  {KINDS.map((k) => (
                    <option key={k} value={k}>
                      {ASSET_KIND_LABELS[k]}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Nombre o descripción">
                <Input required value={form.name} onChange={(e) => set({ name: e.target.value })} placeholder="Cámara domo 4MP" />
              </Field>
              <Field label="Marca">
                <Input value={form.brand} onChange={(e) => set({ brand: e.target.value })} />
              </Field>
              <Field label="Modelo">
                <Input value={form.model} onChange={(e) => set({ model: e.target.value })} />
              </Field>
              <Field label="Serial">
                <Input value={form.serial} onChange={(e) => set({ serial: e.target.value })} autoCapitalize="characters" />
              </Field>
              <Field label="MAC">
                <Input
                  value={form.mac}
                  onChange={(e) => set({ mac: e.target.value })}
                  placeholder="AA:BB:CC:DD:EE:FF"
                  autoCapitalize="characters"
                />
              </Field>
              <Field label="Dirección IP">
                <Input value={form.ip_address} onChange={(e) => set({ ip_address: e.target.value })} inputMode="decimal" />
              </Field>
              <Field label="Ubicación en el sitio">
                <Input value={form.location} onChange={(e) => set({ location: e.target.value })} placeholder="Entrada principal" />
              </Field>
              <Field label="Fecha de instalación">
                <Input type="date" value={form.installed_on} onChange={(e) => set({ installed_on: e.target.value })} />
              </Field>
              <Field label="Garantía hasta">
                <Input type="date" value={form.warranty_until} onChange={(e) => set({ warranty_until: e.target.value })} />
              </Field>
              <Field label="Proyecto con el que se instaló">
                <select
                  className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
                  value={form.project_id}
                  onChange={(e) => set({ project_id: e.target.value })}
                >
                  <option value="">Ninguno</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.code}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
            <Field label="Notas">
              <Textarea value={form.notes} onChange={(e) => set({ notes: e.target.value })} />
            </Field>
            {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
            <div className="flex gap-2">
              <Button className="!w-auto flex-1" type="submit" disabled={save.isPending || !form.name.trim()}>
                {save.isPending ? 'Guardando…' : 'Guardar equipo'}
              </Button>
              <Button className="!w-auto flex-1" type="button" variant="secondary" onClick={() => setEditing(null)}>
                Cancelar
              </Button>
            </div>
          </form>
        </Card>
      )}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {assets?.map((a) => (
          <Card key={a.id} className="space-y-1.5">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="font-medium text-gray-900 dark:text-gray-100">{a.name}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {ASSET_KIND_LABELS[a.kind] ?? a.kind}
                  {a.brand || a.model ? ` · ${[a.brand, a.model].filter(Boolean).join(' ')}` : ''}
                </p>
              </div>
              <WarrantyBadge asset={a} />
            </div>
            <dl className="space-y-0.5 text-xs text-gray-600 dark:text-gray-400">
              {a.location && <div>Ubicación: {a.location}</div>}
              {a.serial && <div>Serial: <span className="select-all font-mono">{a.serial}</span></div>}
              {a.mac && <div>MAC: <span className="select-all font-mono">{a.mac}</span></div>}
              {a.ip_address && <div>IP: <span className="select-all font-mono">{a.ip_address}</span></div>}
              {a.installed_on && <div>Instalado: {a.installed_on}</div>}
              {a.notes && <div>{a.notes}</div>}
            </dl>
            <div className="flex gap-2 pt-1">
              <button
                className="rounded-full bg-brand-gray px-3 py-1.5 text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                onClick={() => {
                  setForm(toForm(a))
                  setError(null)
                  setEditing(a.id)
                }}
              >
                Editar
              </button>
              {canDelete && (
                <button
                  className="rounded-full bg-brand-gray px-3 py-1.5 text-xs font-medium text-red-600 dark:bg-gray-800 dark:text-red-400"
                  onClick={() => {
                    if (window.confirm(`¿Quitar «${a.name}» de los equipos de este cliente?`)) remove.mutate(a.id)
                  }}
                >
                  Quitar
                </button>
              )}
            </div>
          </Card>
        ))}
        {assets?.length === 0 && editing === null && (
          <p className="text-sm text-gray-500">
            Aún no hay equipos registrados. Anota aquí cada cámara, grabador o panel que instales, con su serial y MAC.
          </p>
        )}
      </div>
    </div>
  )
}
