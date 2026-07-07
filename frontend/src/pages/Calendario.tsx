import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import type { Project, Technician, Visit, VisitStatus } from '../lib/types'
import { VISIT_STATUS_LABELS } from '../lib/types'
import { Badge, Button, Card, Field, Input, Textarea } from '../components/ui'

function todayISO() {
  return new Date().toISOString().slice(0, 10)
}

function addDays(iso: string, days: number) {
  const d = new Date(iso + 'T00:00:00')
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

const STATUS_TONE: Record<VisitStatus, 'blue' | 'green' | 'red'> = {
  programada: 'blue',
  completada: 'green',
  cancelada: 'red',
}

function emptyForm(date: string) {
  return { project_id: '', technician_id: '', scheduled_date: date, scheduled_time: '', notes: '' }
}

export function Calendario() {
  const queryClient = useQueryClient()
  const [selectedDate, setSelectedDate] = useState(todayISO())
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(emptyForm(todayISO()))
  const [error, setError] = useState<string | null>(null)

  const { data: visits, isLoading } = useQuery({
    queryKey: ['visits', selectedDate],
    queryFn: async () =>
      (await api.get<Visit[]>('/visits', { params: { start: selectedDate, end: selectedDate } })).data,
  })

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => (await api.get<Project[]>('/projects')).data,
    enabled: showForm,
  })

  const { data: technicians } = useQuery({
    queryKey: ['technicians'],
    queryFn: async () => (await api.get<Technician[]>('/users/technicians')).data,
    enabled: showForm,
  })

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['visits'] })
  }

  const createVisit = useMutation({
    mutationFn: async () =>
      (
        await api.post('/visits', {
          project_id: Number(form.project_id),
          technician_id: form.technician_id ? Number(form.technician_id) : null,
          scheduled_date: form.scheduled_date,
          scheduled_time: form.scheduled_time || null,
          notes: form.notes || null,
        })
      ).data,
    onSuccess: () => {
      invalidate()
      setShowForm(false)
      setForm(emptyForm(selectedDate))
      setError(null)
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? 'Error al agendar la visita'),
  })

  const updateStatus = useMutation({
    mutationFn: async ({ id, status }: { id: number; status: VisitStatus }) =>
      (await api.put(`/visits/${id}`, { status })).data,
    onSuccess: invalidate,
  })

  return (
    <div className="space-y-4 py-4 md:space-y-6 md:py-8">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900 md:text-2xl dark:text-gray-100">Calendario de visitas</h1>
        <button
          onClick={() => {
            setForm(emptyForm(selectedDate))
            setShowForm((v) => !v)
          }}
          className="rounded-full bg-brand-blue px-4 py-2 text-sm font-medium text-white"
        >
          {showForm ? 'Cancelar' : '+ Nueva'}
        </button>
      </div>

      <div className="flex items-center gap-2 md:max-w-sm">
        <button
          onClick={() => setSelectedDate(addDays(selectedDate, -1))}
          className="rounded-full bg-brand-gray px-3 py-2 text-sm text-gray-600 dark:bg-gray-800 dark:text-gray-300"
        >
          ←
        </button>
        <input
          type="date"
          value={selectedDate}
          onChange={(e) => setSelectedDate(e.target.value)}
          className="flex-1 rounded-xl border border-gray-200 bg-white px-4 py-2 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
        />
        <button
          onClick={() => setSelectedDate(addDays(selectedDate, 1))}
          className="rounded-full bg-brand-gray px-3 py-2 text-sm text-gray-600 dark:bg-gray-800 dark:text-gray-300"
        >
          →
        </button>
      </div>

      {showForm && (
        <Card className="md:max-w-2xl">
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault()
              if (!form.project_id) return
              createVisit.mutate()
            }}
          >
            <div className="grid gap-3 md:grid-cols-2">
              <Field label="Proyecto">
                <select
                  required
                  className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
                  value={form.project_id}
                  onChange={(e) => setForm({ ...form, project_id: e.target.value })}
                >
                  <option value="">Selecciona un proyecto…</option>
                  {projects?.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.code}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Técnico (opcional)">
                <select
                  className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
                  value={form.technician_id}
                  onChange={(e) => setForm({ ...form, technician_id: e.target.value })}
                >
                  <option value="">Sin asignar</option>
                  {technicians?.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Fecha">
                <Input
                  type="date"
                  required
                  value={form.scheduled_date}
                  onChange={(e) => setForm({ ...form, scheduled_date: e.target.value })}
                />
              </Field>
              <Field label="Hora (opcional)">
                <Input
                  type="time"
                  value={form.scheduled_time}
                  onChange={(e) => setForm({ ...form, scheduled_time: e.target.value })}
                />
              </Field>
            </div>
            <Field label="Notas">
              <Textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            </Field>
            {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
            <Button type="submit" disabled={createVisit.isPending || !form.project_id}>
              {createVisit.isPending ? 'Guardando…' : 'Agendar visita'}
            </Button>
          </form>
        </Card>
      )}

      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {visits?.map((visit) => (
          <VisitCard
            key={visit.id}
            visit={visit}
            onStatusChange={(status) => updateStatus.mutate({ id: visit.id, status })}
            statusPending={updateStatus.isPending}
            onSaved={invalidate}
          />
        ))}
        {visits?.length === 0 && <p className="text-sm text-gray-500">No hay visitas agendadas este día.</p>}
      </div>
    </div>
  )
}

function VisitCard({
  visit,
  onStatusChange,
  statusPending,
  onSaved,
}: {
  visit: Visit
  onStatusChange: (status: VisitStatus) => void
  statusPending: boolean
  onSaved: () => void
}) {
  const [isEditing, setIsEditing] = useState(false)
  const [technicianId, setTechnicianId] = useState('')
  const [scheduledDate, setScheduledDate] = useState('')
  const [scheduledTime, setScheduledTime] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)

  const { data: technicians } = useQuery({
    queryKey: ['technicians'],
    queryFn: async () => (await api.get<Technician[]>('/users/technicians')).data,
    enabled: isEditing,
  })

  function startEditing() {
    setTechnicianId(visit.technician_id != null ? String(visit.technician_id) : '')
    setScheduledDate(visit.scheduled_date)
    setScheduledTime(visit.scheduled_time ? visit.scheduled_time.slice(0, 5) : '')
    setNotes(visit.notes ?? '')
    setError(null)
    setIsEditing(true)
  }

  const updateVisit = useMutation({
    mutationFn: async () =>
      (
        await api.put(`/visits/${visit.id}`, {
          technician_id: technicianId ? Number(technicianId) : null,
          scheduled_date: scheduledDate,
          scheduled_time: scheduledTime || null,
          notes: notes || null,
        })
      ).data,
    onSuccess: () => {
      onSaved()
      setIsEditing(false)
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? 'No se pudo guardar la visita'),
  })

  if (isEditing) {
    return (
      <Card className="space-y-2">
        <p className="font-medium text-brand-blue">{visit.project_code}</p>
        <form
          className="space-y-2"
          onSubmit={(e) => {
            e.preventDefault()
            updateVisit.mutate()
          }}
        >
          <div className="grid grid-cols-2 gap-2">
            <Field label="Fecha">
              <Input
                type="date"
                required
                value={scheduledDate}
                onChange={(e) => setScheduledDate(e.target.value)}
              />
            </Field>
            <Field label="Hora (opcional)">
              <Input type="time" value={scheduledTime} onChange={(e) => setScheduledTime(e.target.value)} />
            </Field>
          </div>
          <Field label="Técnico (opcional)">
            <select
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
              value={technicianId}
              onChange={(e) => setTechnicianId(e.target.value)}
            >
              <option value="">Sin asignar</option>
              {technicians?.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Notas">
            <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} />
          </Field>
          {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
          <div className="flex gap-2">
            <Button className="!w-auto flex-1" type="submit" disabled={updateVisit.isPending}>
              {updateVisit.isPending ? 'Guardando…' : 'Guardar cambios'}
            </Button>
            <Button
              className="!w-auto flex-1"
              type="button"
              variant="secondary"
              onClick={() => setIsEditing(false)}
              disabled={updateVisit.isPending}
            >
              Cancelar
            </Button>
          </div>
        </form>
      </Card>
    )
  }

  return (
    <Card className="space-y-2">
      <div className="flex items-center justify-between">
        <Link to={`/proyectos/${visit.project_id}`} className="font-medium text-brand-blue">
          {visit.project_code}
        </Link>
        <Badge tone={STATUS_TONE[visit.status]}>{VISIT_STATUS_LABELS[visit.status]}</Badge>
      </div>
      <p className="text-sm text-gray-500 dark:text-gray-400">{visit.client_name}</p>
      <div className="flex gap-3 text-xs text-gray-400">
        {visit.scheduled_time && <span>🕐 {visit.scheduled_time.slice(0, 5)}</span>}
        <span>👤 {visit.technician_name ?? 'Sin asignar'}</span>
      </div>
      {visit.notes && <p className="text-sm text-gray-600 dark:text-gray-400">{visit.notes}</p>}
      {visit.status === 'programada' && (
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            className="!w-auto px-4"
            onClick={() => onStatusChange('completada')}
            disabled={statusPending}
          >
            Marcar completada
          </Button>
          <Button variant="ghost" className="!w-auto px-4" onClick={() => onStatusChange('cancelada')} disabled={statusPending}>
            Cancelar
          </Button>
          <Button variant="ghost" className="!w-auto px-4" onClick={startEditing}>
            Reprogramar
          </Button>
        </div>
      )}
    </Card>
  )
}
