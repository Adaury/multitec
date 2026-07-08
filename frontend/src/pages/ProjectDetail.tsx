import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { api, downloadFile, viewFile } from '../lib/api'
import type {
  Budget,
  BudgetSuggestionOut,
  Engineering,
  Execution,
  Extension,
  ExtensionStatus,
  GenerateFromSurveyOut,
  Invoice,
  InvoiceHistoryEntry,
  LineItemInput,
  LogEntry,
  Material,
  MaterialStatus,
  NcfType,
  PreInvoice,
  Product,
  ProjectDetail as ProjectDetailType,
  PurchaseListPreviewOut,
  Quote,
  QuoteHistoryEntry,
  StageName,
  Survey,
  Technician,
  Ticket,
  TicketHistoryEntry,
  TicketStatus,
} from '../lib/types'
import {
  EXTENSION_STATUS_LABELS,
  MATERIAL_STATUS_LABELS,
  NCF_TYPE_LABELS,
  NCF_TYPES,
  PROJECT_STATUS_LABELS,
  QUOTE_HISTORY_LABELS,
  QUOTE_STATUS_LABELS,
  STAGE_LABELS,
  TICKET_STATUS_LABELS,
} from '../lib/types'
import { formatDOP } from '../lib/format'
import { useAuthStore } from '../lib/authStore'
import { useSpeechDictation } from '../lib/useSpeechDictation'
import { Badge, Button, Card, Field, IconButton, Textarea } from '../components/ui'
import { LineItemsEditor } from '../components/LineItemsEditor'

function DictationField({
  label,
  value,
  onChange,
  rows = 2,
  placeholder,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  rows?: number
  placeholder?: string
}) {
  const { supported, listening, start, stop } = useSpeechDictation({
    onResult: (text) => onChange(value ? `${value} ${text}` : text),
  })

  return (
    <Field label={label}>
      <div className="flex items-start gap-2">
        <div className="flex-1">
          <Textarea rows={rows} placeholder={placeholder} value={value} onChange={(e) => onChange(e.target.value)} />
        </div>
        {supported && (
          <IconButton
            type="button"
            onClick={listening ? stop : start}
            className={listening ? 'bg-red-100 text-red-600 dark:bg-red-950 dark:text-red-400' : ''}
            aria-label="Dictar por voz"
          >
            {listening ? '⏹' : '🎙️'}
          </IconButton>
        )}
      </div>
    </Field>
  )
}

type Tab =
  | 'info'
  | 'levantamiento'
  | 'ingenieria'
  | 'presupuesto'
  | 'cotizacion'
  | 'compras'
  | 'ejecucion'
  | 'bitacora'
  | 'prefactura'
  | 'factura'
  | 'ampliaciones'
  | 'tickets'

const TABS: { key: Tab; label: string }[] = [
  { key: 'info', label: 'Información' },
  { key: 'levantamiento', label: 'Levantamiento' },
  { key: 'ingenieria', label: 'Ingeniería' },
  { key: 'presupuesto', label: 'Presupuesto' },
  { key: 'cotizacion', label: 'Cotización' },
  { key: 'compras', label: 'Compras' },
  { key: 'ejecucion', label: 'Ejecución' },
  { key: 'bitacora', label: 'Bitácora' },
  { key: 'prefactura', label: 'Prefactura' },
  { key: 'factura', label: 'Factura' },
  { key: 'ampliaciones', label: 'Ampliaciones' },
  { key: 'tickets', label: 'Tickets' },
]

export function ProjectDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const tabParam = searchParams.get('tab')
  const initialTab = TABS.some((t) => t.key === tabParam) ? (tabParam as Tab) : 'info'
  const [tab, setTab] = useState<Tab>(initialTab)
  const [generateWarnings, setGenerateWarnings] = useState<string[]>([])

  const { data: project } = useQuery({
    queryKey: ['projects', id],
    queryFn: async () => (await api.get<ProjectDetailType>(`/projects/${id}`)).data,
  })

  if (!project) return <p className="py-4 text-sm text-gray-500 dark:text-gray-400">Cargando…</p>

  return (
    <div className="space-y-4 py-4 md:space-y-6 md:py-8">
      <button onClick={() => navigate(-1)} className="text-sm text-brand-blue">
        ← Volver
      </button>

      <Card>
        <div className="flex items-center justify-between">
          <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">{project.code}</p>
          {tab !== 'tickets' && <Badge>{PROJECT_STATUS_LABELS[project.status] ?? project.status}</Badge>}
        </div>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{project.client.name}</p>
      </Card>

      <div className="flex gap-2 overflow-x-auto rounded-2xl bg-brand-gray p-1 dark:bg-gray-800">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`shrink-0 whitespace-nowrap rounded-xl px-4 py-2 text-sm font-medium ${
              tab === t.key
                ? 'bg-white text-brand-blue shadow-sm dark:bg-gray-700 dark:text-blue-300'
                : 'text-gray-500 dark:text-gray-400'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {generateWarnings.length > 0 && (
        <div className="rounded-3xl border border-amber-300 bg-amber-50 p-5 dark:border-amber-800 dark:bg-amber-950">
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm font-medium text-amber-700 dark:text-amber-300">
              La cotización se generó, pero revisa esto:
            </p>
            <button
              onClick={() => setGenerateWarnings([])}
              className="text-sm text-amber-700 dark:text-amber-300"
              aria-label="Descartar avisos"
            >
              ×
            </button>
          </div>
          <ul className="mt-1 list-inside list-disc text-sm text-amber-700 dark:text-amber-300">
            {generateWarnings.map((warning, index) => (
              <li key={index}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      {tab === 'info' && <InfoTab project={project} />}
      {tab === 'levantamiento' && (
        <LevantamientoTab
          projectId={project.id}
          onGenerated={(warnings) => {
            setGenerateWarnings(warnings)
            setTab('cotizacion')
          }}
        />
      )}
      {tab === 'ingenieria' && <IngenieriaTab projectId={project.id} />}
      {tab === 'presupuesto' && <BudgetTab projectId={project.id} onConverted={() => setTab('cotizacion')} />}
      {tab === 'cotizacion' && <QuoteTab projectId={project.id} />}
      {tab === 'compras' && <PurchasesTab projectId={project.id} />}
      {tab === 'ejecucion' && <ExecutionTab projectId={project.id} />}
      {tab === 'bitacora' && <LogbookTab projectId={project.id} />}
      {tab === 'prefactura' && (
        <PreInvoiceTab
          projectId={project.id}
          clientHasRnc={!!project.client.rnc}
          onConverted={() => setTab('factura')}
        />
      )}
      {tab === 'factura' && <InvoiceTab projectId={project.id} />}
      {tab === 'ampliaciones' && <ExtensionsTab projectId={project.id} />}
      {tab === 'tickets' && <TicketsTab projectId={project.id} />}
    </div>
  )
}

const PROJECT_STATUS_KEYS = Object.keys(PROJECT_STATUS_LABELS)

function InfoTab({ project }: { project: ProjectDetailType }) {
  const queryClient = useQueryClient()
  const role = useAuthStore((s) => s.user?.role)
  const canManagePortal = role === 'admin' || role === 'oficina'
  const canEditProject = role === 'admin' || role === 'oficina'
  const [copied, setCopied] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [status, setStatus] = useState(project.status)
  const [responsibleId, setResponsibleId] = useState<number | ''>(project.responsible_id ?? '')
  const [description, setDescription] = useState(project.description ?? '')

  const { data: technicians } = useQuery({
    queryKey: ['technicians'],
    queryFn: async () => (await api.get<Technician[]>('/users/technicians')).data,
  })

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['projects'] })
  }

  const createLink = useMutation({
    mutationFn: async () => (await api.post(`/projects/${project.id}/public-link`)).data,
    onSuccess: invalidate,
  })
  const revokeLink = useMutation({
    mutationFn: async () => api.delete(`/projects/${project.id}/public-link`),
    onSuccess: invalidate,
  })

  const updateProject = useMutation({
    mutationFn: async () =>
      (
        await api.put(`/projects/${project.id}`, {
          status,
          responsible_id: responsibleId === '' ? null : responsibleId,
          description: description || null,
        })
      ).data,
    onSuccess: () => {
      invalidate()
      setIsEditing(false)
    },
  })

  function startEditing() {
    setStatus(project.status)
    setResponsibleId(project.responsible_id ?? '')
    setDescription(project.description ?? '')
    setIsEditing(true)
  }

  const portalUrl = project.public_token
    ? `${window.location.origin}/portal/${project.public_token}`
    : null

  return (
    <div className="space-y-4">
      <Card className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
        {isEditing ? (
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault()
              updateProject.mutate()
            }}
          >
            <Field label="Estado">
              <select
                className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                {PROJECT_STATUS_KEYS.map((key) => (
                  <option key={key} value={key}>
                    {PROJECT_STATUS_LABELS[key]}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Técnico responsable">
              <select
                className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
                value={responsibleId}
                onChange={(e) => setResponsibleId(e.target.value ? Number(e.target.value) : '')}
              >
                <option value="">Sin asignar</option>
                {technicians?.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Descripción">
              <Textarea value={description} onChange={(e) => setDescription(e.target.value)} />
            </Field>
            {updateProject.isError && (
              <p className="text-sm text-red-600 dark:text-red-400">No se pudo guardar el proyecto.</p>
            )}
            <div className="flex gap-2">
              <Button className="!w-auto flex-1" type="submit" disabled={updateProject.isPending}>
                {updateProject.isPending ? 'Guardando…' : 'Guardar cambios'}
              </Button>
              <Button
                className="!w-auto flex-1"
                type="button"
                variant="secondary"
                onClick={() => setIsEditing(false)}
                disabled={updateProject.isPending}
              >
                Cancelar
              </Button>
            </div>
          </form>
        ) : (
          <>
            <div className="flex items-center justify-between gap-2">
              <p>
                <span className="font-medium text-gray-800 dark:text-gray-200">Cliente:</span> {project.client.name}
                {project.client.company ? ` (${project.client.company})` : ''}
              </p>
              {canEditProject && (
                <button
                  onClick={startEditing}
                  className="shrink-0 rounded-full bg-brand-gray px-3 py-1 text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                >
                  Editar
                </button>
              )}
            </div>
            <p>
              <span className="font-medium text-gray-800 dark:text-gray-200">Fecha:</span> {project.date}
            </p>
            <p>
              <span className="font-medium text-gray-800 dark:text-gray-200">Estado:</span> {PROJECT_STATUS_LABELS[project.status] ?? project.status}
            </p>
            <p>
              <span className="font-medium text-gray-800 dark:text-gray-200">Técnico responsable:</span>{' '}
              {technicians?.find((t) => t.id === project.responsible_id)?.name ?? 'Sin asignar'}
            </p>
            {project.description && (
              <p>
                <span className="font-medium text-gray-800 dark:text-gray-200">Descripción:</span> {project.description}
              </p>
            )}
          </>
        )}
      </Card>

      {canManagePortal && (
        <Card className="space-y-2">
          <p className="text-sm font-medium text-gray-800 dark:text-gray-200">Portal de cliente</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Enlace de solo lectura, sin necesidad de iniciar sesión, para que el cliente vea el estado de su
            proyecto, sus cotizaciones y sus facturas (con PDF descargable).
          </p>
          {portalUrl ? (
            <div className="space-y-2">
              <div className="rounded-xl bg-brand-gray px-3 py-2 text-xs text-gray-600 break-all dark:bg-gray-800 dark:text-gray-400">
                {portalUrl}
              </div>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  onClick={() => {
                    navigator.clipboard.writeText(portalUrl)
                    setCopied(true)
                    setTimeout(() => setCopied(false), 2000)
                  }}
                >
                  {copied ? 'Copiado ✓' : 'Copiar enlace'}
                </Button>
                <Button variant="secondary" onClick={() => createLink.mutate()} disabled={createLink.isPending}>
                  Regenerar
                </Button>
                <Button variant="ghost" onClick={() => revokeLink.mutate()} disabled={revokeLink.isPending}>
                  Desactivar
                </Button>
              </div>
            </div>
          ) : (
            <Button onClick={() => createLink.mutate()} disabled={createLink.isPending}>
              {createLink.isPending ? 'Generando…' : 'Generar enlace'}
            </Button>
          )}
        </Card>
      )}
    </div>
  )
}

function LevantamientoTab({
  projectId,
  onGenerated,
}: {
  projectId: number
  onGenerated: (warnings: string[]) => void
}) {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [recording, setRecording] = useState(false)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const { data: survey } = useQuery({
    queryKey: ['survey', projectId],
    queryFn: async () => (await api.get<Survey>(`/projects/${projectId}/survey`)).data,
  })

  const [notes, setNotes] = useState('')
  const [measurements, setMeasurements] = useState('')
  const [observations, setObservations] = useState('')

  const notesInitialized = useRef(false)
  if (survey && !notesInitialized.current) {
    setNotes(survey.notes ?? '')
    setMeasurements(survey.measurements ?? '')
    setObservations(survey.observations ?? '')
    notesInitialized.current = true
  }

  const saveNotes = useMutation({
    mutationFn: async () =>
      (await api.put(`/projects/${projectId}/survey`, { notes, measurements, observations })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['survey', projectId] }),
  })

  const uploadAsset = useMutation({
    mutationFn: async ({ kind, file }: { kind: 'photo' | 'audio'; file: File }) => {
      const form = new FormData()
      form.append('kind', kind)
      form.append('file', file)
      return (await api.post(`/projects/${projectId}/survey/assets`, form)).data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['survey', projectId] }),
  })

  const deleteAsset = useMutation({
    mutationFn: async (assetId: number) =>
      api.delete(`/projects/${projectId}/survey/assets/${assetId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['survey', projectId] }),
  })

  const [aiError, setAiError] = useState<string | null>(null)
  const aiSummarize = useMutation({
    mutationFn: async () => (await api.post(`/projects/${projectId}/survey/ai-summarize`)).data,
    onSuccess: () => {
      setAiError(null)
      queryClient.invalidateQueries({ queryKey: ['survey', projectId] })
    },
    onError: (error: any) => setAiError(error?.response?.data?.detail ?? 'Error al organizar con IA'),
  })

  const [generateError, setGenerateError] = useState<string | null>(null)
  const generate = useMutation({
    mutationFn: async () =>
      (await api.post<GenerateFromSurveyOut>(`/projects/${projectId}/generate-from-survey`)).data,
    onSuccess: (data) => {
      setGenerateError(null)
      queryClient.invalidateQueries({ queryKey: ['budgets', projectId] })
      queryClient.invalidateQueries({ queryKey: ['quotes', projectId] })
      queryClient.invalidateQueries({ queryKey: ['engineering', projectId] })
      onGenerated(data.warnings)
    },
    onError: (error: any) => setGenerateError(error?.response?.data?.detail ?? 'Error al generar la cotización'),
  })

  async function toggleRecording() {
    if (recording) {
      mediaRecorderRef.current?.stop()
      setRecording(false)
      return
    }
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const recorder = new MediaRecorder(stream)
    chunksRef.current = []
    recorder.ondataavailable = (e) => chunksRef.current.push(e.data)
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
      const file = new File([blob], `nota-voz-${Date.now()}.webm`, { type: blob.type })
      uploadAsset.mutate({ kind: 'audio', file })
      stream.getTracks().forEach((track) => track.stop())
    }
    mediaRecorderRef.current = recorder
    recorder.start()
    setRecording(true)
  }

  return (
    <div className="space-y-4">
      <Card className="space-y-3">
        <DictationField label="Notas" rows={3} value={notes} onChange={setNotes} />
        <DictationField
          label="Medidas"
          placeholder="Ej. desde app Medidas del iPhone o cinta métrica"
          value={measurements}
          onChange={setMeasurements}
        />
        <DictationField label="Observaciones" value={observations} onChange={setObservations} />
        <Button onClick={() => saveNotes.mutate()} disabled={saveNotes.isPending}>
          {saveNotes.isPending ? 'Guardando…' : 'Guardar levantamiento'}
        </Button>
      </Card>

      <Card className="space-y-2">
        <p className="font-medium text-gray-800 dark:text-gray-200">Generar todo con IA</p>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Lee las notas, medidas y observaciones de arriba y crea de una vez el Presupuesto
          y la Cotización (y un borrador de Ingeniería, si aún no tiene uno) — sin volver a
          capturar nada. Puede tardar ~1 minuto.
        </p>
        {generateError && <p className="text-sm text-red-600 dark:text-red-400">{generateError}</p>}
        <Button onClick={() => generate.mutate()} disabled={generate.isPending}>
          {generate.isPending ? 'Generando… (puede tardar ~1 min)' : '🤖 Generar cotización con IA'}
        </Button>
      </Card>

      <Card className="space-y-3">
        <p className="font-medium text-gray-800 dark:text-gray-200">Fotos y audio</p>
        <div className="flex gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) uploadAsset.mutate({ kind: 'photo', file })
              e.target.value = ''
            }}
          />
          <Button variant="secondary" onClick={() => fileInputRef.current?.click()}>
            📷 Tomar foto
          </Button>
          <Button variant={recording ? 'primary' : 'secondary'} onClick={toggleRecording}>
            {recording ? '⏹ Detener' : '🎙️ Grabar nota'}
          </Button>
        </div>

        <div className="grid grid-cols-3 gap-2">
          {survey?.assets
            .filter((a) => a.kind === 'photo')
            .map((asset) => (
              <div key={asset.id} className="relative">
                <img
                  src={`/${asset.file_path.replace(/^.*uploads\//, 'uploads/')}`}
                  className="aspect-square rounded-xl object-cover"
                  alt="Foto de levantamiento"
                />
                <button
                  type="button"
                  onClick={() => deleteAsset.mutate(asset.id)}
                  disabled={deleteAsset.isPending}
                  aria-label="Borrar foto"
                  className="absolute right-1 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-black/60 text-xs text-white"
                >
                  ✕
                </button>
              </div>
            ))}
        </div>

        <div className="space-y-2">
          {survey?.assets
            .filter((a) => a.kind === 'audio')
            .map((asset) => (
              <div key={asset.id} className="flex items-center gap-2">
                <audio
                  controls
                  src={`/${asset.file_path.replace(/^.*uploads\//, 'uploads/')}`}
                  className="w-full"
                />
                <button
                  type="button"
                  onClick={() => deleteAsset.mutate(asset.id)}
                  disabled={deleteAsset.isPending}
                  aria-label="Borrar nota de voz"
                  className="shrink-0 text-lg text-red-500"
                >
                  ✕
                </button>
              </div>
            ))}
        </div>
      </Card>

      <Card className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="font-medium text-gray-800 dark:text-gray-200">Resumen con IA</p>
          <Button
            variant="secondary"
            className="!w-auto px-4"
            onClick={() => aiSummarize.mutate()}
            disabled={aiSummarize.isPending}
          >
            {aiSummarize.isPending ? 'Organizando…' : '🤖 Organizar con IA'}
          </Button>
        </div>
        {aiError && <p className="text-sm text-red-600 dark:text-red-400">{aiError}</p>}
        {survey?.ai_summary && <p className="whitespace-pre-line text-sm text-gray-700 dark:text-gray-300">{survey.ai_summary}</p>}
        {!survey?.ai_summary && !aiError && (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Analiza las notas y fotos del levantamiento con IA y genera un resumen técnico.
          </p>
        )}
      </Card>
    </div>
  )
}

function IngenieriaTab({ projectId }: { projectId: number }) {
  const queryClient = useQueryClient()
  const { data: engineering } = useQuery({
    queryKey: ['engineering', projectId],
    queryFn: async () => (await api.get<Engineering>(`/projects/${projectId}/engineering`)).data,
  })

  const [form, setForm] = useState({
    recommended_equipment: '',
    distribution: '',
    conduits: '',
    wiring: '',
    technical_design: '',
    observations: '',
  })

  const initialized = useRef(false)
  if (engineering && !initialized.current) {
    setForm({
      recommended_equipment: engineering.recommended_equipment ?? '',
      distribution: engineering.distribution ?? '',
      conduits: engineering.conduits ?? '',
      wiring: engineering.wiring ?? '',
      technical_design: engineering.technical_design ?? '',
      observations: engineering.observations ?? '',
    })
    initialized.current = true
  }

  const save = useMutation({
    mutationFn: async () => (await api.put(`/projects/${projectId}/engineering`, form)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['engineering', projectId] }),
  })

  const [aiError, setAiError] = useState<string | null>(null)
  const aiDraft = useMutation({
    mutationFn: async () => (await api.post(`/projects/${projectId}/engineering/ai-draft`)).data,
    onSuccess: (draft) => {
      setAiError(null)
      setForm(draft)
    },
    onError: (error: any) => setAiError(error?.response?.data?.detail ?? 'Error al generar la propuesta'),
  })

  return (
    <Card className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3 md:max-w-2xl">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm text-gray-500 dark:text-gray-400">Borrador generado con IA a partir del levantamiento.</p>
          {engineering?.ai_generated && (
            <Badge tone="blue">
              <span className="shrink-0 whitespace-nowrap">🤖 Generado por IA</span>
            </Badge>
          )}
        </div>
        <Button
          variant="secondary"
          className="!w-auto shrink-0 px-4"
          onClick={() => aiDraft.mutate()}
          disabled={aiDraft.isPending}
        >
          {aiDraft.isPending ? 'Generando…' : '🤖 Generar propuesta'}
        </Button>
      </div>
      {aiError && <p className="text-sm text-red-600 dark:text-red-400">{aiError}</p>}
      <Field label="Equipos recomendados">
        <Textarea rows={2} value={form.recommended_equipment} onChange={(e) => setForm({ ...form, recommended_equipment: e.target.value })} />
      </Field>
      <Field label="Distribución">
        <Textarea rows={2} value={form.distribution} onChange={(e) => setForm({ ...form, distribution: e.target.value })} />
      </Field>
      <Field label="Canalizaciones">
        <Textarea rows={2} value={form.conduits} onChange={(e) => setForm({ ...form, conduits: e.target.value })} />
      </Field>
      <Field label="Cableado">
        <Textarea rows={2} value={form.wiring} onChange={(e) => setForm({ ...form, wiring: e.target.value })} />
      </Field>
      <Field label="Diseño técnico">
        <Textarea rows={2} value={form.technical_design} onChange={(e) => setForm({ ...form, technical_design: e.target.value })} />
      </Field>
      <Field label="Observaciones">
        <Textarea rows={2} value={form.observations} onChange={(e) => setForm({ ...form, observations: e.target.value })} />
      </Field>
      <Button onClick={() => save.mutate()} disabled={save.isPending}>
        {save.isPending ? 'Guardando…' : 'Guardar ingeniería'}
      </Button>
    </Card>
  )
}

function useProducts() {
  return useQuery({
    queryKey: ['catalog'],
    queryFn: async () => (await api.get<Product[]>('/catalog')).data,
  })
}

function BudgetTab({ projectId, onConverted }: { projectId: number; onConverted: () => void }) {
  const queryClient = useQueryClient()
  const { data: products } = useProducts()
  const { data: budgets } = useQuery({
    queryKey: ['budgets', projectId],
    queryFn: async () => (await api.get<Budget[]>(`/projects/${projectId}/budgets`)).data,
  })

  const [showForm, setShowForm] = useState(false)
  const [notes, setNotes] = useState('')
  const [items, setItems] = useState<LineItemInput[]>([])

  const createBudget = useMutation({
    mutationFn: async () => (await api.post(`/projects/${projectId}/budgets`, { notes, items })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets', projectId] })
      setShowForm(false)
      setNotes('')
      setItems([])
    },
  })

  const convertToQuote = useMutation({
    mutationFn: async (budgetId: number) => (await api.post(`/budgets/${budgetId}/convert-to-quote`)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quotes', projectId] })
      onConverted()
    },
  })

  const [aiError, setAiError] = useState<string | null>(null)
  const [aiWarnings, setAiWarnings] = useState<string[]>([])
  const aiSuggest = useMutation({
    mutationFn: async () => (await api.post<BudgetSuggestionOut>(`/projects/${projectId}/budget-suggestions`)).data,
    onSuccess: (data) => {
      setAiError(null)
      setAiWarnings(data.warnings)
      setItems(data.items.map((item) => ({ ...item })))
    },
    onError: (error: any) => {
      setAiWarnings([])
      setAiError(error?.response?.data?.detail ?? 'Error al sugerir materiales')
    },
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between md:max-w-2xl">
        <p className="text-sm text-gray-500 dark:text-gray-400">Documento resumido — solo muestra el total.</p>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-full bg-brand-blue px-4 py-2 text-sm font-medium text-white"
        >
          {showForm ? 'Cancelar' : '+ Nuevo'}
        </button>
      </div>

      {showForm && (
        <Card className="space-y-3">
          <Field label="Notas">
            <Textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </Field>
          <Button
            type="button"
            variant="secondary"
            onClick={() => aiSuggest.mutate()}
            disabled={aiSuggest.isPending}
          >
            {aiSuggest.isPending ? 'Sugiriendo…' : '🤖 Sugerir materiales'}
          </Button>
          {aiError && <p className="text-sm text-red-600 dark:text-red-400">{aiError}</p>}
          {aiWarnings.length > 0 && (
            <ul className="list-inside list-disc text-sm text-amber-600 dark:text-amber-400">
              {aiWarnings.map((warning, index) => (
                <li key={index}>{warning}</li>
              ))}
            </ul>
          )}
          <LineItemsEditor items={items} onChange={setItems} products={products ?? []} mode="budget" />
          <Button onClick={() => createBudget.mutate()} disabled={createBudget.isPending || items.length === 0}>
            {createBudget.isPending ? 'Guardando…' : 'Guardar presupuesto'}
          </Button>
        </Card>
      )}

      <div className="grid grid-cols-1 items-start gap-3 md:grid-cols-2 xl:grid-cols-3">
        {budgets?.map((budget) => (
          <BudgetCard
            key={budget.id}
            budget={budget}
            projectId={projectId}
            products={products ?? []}
            onConvert={() => convertToQuote.mutate(budget.id)}
            isConverting={convertToQuote.isPending}
          />
        ))}
        {budgets?.length === 0 && <p className="text-sm text-gray-500 dark:text-gray-400">Aún no hay presupuestos.</p>}
      </div>
    </div>
  )
}

function BudgetCard({
  budget,
  projectId,
  products,
  onConvert,
  isConverting,
}: {
  budget: Budget
  projectId: number
  products: Product[]
  onConvert: () => void
  isConverting: boolean
}) {
  const queryClient = useQueryClient()
  const [isEditing, setIsEditing] = useState(false)
  const [notes, setNotes] = useState(budget.notes ?? '')
  const [items, setItems] = useState<LineItemInput[]>([])

  function startEditing() {
    setNotes(budget.notes ?? '')
    setItems(
      budget.items.map((item) => {
        const product = item.product_id ? products.find((p) => p.id === item.product_id) : undefined
        return {
          product_id: item.product_id,
          description: item.description,
          quantity: item.quantity,
          unit_price: product?.price ?? 0,
          note: item.note,
        }
      }),
    )
    setIsEditing(true)
  }

  const updateBudget = useMutation({
    mutationFn: async () => (await api.put(`/budgets/${budget.id}`, { notes, items })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets', projectId] })
      setIsEditing(false)
    },
  })

  const hasUnpricedFreeTextItems = items.some((item) => !item.product_id && item.unit_price === 0)

  if (isEditing) {
    return (
      <Card className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="font-medium text-gray-900 dark:text-gray-100">{budget.code}</p>
          <Badge tone="gray">Editando</Badge>
        </div>
        <Field label="Notas">
          <Textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </Field>
        <LineItemsEditor items={items} onChange={setItems} products={products} mode="budget" />
        {hasUnpricedFreeTextItems && (
          <p className="text-xs text-amber-600 dark:text-amber-400">
            Las líneas sin producto de catálogo no guardan su precio unitario — revisa el precio de las líneas de
            texto libre antes de guardar, o el total puede quedar incompleto.
          </p>
        )}
        {updateBudget.isError && (
          <p className="text-sm text-red-600 dark:text-red-400">No se pudo guardar el presupuesto.</p>
        )}
        <div className="flex gap-2">
          <Button
            className="!w-auto flex-1"
            onClick={() => updateBudget.mutate()}
            disabled={updateBudget.isPending || items.length === 0}
          >
            {updateBudget.isPending ? 'Guardando…' : 'Guardar cambios'}
          </Button>
          <Button
            variant="secondary"
            className="!w-auto flex-1"
            onClick={() => setIsEditing(false)}
            disabled={updateBudget.isPending}
          >
            Cancelar
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <Card>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <p className="font-medium text-gray-900 dark:text-gray-100">{budget.code}</p>
          {budget.ai_generated && <Badge tone="blue">🤖 IA</Badge>}
        </div>
        <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">{formatDOP(budget.total)}</p>
      </div>
      {budget.notes && <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{budget.notes}</p>}
      <ul className="mt-2 list-inside list-disc text-sm text-gray-600 dark:text-gray-400">
        {budget.items.map((item) => (
          <li key={item.id}>
            {item.quantity} × {item.description}
            {item.note && <span className="block pl-4 text-xs italic text-gray-400 dark:text-gray-500">{item.note}</span>}
          </li>
        ))}
      </ul>
      <div className="mt-3 space-y-1.5">
        <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
          Resumen para el cliente (solo nombres y total)
        </p>
        <div className="flex gap-2">
          <Button
            variant="ghost"
            className="!w-auto flex-1 px-3 py-2 text-sm"
            onClick={() => viewFile(`/budgets/${budget.id}/pdf`)}
          >
            Ver
          </Button>
          <Button
            variant="secondary"
            className="!w-auto flex-1 px-3 py-2 text-sm"
            onClick={() => downloadFile(`/budgets/${budget.id}/pdf`, `${budget.code}-resumen.pdf`)}
          >
            Descargar
          </Button>
        </div>
      </div>
      <div className="mt-3 flex gap-2">
        <Button variant="secondary" className="!w-auto flex-1" onClick={startEditing}>
          Editar
        </Button>
        <Button variant="secondary" className="!w-auto flex-1" onClick={onConvert} disabled={isConverting}>
          {isConverting ? 'Convirtiendo…' : 'Convertir a cotización →'}
        </Button>
      </div>
    </Card>
  )
}

function QuoteTab({ projectId }: { projectId: number }) {
  const queryClient = useQueryClient()
  const { data: products } = useProducts()
  const { data: quotes } = useQuery({
    queryKey: ['quotes', projectId],
    queryFn: async () => (await api.get<Quote[]>(`/projects/${projectId}/quotes`)).data,
  })

  const [showForm, setShowForm] = useState(false)
  const [notes, setNotes] = useState('')
  const [items, setItems] = useState<LineItemInput[]>([])
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const createQuote = useMutation({
    mutationFn: async () => (await api.post(`/projects/${projectId}/quotes`, { notes, items })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quotes', projectId] })
      setShowForm(false)
      setNotes('')
      setItems([])
    },
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between md:max-w-2xl">
        <p className="text-sm text-gray-500 dark:text-gray-400">Documento detallado con ITBIS 18%.</p>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-full bg-brand-blue px-4 py-2 text-sm font-medium text-white"
        >
          {showForm ? 'Cancelar' : '+ Nueva'}
        </button>
      </div>

      {showForm && (
        <Card className="space-y-3">
          <Field label="Notas">
            <Textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </Field>
          <LineItemsEditor items={items} onChange={setItems} products={products ?? []} mode="quote" />
          <Button onClick={() => createQuote.mutate()} disabled={createQuote.isPending || items.length === 0}>
            {createQuote.isPending ? 'Guardando…' : 'Guardar cotización'}
          </Button>
        </Card>
      )}

      <div className="grid grid-cols-1 items-start gap-3 md:grid-cols-2 xl:grid-cols-3">
        {quotes?.map((quote) => (
          <QuoteCard
            key={quote.id}
            quote={quote}
            expanded={expandedId === quote.id}
            onToggle={() => setExpandedId(expandedId === quote.id ? null : quote.id)}
            projectId={projectId}
            products={products ?? []}
          />
        ))}
        {quotes?.length === 0 && <p className="text-sm text-gray-500 dark:text-gray-400">Aún no hay cotizaciones.</p>}
      </div>
    </div>
  )
}

const STATUS_TONE: Record<string, 'blue' | 'green' | 'red' | 'gray'> = {
  pendiente: 'blue',
  aprobada: 'green',
  no_aprobada: 'red',
  archivada: 'gray',
}

function QuoteCard({
  quote,
  expanded,
  onToggle,
  projectId,
  products,
}: {
  quote: Quote
  expanded: boolean
  onToggle: () => void
  projectId: number
  products: Product[]
}) {
  const queryClient = useQueryClient()
  const [reason, setReason] = useState('')
  const [showRejectForm, setShowRejectForm] = useState(false)
  const [showPurchaseList, setShowPurchaseList] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [editNotes, setEditNotes] = useState('')
  const [editItems, setEditItems] = useState<LineItemInput[]>([])

  const { data: history } = useQuery({
    queryKey: ['quote-history', quote.id],
    queryFn: async () => (await api.get<QuoteHistoryEntry[]>(`/quotes/${quote.id}/history`)).data,
    enabled: expanded,
  })

  const { data: purchaseListPreview, isLoading: purchaseListLoading } = useQuery({
    queryKey: ['purchase-list-preview', quote.id],
    queryFn: async () =>
      (await api.get<PurchaseListPreviewOut>(`/quotes/${quote.id}/purchase-list-preview`)).data,
    enabled: showPurchaseList,
  })

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['quotes', projectId] })
    queryClient.invalidateQueries({ queryKey: ['quote-history', quote.id] })
  }

  const approve = useMutation({
    mutationFn: async () => (await api.post(`/quotes/${quote.id}/approve`)).data,
    onSuccess: invalidate,
  })
  const reject = useMutation({
    mutationFn: async () => (await api.post(`/quotes/${quote.id}/reject`, { reason })).data,
    onSuccess: () => {
      invalidate()
      setShowRejectForm(false)
      setReason('')
    },
  })
  const archive = useMutation({
    mutationFn: async () => (await api.post(`/quotes/${quote.id}/archive`)).data,
    onSuccess: invalidate,
  })
  const reactivate = useMutation({
    mutationFn: async () => (await api.post(`/quotes/${quote.id}/reactivate`)).data,
    onSuccess: invalidate,
  })

  const updateQuote = useMutation({
    mutationFn: async () => (await api.put(`/quotes/${quote.id}`, { notes: editNotes, items: editItems })).data,
    onSuccess: () => {
      invalidate()
      setIsEditing(false)
    },
  })

  function startEditing() {
    setEditNotes(quote.notes ?? '')
    setEditItems(
      quote.items.map((item) => ({
        product_id: item.product_id,
        description: item.description,
        quantity: item.quantity,
        unit_price: item.unit_price,
        note: item.note,
      })),
    )
    setIsEditing(true)
  }

  return (
    <Card>
      <button className="w-full text-left" onClick={onToggle}>
        <div className="flex items-center justify-between">
          <p className="font-medium text-gray-900 dark:text-gray-100">{quote.code}</p>
          <Badge tone={STATUS_TONE[quote.status]}>{QUOTE_STATUS_LABELS[quote.status]}</Badge>
        </div>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{formatDOP(quote.total)}</p>
      </button>

      {expanded && isEditing && (
        <div className="mt-3 space-y-3 border-t border-gray-100 pt-3 dark:border-gray-800">
          <Field label="Notas">
            <Textarea rows={2} value={editNotes} onChange={(e) => setEditNotes(e.target.value)} />
          </Field>
          <LineItemsEditor items={editItems} onChange={setEditItems} products={products} mode="quote" />
          {updateQuote.isError && (
            <p className="text-sm text-red-600 dark:text-red-400">No se pudo guardar la cotización.</p>
          )}
          <div className="flex gap-2">
            <Button
              className="!w-auto flex-1"
              onClick={() => updateQuote.mutate()}
              disabled={updateQuote.isPending || editItems.length === 0}
            >
              {updateQuote.isPending ? 'Guardando…' : 'Guardar cambios'}
            </Button>
            <Button
              className="!w-auto flex-1"
              variant="secondary"
              onClick={() => setIsEditing(false)}
              disabled={updateQuote.isPending}
            >
              Cancelar
            </Button>
          </div>
        </div>
      )}

      {expanded && !isEditing && (
        <div className="mt-3 space-y-3 border-t border-gray-100 pt-3 dark:border-gray-800">
          <ul className="space-y-1 text-sm text-gray-600 dark:text-gray-400">
            {quote.items.map((item) => (
              <li key={item.id}>
                <div className="flex justify-between">
                  <span>
                    {item.quantity} × {item.description}
                  </span>
                  <span>{formatDOP(item.subtotal)}</span>
                </div>
                {item.note && <p className="text-xs italic text-gray-400 dark:text-gray-500">{item.note}</p>}
              </li>
            ))}
          </ul>
          <div className="space-y-1 rounded-xl bg-brand-gray p-3 text-sm dark:bg-gray-800">
            <div className="flex justify-between text-gray-500 dark:text-gray-400">
              <span>Subtotal</span>
              <span>{formatDOP(quote.subtotal)}</span>
            </div>
            <div className="flex justify-between text-gray-500 dark:text-gray-400">
              <span>ITBIS (18%)</span>
              <span>{formatDOP(quote.itbis)}</span>
            </div>
            <div className="flex justify-between font-semibold text-gray-900 dark:text-gray-100">
              <span>Total</span>
              <span>{formatDOP(quote.total)}</span>
            </div>
          </div>

          <div className="space-y-3">
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Cotización detallada</p>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  className="!w-auto flex-1 px-3 py-2 text-sm"
                  onClick={() => viewFile(`/quotes/${quote.id}/pdf`)}
                >
                  Ver
                </Button>
                <Button
                  variant="secondary"
                  className="!w-auto flex-1 px-3 py-2 text-sm"
                  onClick={() => downloadFile(`/quotes/${quote.id}/pdf`, `${quote.code}.pdf`)}
                >
                  Descargar
                </Button>
              </div>
            </div>
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
                Cotización ejecutiva (resumen por categoría)
              </p>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  className="!w-auto flex-1 px-3 py-2 text-sm"
                  onClick={() => viewFile(`/quotes/${quote.id}/pdf?variant=ejecutiva`)}
                >
                  Ver
                </Button>
                <Button
                  variant="secondary"
                  className="!w-auto flex-1 px-3 py-2 text-sm"
                  onClick={() =>
                    downloadFile(`/quotes/${quote.id}/pdf?variant=ejecutiva`, `${quote.code}-ejecutiva.pdf`)
                  }
                >
                  Descargar
                </Button>
              </div>
            </div>
          </div>

          <div className="space-y-1.5">
            <button
              type="button"
              onClick={() => setShowPurchaseList((v) => !v)}
              className="text-xs font-medium text-brand-blue hover:underline"
            >
              {showPurchaseList ? 'Ocultar lista de compras' : 'Ver lista de compras'}
            </button>
            {showPurchaseList && (
              <div className="space-y-1 rounded-xl bg-brand-gray p-3 text-sm dark:bg-gray-800">
                {purchaseListLoading && <p className="text-xs text-gray-400">Cargando…</p>}
                {purchaseListPreview?.already_generated && (
                  <p className="text-xs text-amber-600 dark:text-amber-400">
                    Ya se generó como lista de compras real al aprobar — esto es lo mismo.
                  </p>
                )}
                {purchaseListPreview && purchaseListPreview.items.length === 0 && (
                  <p className="text-xs text-gray-400">Sin materiales.</p>
                )}
                {purchaseListPreview && purchaseListPreview.items.length > 0 && (
                  <ul className="space-y-1 text-gray-600 dark:text-gray-400">
                    {purchaseListPreview.items.map((item, index) => (
                      <li key={index}>
                        {item.quantity} × {item.description}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>

          {quote.status === 'pendiente' && (
            <div className="flex gap-2">
              <Button className="!w-auto flex-1" onClick={() => approve.mutate()} disabled={approve.isPending}>
                Aprobar
              </Button>
              <Button
                className="!w-auto flex-1"
                variant="secondary"
                onClick={() => setShowRejectForm((v) => !v)}
              >
                Rechazar
              </Button>
              <Button className="!w-auto flex-1" variant="ghost" onClick={startEditing}>
                Editar
              </Button>
            </div>
          )}
          {showRejectForm && (
            <div className="space-y-2">
              <Field label="Motivo del rechazo">
                <Textarea rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
              </Field>
              <Button variant="secondary" onClick={() => reject.mutate()} disabled={reject.isPending || !reason}>
                {reject.isPending ? 'Guardando…' : 'Confirmar rechazo'}
              </Button>
            </div>
          )}
          {quote.status !== 'archivada' && quote.status !== 'aprobada' && (
            <Button variant="ghost" onClick={() => archive.mutate()} disabled={archive.isPending}>
              Archivar
            </Button>
          )}
          {quote.status === 'archivada' && (
            <Button variant="secondary" onClick={() => reactivate.mutate()} disabled={reactivate.isPending}>
              Reactivar
            </Button>
          )}

          {history && history.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">Historial</p>
              <ul className="space-y-1 text-xs text-gray-500 dark:text-gray-400">
                {history.map((h) => (
                  <li key={h.id}>
                    {new Date(h.created_at).toLocaleString('es-DO')} — {QUOTE_HISTORY_LABELS[h.action] ?? h.action}
                    {h.note ? `: ${h.note}` : ''}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </Card>
  )
}

const MATERIAL_STATUS_OPTIONS: MaterialStatus[] = ['disponible', 'pendiente_compra', 'comprado', 'instalado']

function PurchasesTab({ projectId }: { projectId: number }) {
  const queryClient = useQueryClient()
  const { data: products } = useProducts()
  const { data: materials } = useQuery({
    queryKey: ['materials', projectId],
    queryFn: async () => (await api.get<Material[]>(`/projects/${projectId}/materials`)).data,
  })

  const [showForm, setShowForm] = useState(false)
  const [productId, setProductId] = useState('')
  const [description, setDescription] = useState('')
  const [quantity, setQuantity] = useState(1)
  const [notes, setNotes] = useState('')

  const createMaterial = useMutation({
    mutationFn: async () =>
      (
        await api.post(`/projects/${projectId}/materials`, {
          product_id: productId ? Number(productId) : null,
          description,
          quantity,
          notes: notes || null,
        })
      ).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['materials', projectId] })
      setShowForm(false)
      setProductId('')
      setDescription('')
      setQuantity(1)
      setNotes('')
    },
  })

  const updateStatus = useMutation({
    mutationFn: async ({ id, status }: { id: number; status: MaterialStatus }) =>
      (await api.put(`/materials/${id}/status`, { status })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['materials', projectId] }),
  })

  const purchaseList = materials?.filter((m) => m.status === 'pendiente_compra') ?? []
  const others = materials?.filter((m) => m.status !== 'pendiente_compra') ?? []

  function selectProduct(id: string) {
    setProductId(id)
    const product = products?.find((p) => p.id === Number(id))
    if (product) setDescription(product.name)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between md:max-w-2xl">
        <p className="text-sm text-gray-500 dark:text-gray-400">Lista inteligente generada al aprobar cotizaciones.</p>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-full bg-brand-blue px-4 py-2 text-sm font-medium text-white"
        >
          {showForm ? 'Cancelar' : '+ Agregar'}
        </button>
      </div>

      {showForm && (
        <Card className="space-y-3">
          <Field label="Producto (opcional)">
            <select
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
              value={productId}
              onChange={(e) => selectProduct(e.target.value)}
            >
              <option value="">Texto libre…</option>
              {products?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.code} · {p.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Descripción">
            <input
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </Field>
          <Field label="Cantidad">
            <input
              type="number"
              min="0"
              step="0.01"
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
              value={quantity}
              onChange={(e) => setQuantity(Number(e.target.value))}
            />
          </Field>
          <Field label="Notas (opcional)">
            <input
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </Field>
          <Button onClick={() => createMaterial.mutate()} disabled={createMaterial.isPending || !description}>
            {createMaterial.isPending ? 'Guardando…' : 'Agregar material'}
          </Button>
        </Card>
      )}

      <div>
        <p className="mb-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
          Lista de compra ({purchaseList.length})
        </p>
        <div className="grid items-start gap-2 md:grid-cols-2 xl:grid-cols-3">
          {purchaseList.map((m) => (
            <MaterialRow key={m.id} material={m} onStatusChange={(status) => updateStatus.mutate({ id: m.id, status })} />
          ))}
          {purchaseList.length === 0 && <p className="text-sm text-gray-500 dark:text-gray-400">Nada pendiente de comprar.</p>}
        </div>
      </div>

      {others.length > 0 && (
        <div>
          <p className="mb-2 text-sm font-semibold text-gray-900 dark:text-gray-100">Otros materiales</p>
          <div className="grid items-start gap-2 md:grid-cols-2 xl:grid-cols-3">
            {others.map((m) => (
              <MaterialRow key={m.id} material={m} onStatusChange={(status) => updateStatus.mutate({ id: m.id, status })} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function MaterialRow({ material, onStatusChange }: { material: Material; onStatusChange: (status: MaterialStatus) => void }) {
  return (
    <Card className="flex items-center justify-between gap-3">
      <div>
        <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
          {material.quantity} × {material.description}
        </p>
        {material.notes && <p className="text-xs text-gray-500 dark:text-gray-400">{material.notes}</p>}
        <Badge tone={material.status === 'pendiente_compra' ? 'amber' : material.status === 'instalado' ? 'green' : 'gray'}>
          {MATERIAL_STATUS_LABELS[material.status]}
        </Badge>
      </div>
      <select
        className="rounded-xl border border-gray-200 bg-white px-2 py-2 text-xs text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
        value={material.status}
        onChange={(e) => onStatusChange(e.target.value as MaterialStatus)}
      >
        {MATERIAL_STATUS_OPTIONS.map((status) => (
          <option key={status} value={status}>
            {MATERIAL_STATUS_LABELS[status]}
          </option>
        ))}
      </select>
    </Card>
  )
}

function ExecutionTab({ projectId }: { projectId: number }) {
  const queryClient = useQueryClient()
  const { data: execution } = useQuery({
    queryKey: ['execution', projectId],
    queryFn: async () => (await api.get<Execution>(`/projects/${projectId}/execution`)).data,
  })

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['execution', projectId] })
  }

  const advance = useMutation({
    mutationFn: async () => (await api.post(`/projects/${projectId}/execution/advance`)).data,
    onSuccess: invalidate,
  })
  const undo = useMutation({
    mutationFn: async () => (await api.post(`/projects/${projectId}/execution/undo`)).data,
    onSuccess: invalidate,
  })

  if (!execution) return <p className="text-sm text-gray-500 dark:text-gray-400">Cargando…</p>

  const allDone = execution.stages.every((s) => s.completed)
  const anyDone = execution.stages.some((s) => s.completed)

  return (
    <div className="space-y-4">
      <Card>
        <div className="mb-2 flex items-center justify-between">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Avance</p>
          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{execution.progress_percent}%</p>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-brand-gray dark:bg-gray-800">
          <div className="h-full rounded-full bg-brand-blue" style={{ width: `${execution.progress_percent}%` }} />
        </div>
      </Card>

      <div className="space-y-2">
        {execution.stages.map((stage) => (
          <Card key={stage.id} className="flex items-center gap-3">
            <span
              className={`flex h-8 w-8 items-center justify-center rounded-full text-sm ${
                stage.completed
                  ? 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300'
                  : 'bg-brand-gray text-gray-400 dark:bg-gray-800'
              }`}
            >
              {stage.completed ? '✓' : stage.order + 1}
            </span>
            <span className={`text-sm font-medium ${stage.completed ? 'text-gray-900 dark:text-gray-100' : 'text-gray-500 dark:text-gray-400'}`}>
              {STAGE_LABELS[stage.name as StageName]}
            </span>
          </Card>
        ))}
      </div>

      <div className="flex gap-2">
        <Button onClick={() => advance.mutate()} disabled={advance.isPending || allDone}>
          {allDone ? 'Todas completas' : 'Completar siguiente etapa'}
        </Button>
        {anyDone && (
          <Button variant="secondary" onClick={() => undo.mutate()} disabled={undo.isPending}>
            Deshacer
          </Button>
        )}
      </div>
    </div>
  )
}

function LogbookTab({ projectId }: { projectId: number }) {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [comment, setComment] = useState('')
  const [pendingPhotoEntryId, setPendingPhotoEntryId] = useState<number | null>(null)

  const { data: entries } = useQuery({
    queryKey: ['logbook', projectId],
    queryFn: async () => (await api.get<LogEntry[]>(`/projects/${projectId}/logbook`)).data,
  })
  const { data: technicians } = useQuery({
    queryKey: ['technicians'],
    queryFn: async () => (await api.get<Technician[]>('/users/technicians')).data,
  })

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['logbook', projectId] })
  }

  const createEntry = useMutation({
    mutationFn: async () => (await api.post(`/projects/${projectId}/logbook`, { comment })).data,
    onSuccess: () => {
      invalidate()
      setComment('')
    },
  })

  const uploadPhoto = useMutation({
    mutationFn: async ({ entryId, file }: { entryId: number; file: File }) => {
      const form = new FormData()
      form.append('file', file)
      return (await api.post(`/logbook/${entryId}/photos`, form)).data
    },
    onSuccess: invalidate,
  })

  return (
    <div className="space-y-4">
      <Card className="space-y-3">
        <Field label="Nueva entrada">
          <Textarea rows={3} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Qué se hizo hoy…" />
        </Field>
        <Button onClick={() => createEntry.mutate()} disabled={createEntry.isPending || !comment}>
          {createEntry.isPending ? 'Guardando…' : 'Agregar a la bitácora'}
        </Button>
      </Card>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file && pendingPhotoEntryId) uploadPhoto.mutate({ entryId: pendingPhotoEntryId, file })
          e.target.value = ''
          setPendingPhotoEntryId(null)
        }}
      />

      <div className="space-y-3 md:max-w-2xl">
        {entries?.map((entry) => (
          <Card key={entry.id}>
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs text-gray-400">{entry.entry_date}</p>
              {technicians?.find((t) => t.id === entry.responsible_id) && (
                <p className="text-xs text-gray-400">
                  {technicians.find((t) => t.id === entry.responsible_id)?.name}
                </p>
              )}
            </div>
            <p className="mt-1 text-sm text-gray-800 dark:text-gray-200">{entry.comment}</p>
            {entry.assets.length > 0 && (
              <div className="mt-2 grid grid-cols-3 gap-2">
                {entry.assets.map((asset) => (
                  <img
                    key={asset.id}
                    src={`/${asset.file_path.replace(/^.*uploads\//, 'uploads/')}`}
                    className="aspect-square rounded-xl object-cover"
                    alt="Foto de bitácora"
                  />
                ))}
              </div>
            )}
            <Button
              variant="ghost"
              className="mt-2"
              onClick={() => {
                setPendingPhotoEntryId(entry.id)
                fileInputRef.current?.click()
              }}
            >
              📷 Agregar foto
            </Button>
          </Card>
        ))}
        {entries?.length === 0 && <p className="text-sm text-gray-500 dark:text-gray-400">Aún no hay entradas en la bitácora.</p>}
      </div>
    </div>
  )
}

function PreInvoiceTab({
  projectId,
  clientHasRnc,
  onConverted,
}: {
  projectId: number
  clientHasRnc: boolean
  onConverted: () => void
}) {
  const queryClient = useQueryClient()
  const isAdmin = useAuthStore((s) => s.user?.role === 'admin')
  const [ncfTypeByPreInvoice, setNcfTypeByPreInvoice] = useState<Record<number, NcfType>>({})
  const { data: products } = useProducts()
  const [showForm, setShowForm] = useState(false)
  const [notes, setNotes] = useState('')
  const [items, setItems] = useState<LineItemInput[]>([])

  const { data: quotes } = useQuery({
    queryKey: ['quotes', projectId],
    queryFn: async () => (await api.get<Quote[]>(`/projects/${projectId}/quotes`)).data,
  })
  const { data: preInvoices } = useQuery({
    queryKey: ['pre-invoices', projectId],
    queryFn: async () => (await api.get<PreInvoice[]>(`/projects/${projectId}/pre-invoices`)).data,
  })

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['pre-invoices', projectId] })
  }

  const createPreInvoice = useMutation({
    mutationFn: async () => (await api.post(`/projects/${projectId}/pre-invoices`, { notes, items })).data,
    onSuccess: () => {
      invalidate()
      setShowForm(false)
      setNotes('')
      setItems([])
    },
  })

  function ncfTypeFor(preInvoiceId: number): NcfType {
    return ncfTypeByPreInvoice[preInvoiceId] ?? (clientHasRnc ? 'B01' : 'B02')
  }

  const generate = useMutation({
    mutationFn: async (quoteId: number) => (await api.post(`/quotes/${quoteId}/generate-pre-invoice`)).data,
    onSuccess: invalidate,
  })
  const [convertError, setConvertError] = useState<string | null>(null)
  const convert = useMutation({
    mutationFn: async (preInvoiceId: number) =>
      (
        await api.post(`/pre-invoices/${preInvoiceId}/convert-to-invoice`, {
          ncf_type: ncfTypeFor(preInvoiceId),
        })
      ).data,
    onSuccess: () => {
      setConvertError(null)
      invalidate()
      onConverted()
    },
    onError: (err: any) => setConvertError(err?.response?.data?.detail ?? 'Error al convertir a factura'),
  })

  const usedQuoteIds = new Set(preInvoices?.map((p) => p.source_quote_id).filter(Boolean))
  const approvedWithoutPreInvoice = quotes?.filter((q) => q.status === 'aprobada' && !usedQuoteIds.has(q.id)) ?? []

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2 md:max-w-2xl">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Documento previo — normalmente generado desde una cotización aprobada, o creado a mano si hace
          falta facturar algo sin pasar por ese flujo.
        </p>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="shrink-0 rounded-full bg-brand-blue px-4 py-2 text-sm font-medium text-white"
        >
          {showForm ? 'Cancelar' : '+ Nueva'}
        </button>
      </div>

      {showForm && (
        <Card className="space-y-3">
          <Field label="Notas">
            <Textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </Field>
          <LineItemsEditor items={items} onChange={setItems} products={products ?? []} mode="quote" />
          <Button onClick={() => createPreInvoice.mutate()} disabled={createPreInvoice.isPending || items.length === 0}>
            {createPreInvoice.isPending ? 'Guardando…' : 'Guardar prefactura'}
          </Button>
        </Card>
      )}

      {approvedWithoutPreInvoice.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Cotizaciones aprobadas sin prefactura</p>
          {approvedWithoutPreInvoice.map((quote) => (
            <Card key={quote.id} className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{quote.code}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{formatDOP(quote.total)}</p>
              </div>
              <Button
                variant="secondary"
                className="!w-auto px-4"
                onClick={() => generate.mutate(quote.id)}
                disabled={generate.isPending}
              >
                Generar prefactura
              </Button>
            </Card>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 items-start gap-3 md:grid-cols-2 xl:grid-cols-3">
        {preInvoices?.map((pfc) => (
          <Card key={pfc.id}>
            <div className="flex items-center justify-between">
              <p className="font-medium text-gray-900 dark:text-gray-100">{pfc.code}</p>
              <Badge tone={pfc.status === 'facturada' ? 'green' : 'blue'}>
                {pfc.status === 'facturada' ? 'Facturada' : 'Pendiente'}
              </Badge>
            </div>
            {pfc.notes && <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{pfc.notes}</p>}
            <ul className="mt-2 space-y-1 text-sm text-gray-600 dark:text-gray-400">
              {pfc.items.map((item) => (
                <li key={item.id}>
                  <div className="flex justify-between">
                    <span>
                      {item.quantity} × {item.description}
                    </span>
                    <span>{formatDOP(item.subtotal)}</span>
                  </div>
                  {item.note && <p className="text-xs italic text-gray-400 dark:text-gray-500">{item.note}</p>}
                </li>
              ))}
            </ul>
            <div className="mt-2 space-y-1 rounded-xl bg-brand-gray p-3 text-sm dark:bg-gray-800">
              <div className="flex justify-between text-gray-500 dark:text-gray-400">
                <span>Subtotal</span>
                <span>{formatDOP(pfc.subtotal)}</span>
              </div>
              <div className="flex justify-between text-gray-500 dark:text-gray-400">
                <span>ITBIS (18%)</span>
                <span>{formatDOP(pfc.itbis)}</span>
              </div>
              <div className="flex justify-between font-semibold text-gray-900 dark:text-gray-100">
                <span>Total</span>
                <span>{formatDOP(pfc.total)}</span>
              </div>
            </div>
            {pfc.status === 'pendiente' && isAdmin && (
              <div className="mt-3 space-y-2 border-t border-gray-100 pt-3 dark:border-gray-800">
                <Field label="Tipo de NCF">
                  <select
                    className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
                    value={ncfTypeFor(pfc.id)}
                    onChange={(e) =>
                      setNcfTypeByPreInvoice((prev) => ({ ...prev, [pfc.id]: e.target.value as NcfType }))
                    }
                  >
                    {NCF_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {NCF_TYPE_LABELS[t]}
                      </option>
                    ))}
                  </select>
                </Field>
                {convertError && <p className="text-sm text-red-600 dark:text-red-400">{convertError}</p>}
                <Button onClick={() => convert.mutate(pfc.id)} disabled={convert.isPending}>
                  {convert.isPending ? 'Convirtiendo…' : 'Convertir a factura'}
                </Button>
              </div>
            )}
            {pfc.status === 'pendiente' && !isAdmin && (
              <p className="mt-3 text-xs text-gray-400">Solo un administrador puede convertir a factura.</p>
            )}
          </Card>
        ))}
        {preInvoices?.length === 0 && <p className="text-sm text-gray-500 dark:text-gray-400">Aún no hay prefacturas.</p>}
      </div>
    </div>
  )
}

function InvoiceTab({ projectId }: { projectId: number }) {
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const { data: invoices } = useQuery({
    queryKey: ['invoices', projectId],
    queryFn: async () => (await api.get<Invoice[]>(`/projects/${projectId}/invoices`)).data,
  })
  const { data: survey } = useQuery({
    queryKey: ['survey', projectId],
    queryFn: async () => (await api.get<Survey>(`/projects/${projectId}/survey`)).data,
  })

  const hasSurveyReference =
    survey && (survey.notes || survey.observations || survey.assets.some((a) => a.kind === 'photo'))

  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-500 dark:text-gray-400">Facturas emitidas (solo lectura).</p>

      {hasSurveyReference && (
        <Card className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
            Referencia del levantamiento
          </p>
          {survey?.notes && <p className="text-sm text-gray-700 dark:text-gray-300">{survey.notes}</p>}
          {survey?.observations && <p className="text-sm text-gray-700 dark:text-gray-300">{survey.observations}</p>}
          {survey && survey.assets.filter((a) => a.kind === 'photo').length > 0 && (
            <div className="grid grid-cols-4 gap-2">
              {survey.assets
                .filter((a) => a.kind === 'photo')
                .map((asset) => (
                  <img
                    key={asset.id}
                    src={`/${asset.file_path.replace(/^.*uploads\//, 'uploads/')}`}
                    className="aspect-square rounded-lg object-cover"
                    alt="Foto de levantamiento"
                  />
                ))}
            </div>
          )}
        </Card>
      )}

      <div className="grid grid-cols-1 items-start gap-3 md:grid-cols-2 xl:grid-cols-3">
        {invoices?.map((invoice) => (
          <InvoiceCard
            key={invoice.id}
            invoice={invoice}
            expanded={expandedId === invoice.id}
            onToggle={() => setExpandedId(expandedId === invoice.id ? null : invoice.id)}
          />
        ))}
      </div>
      {invoices?.length === 0 && <p className="text-sm text-gray-500 dark:text-gray-400">Aún no hay facturas.</p>}
    </div>
  )
}

function InvoiceCard({ invoice, expanded, onToggle }: { invoice: Invoice; expanded: boolean; onToggle: () => void }) {
  const { data: history } = useQuery({
    queryKey: ['invoice-history', invoice.id],
    queryFn: async () => (await api.get<InvoiceHistoryEntry[]>(`/invoices/${invoice.id}/history`)).data,
    enabled: expanded,
  })

  return (
    <Card>
      <button className="w-full text-left" onClick={onToggle}>
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-gray-900 dark:text-gray-100">{invoice.code}</p>
            {invoice.ncf && <p className="text-xs text-gray-500 dark:text-gray-400">NCF: {invoice.ncf}</p>}
          </div>
          <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">{formatDOP(invoice.total)}</p>
        </div>
      </button>
      {expanded && (
        <div className="mt-3 space-y-3 border-t border-gray-100 pt-3 dark:border-gray-800">
          <ul className="space-y-1 text-sm text-gray-600 dark:text-gray-400">
            {invoice.items.map((item) => (
              <li key={item.id}>
                <div className="flex justify-between">
                  <span>
                    {item.quantity} × {item.description}
                  </span>
                  <span>{formatDOP(item.subtotal)}</span>
                </div>
                {item.note && <p className="text-xs italic text-gray-400 dark:text-gray-500">{item.note}</p>}
              </li>
            ))}
          </ul>
          <div className="space-y-1 rounded-xl bg-brand-gray p-3 text-sm dark:bg-gray-800">
            <div className="flex justify-between text-gray-500 dark:text-gray-400">
              <span>Subtotal</span>
              <span>{formatDOP(invoice.subtotal)}</span>
            </div>
            <div className="flex justify-between text-gray-500 dark:text-gray-400">
              <span>ITBIS (18%)</span>
              <span>{formatDOP(invoice.itbis)}</span>
            </div>
            <div className="flex justify-between font-semibold text-gray-900 dark:text-gray-100">
              <span>Total</span>
              <span>{formatDOP(invoice.total)}</span>
            </div>
          </div>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Factura (con precios)</p>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  className="!w-auto flex-1 px-3 py-2 text-sm"
                  onClick={() => viewFile(`/invoices/${invoice.id}/pdf`)}
                >
                  Ver
                </Button>
                <Button
                  variant="secondary"
                  className="!w-auto flex-1 px-3 py-2 text-sm"
                  onClick={() => downloadFile(`/invoices/${invoice.id}/pdf`, `${invoice.code}.pdf`)}
                >
                  Descargar
                </Button>
              </div>
            </div>
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Detalle de trabajo (sin precios)</p>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  className="!w-auto flex-1 px-3 py-2 text-sm"
                  onClick={() => viewFile(`/invoices/${invoice.id}/pdf?variant=global`)}
                >
                  Ver
                </Button>
                <Button
                  variant="secondary"
                  className="!w-auto flex-1 px-3 py-2 text-sm"
                  onClick={() =>
                    downloadFile(`/invoices/${invoice.id}/pdf?variant=global`, `${invoice.code}-global.pdf`)
                  }
                >
                  Descargar
                </Button>
              </div>
            </div>
          </div>
          {history && history.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">Historial</p>
              <ul className="space-y-1 text-xs text-gray-500 dark:text-gray-400">
                {history.map((h) => (
                  <li key={h.id}>
                    {new Date(h.created_at).toLocaleString('es-DO')} — {QUOTE_HISTORY_LABELS[h.action] ?? h.action}
                    {h.note ? `: ${h.note}` : ''}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </Card>
  )
}

function ExtensionsTab({ projectId }: { projectId: number }) {
  const queryClient = useQueryClient()
  const { data: extensions } = useQuery({
    queryKey: ['extensions', projectId],
    queryFn: async () => (await api.get<Extension[]>(`/projects/${projectId}/extensions`)).data,
  })
  const { data: quotes } = useQuery({
    queryKey: ['quotes', projectId],
    queryFn: async () => (await api.get<Quote[]>(`/projects/${projectId}/quotes`)).data,
  })

  const [showForm, setShowForm] = useState(false)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [quoteId, setQuoteId] = useState('')

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['extensions', projectId] })
  }

  const createExtension = useMutation({
    mutationFn: async () =>
      (
        await api.post(`/projects/${projectId}/extensions`, {
          title,
          description: description || null,
          quote_id: quoteId ? Number(quoteId) : null,
        })
      ).data,
    onSuccess: () => {
      invalidate()
      setShowForm(false)
      setTitle('')
      setDescription('')
      setQuoteId('')
    },
  })

  const updateStatus = useMutation({
    mutationFn: async ({ id, status }: { id: number; status: ExtensionStatus }) =>
      (await api.put(`/extensions/${id}/status`, { status })).data,
    onSuccess: invalidate,
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between md:max-w-2xl">
        <p className="text-sm text-gray-500 dark:text-gray-400">Siempre pertenecen a este proyecto.</p>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-full bg-brand-blue px-4 py-2 text-sm font-medium text-white"
        >
          {showForm ? 'Cancelar' : '+ Nueva'}
        </button>
      </div>

      {showForm && (
        <Card className="space-y-3">
          <Field label="Título">
            <input
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </Field>
          <Field label="Descripción">
            <Textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
          </Field>
          <Field label="Cotización relacionada (opcional)">
            <select
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
              value={quoteId}
              onChange={(e) => setQuoteId(e.target.value)}
            >
              <option value="">Sin costo asociado</option>
              {quotes?.map((q) => (
                <option key={q.id} value={q.id}>
                  {q.code} · {formatDOP(q.total)}
                </option>
              ))}
            </select>
          </Field>
          <Button onClick={() => createExtension.mutate()} disabled={createExtension.isPending || !title}>
            {createExtension.isPending ? 'Guardando…' : 'Guardar ampliación'}
          </Button>
        </Card>
      )}

      <div className="grid grid-cols-1 items-start gap-3 md:grid-cols-2 xl:grid-cols-3">
        {extensions?.map((ext) => (
          <Card key={ext.id}>
            <div className="flex items-center justify-between">
              <p className="font-medium text-gray-900 dark:text-gray-100">{ext.code}</p>
              <Badge tone={ext.status === 'aprobada' ? 'green' : ext.status === 'rechazada' ? 'red' : 'blue'}>
                {EXTENSION_STATUS_LABELS[ext.status]}
              </Badge>
            </div>
            <p className="mt-1 text-sm font-medium text-gray-800 dark:text-gray-200">{ext.title}</p>
            {ext.description && <p className="text-sm text-gray-500 dark:text-gray-400">{ext.description}</p>}
            {ext.status === 'pendiente' && (
              <div className="mt-3 flex gap-2">
                <Button onClick={() => updateStatus.mutate({ id: ext.id, status: 'aprobada' })} disabled={updateStatus.isPending}>
                  Aprobar
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => updateStatus.mutate({ id: ext.id, status: 'rechazada' })}
                  disabled={updateStatus.isPending}
                >
                  Rechazar
                </Button>
              </div>
            )}
          </Card>
        ))}
        {extensions?.length === 0 && <p className="text-sm text-gray-500 dark:text-gray-400">Aún no hay ampliaciones.</p>}
      </div>
    </div>
  )
}

const TICKET_STATUS_TONE: Record<TicketStatus, 'blue' | 'amber' | 'green' | 'gray'> = {
  abierto: 'blue',
  en_proceso: 'amber',
  resuelto: 'green',
  cerrado: 'gray',
}

function TicketsTab({ projectId }: { projectId: number }) {
  const queryClient = useQueryClient()
  const { data: tickets } = useQuery({
    queryKey: ['tickets', projectId],
    queryFn: async () => (await api.get<Ticket[]>(`/projects/${projectId}/tickets`)).data,
  })
  const { data: technicians } = useQuery({
    queryKey: ['technicians'],
    queryFn: async () => (await api.get<Technician[]>('/users/technicians')).data,
  })

  const [showForm, setShowForm] = useState(false)
  const [problem, setProblem] = useState('')
  const [technicianId, setTechnicianId] = useState<number | ''>('')
  const [expandedId, setExpandedId] = useState<number | null>(null)

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['tickets', projectId] })
  }

  const createTicket = useMutation({
    mutationFn: async () =>
      (
        await api.post(`/projects/${projectId}/tickets`, {
          problem,
          technician_id: technicianId || null,
        })
      ).data,
    onSuccess: () => {
      invalidate()
      setShowForm(false)
      setProblem('')
      setTechnicianId('')
    },
  })

  function technicianName(id: number | null) {
    return technicians?.find((t) => t.id === id)?.name
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between md:max-w-2xl">
        <p className="text-sm text-gray-500 dark:text-gray-400">Soporte técnico del proyecto.</p>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-full bg-brand-blue px-4 py-2 text-sm font-medium text-white"
        >
          {showForm ? 'Cancelar' : '+ Nuevo'}
        </button>
      </div>

      {showForm && (
        <Card className="space-y-3">
          <Field label="Problema">
            <Textarea rows={3} value={problem} onChange={(e) => setProblem(e.target.value)} />
          </Field>
          <Field label="Técnico asignado (opcional)">
            <select
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
              value={technicianId}
              onChange={(e) => setTechnicianId(e.target.value ? Number(e.target.value) : '')}
            >
              <option value="">Sin asignar</option>
              {technicians?.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </Field>
          <Button onClick={() => createTicket.mutate()} disabled={createTicket.isPending || !problem}>
            {createTicket.isPending ? 'Guardando…' : 'Crear ticket'}
          </Button>
        </Card>
      )}

      <div className="grid grid-cols-1 items-start gap-3 md:grid-cols-2 xl:grid-cols-3">
        {tickets?.map((ticket) => (
          <TicketCard
            key={ticket.id}
            ticket={ticket}
            technicians={technicians ?? []}
            technicianName={technicianName(ticket.technician_id)}
            expanded={expandedId === ticket.id}
            onToggle={() => setExpandedId(expandedId === ticket.id ? null : ticket.id)}
            onChanged={invalidate}
          />
        ))}
        {tickets?.length === 0 && <p className="text-sm text-gray-500 dark:text-gray-400">Aún no hay tickets.</p>}
      </div>
    </div>
  )
}

function TicketCard({
  ticket,
  technicians,
  technicianName,
  expanded,
  onToggle,
  onChanged,
}: {
  ticket: Ticket
  technicians: Technician[]
  technicianName: string | undefined
  expanded: boolean
  onToggle: () => void
  onChanged: () => void
}) {
  const [solution, setSolution] = useState(ticket.solution ?? '')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data: history } = useQuery({
    queryKey: ['ticket-history', ticket.id],
    queryFn: async () => (await api.get<TicketHistoryEntry[]>(`/tickets/${ticket.id}/history`)).data,
    enabled: expanded,
  })

  const updateTicket = useMutation({
    mutationFn: async (payload: { solution?: string; status?: TicketStatus; technician_id?: number | null }) =>
      (await api.put(`/tickets/${ticket.id}`, payload)).data,
    onSuccess: onChanged,
  })

  const uploadPhoto = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData()
      form.append('file', file)
      return (await api.post(`/tickets/${ticket.id}/photos`, form)).data
    },
    onSuccess: onChanged,
  })

  const deletePhoto = useMutation({
    mutationFn: async (assetId: number) => api.delete(`/tickets/${ticket.id}/photos/${assetId}`),
    onSuccess: onChanged,
  })

  return (
    <Card>
      <button className="w-full text-left" onClick={onToggle}>
        <div className="flex items-center justify-between">
          <p className="font-medium text-gray-900 dark:text-gray-100">{ticket.code}</p>
          <Badge tone={TICKET_STATUS_TONE[ticket.status]}>{TICKET_STATUS_LABELS[ticket.status]}</Badge>
        </div>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{ticket.problem}</p>
        <p className="mt-1 text-xs text-gray-400">Técnico: {technicianName ?? 'Sin asignar'}</p>
      </button>

      {expanded && (
        <div className="mt-3 space-y-3 border-t border-gray-100 pt-3 dark:border-gray-800">
          {ticket.solution && (
            <p className="text-sm text-gray-600 dark:text-gray-400">
              <span className="font-medium text-gray-800 dark:text-gray-200">Solución:</span> {ticket.solution}
            </p>
          )}

          <Field label="Técnico asignado">
            <select
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
              value={ticket.technician_id ?? ''}
              onChange={(e) =>
                updateTicket.mutate({ technician_id: e.target.value ? Number(e.target.value) : null })
              }
              disabled={updateTicket.isPending}
            >
              <option value="">Sin asignar</option>
              {technicians.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </Field>

          {ticket.status !== 'cerrado' && (
            <div className="space-y-2">
              <Field label="Solución">
                <Textarea rows={2} value={solution} onChange={(e) => setSolution(e.target.value)} />
              </Field>
              <div className="flex flex-wrap gap-2">
                {ticket.status === 'abierto' && (
                  <Button
                    variant="secondary"
                    className="!w-auto px-4"
                    onClick={() => updateTicket.mutate({ status: 'en_proceso' })}
                    disabled={updateTicket.isPending}
                  >
                    Tomar ticket
                  </Button>
                )}
                <Button
                  className="!w-auto px-4"
                  onClick={() => updateTicket.mutate({ solution, status: 'resuelto' })}
                  disabled={updateTicket.isPending || !solution}
                >
                  Marcar resuelto
                </Button>
                {ticket.status === 'resuelto' && (
                  <Button
                    variant="ghost"
                    className="!w-auto px-4"
                    onClick={() => updateTicket.mutate({ status: 'cerrado' })}
                    disabled={updateTicket.isPending}
                  >
                    Cerrar
                  </Button>
                )}
              </div>
            </div>
          )}

          <div className="space-y-2">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Fotos de evidencia</p>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) uploadPhoto.mutate(file)
                e.target.value = ''
              }}
            />
            <div className="grid grid-cols-3 gap-2">
              {ticket.assets.map((asset) => (
                <div key={asset.id} className="relative">
                  <img
                    src={`/${asset.file_path.replace(/^.*uploads\//, 'uploads/')}`}
                    className="aspect-square rounded-xl object-cover"
                    alt="Foto de evidencia del ticket"
                  />
                  <button
                    type="button"
                    onClick={() => deletePhoto.mutate(asset.id)}
                    disabled={deletePhoto.isPending}
                    aria-label="Borrar foto"
                    className="absolute right-1 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-black/60 text-xs text-white"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
            <Button variant="secondary" onClick={() => fileInputRef.current?.click()} disabled={uploadPhoto.isPending}>
              {uploadPhoto.isPending ? 'Subiendo…' : '📷 Agregar foto'}
            </Button>
          </div>

          {history && history.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">Historial</p>
              <ul className="space-y-1 text-xs text-gray-500 dark:text-gray-400">
                {history.map((h) => (
                  <li key={h.id}>
                    {new Date(h.created_at).toLocaleString('es-DO')} — {TICKET_STATUS_LABELS[h.action as TicketStatus] ?? h.action}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </Card>
  )
}
