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
  Quote,
  QuoteHistoryEntry,
  StageName,
  Survey,
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
            className={listening ? 'bg-red-100 text-red-600' : ''}
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

  const { data: project } = useQuery({
    queryKey: ['projects', id],
    queryFn: async () => (await api.get<ProjectDetailType>(`/projects/${id}`)).data,
  })

  if (!project) return <p className="py-4 text-sm text-gray-500">Cargando…</p>

  return (
    <div className="space-y-4 py-4">
      <button onClick={() => navigate(-1)} className="text-sm text-brand-blue">
        ← Volver
      </button>

      <Card>
        <div className="flex items-center justify-between">
          <p className="text-lg font-semibold text-gray-900">{project.code}</p>
          {tab !== 'tickets' && <Badge>{PROJECT_STATUS_LABELS[project.status] ?? project.status}</Badge>}
        </div>
        <p className="mt-1 text-sm text-gray-500">{project.client.name}</p>
      </Card>

      <div className="flex gap-2 overflow-x-auto rounded-2xl bg-brand-gray p-1">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`shrink-0 whitespace-nowrap rounded-xl px-4 py-2 text-sm font-medium ${
              tab === t.key ? 'bg-white text-brand-blue shadow-sm' : 'text-gray-500'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'info' && <InfoTab project={project} />}
      {tab === 'levantamiento' && <LevantamientoTab projectId={project.id} />}
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

function InfoTab({ project }: { project: ProjectDetailType }) {
  return (
    <Card className="space-y-2 text-sm text-gray-600">
      <p>
        <span className="font-medium text-gray-800">Cliente:</span> {project.client.name}
        {project.client.company ? ` (${project.client.company})` : ''}
      </p>
      <p>
        <span className="font-medium text-gray-800">Fecha:</span> {project.date}
      </p>
      <p>
        <span className="font-medium text-gray-800">Estado:</span> {PROJECT_STATUS_LABELS[project.status] ?? project.status}
      </p>
      {project.description && (
        <p>
          <span className="font-medium text-gray-800">Descripción:</span> {project.description}
        </p>
      )}
    </Card>
  )
}

function LevantamientoTab({ projectId }: { projectId: number }) {
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

      <Card className="space-y-3">
        <p className="font-medium text-gray-800">Fotos y audio</p>
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
          <p className="font-medium text-gray-800">Resumen con IA</p>
          <Button
            variant="secondary"
            className="w-auto px-4"
            onClick={() => aiSummarize.mutate()}
            disabled={aiSummarize.isPending}
          >
            {aiSummarize.isPending ? 'Organizando…' : '🤖 Organizar con IA'}
          </Button>
        </div>
        {aiError && <p className="text-sm text-red-600">{aiError}</p>}
        {survey?.ai_summary && <p className="whitespace-pre-line text-sm text-gray-700">{survey.ai_summary}</p>}
        {!survey?.ai_summary && !aiError && (
          <p className="text-sm text-gray-500">
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
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">Borrador generado con IA a partir del levantamiento.</p>
        <Button
          variant="secondary"
          className="w-auto shrink-0 px-4"
          onClick={() => aiDraft.mutate()}
          disabled={aiDraft.isPending}
        >
          {aiDraft.isPending ? 'Generando…' : '🤖 Generar propuesta'}
        </Button>
      </div>
      {aiError && <p className="text-sm text-red-600">{aiError}</p>}
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
  const aiSuggest = useMutation({
    mutationFn: async () => (await api.post<BudgetSuggestionOut>(`/projects/${projectId}/budget-suggestions`)).data,
    onSuccess: (data) => {
      setAiError(null)
      setItems(data.items.map((item) => ({ ...item })))
    },
    onError: (error: any) => setAiError(error?.response?.data?.detail ?? 'Error al sugerir materiales'),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">Documento resumido — solo muestra el total.</p>
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
          {aiError && <p className="text-sm text-red-600">{aiError}</p>}
          <LineItemsEditor items={items} onChange={setItems} products={products ?? []} mode="budget" />
          <Button onClick={() => createBudget.mutate()} disabled={createBudget.isPending || items.length === 0}>
            {createBudget.isPending ? 'Guardando…' : 'Guardar presupuesto'}
          </Button>
        </Card>
      )}

      <div className="space-y-3">
        {budgets?.map((budget) => (
          <Card key={budget.id}>
            <div className="flex items-center justify-between">
              <p className="font-medium text-gray-900">{budget.code}</p>
              <p className="text-sm font-semibold text-gray-800">{formatDOP(budget.total)}</p>
            </div>
            {budget.notes && <p className="mt-1 text-sm text-gray-500">{budget.notes}</p>}
            <ul className="mt-2 list-inside list-disc text-sm text-gray-600">
              {budget.items.map((item) => (
                <li key={item.id}>
                  {item.quantity} × {item.description}
                </li>
              ))}
            </ul>
            <Button
              variant="secondary"
              className="mt-3"
              onClick={() => convertToQuote.mutate(budget.id)}
              disabled={convertToQuote.isPending}
            >
              {convertToQuote.isPending ? 'Convirtiendo…' : 'Convertir a cotización →'}
            </Button>
          </Card>
        ))}
        {budgets?.length === 0 && <p className="text-sm text-gray-500">Aún no hay presupuestos.</p>}
      </div>
    </div>
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
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">Documento detallado con ITBIS 18%.</p>
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

      <div className="space-y-3">
        {quotes?.map((quote) => (
          <QuoteCard
            key={quote.id}
            quote={quote}
            expanded={expandedId === quote.id}
            onToggle={() => setExpandedId(expandedId === quote.id ? null : quote.id)}
            projectId={projectId}
          />
        ))}
        {quotes?.length === 0 && <p className="text-sm text-gray-500">Aún no hay cotizaciones.</p>}
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
}: {
  quote: Quote
  expanded: boolean
  onToggle: () => void
  projectId: number
}) {
  const queryClient = useQueryClient()
  const [reason, setReason] = useState('')
  const [showRejectForm, setShowRejectForm] = useState(false)

  const { data: history } = useQuery({
    queryKey: ['quote-history', quote.id],
    queryFn: async () => (await api.get<QuoteHistoryEntry[]>(`/quotes/${quote.id}/history`)).data,
    enabled: expanded,
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

  return (
    <Card>
      <button className="w-full text-left" onClick={onToggle}>
        <div className="flex items-center justify-between">
          <p className="font-medium text-gray-900">{quote.code}</p>
          <Badge tone={STATUS_TONE[quote.status]}>{QUOTE_STATUS_LABELS[quote.status]}</Badge>
        </div>
        <p className="mt-1 text-sm text-gray-500">{formatDOP(quote.total)}</p>
      </button>

      {expanded && (
        <div className="mt-3 space-y-3 border-t border-gray-100 pt-3">
          <ul className="space-y-1 text-sm text-gray-600">
            {quote.items.map((item) => (
              <li key={item.id} className="flex justify-between">
                <span>
                  {item.quantity} × {item.description}
                </span>
                <span>{formatDOP(item.subtotal)}</span>
              </li>
            ))}
          </ul>
          <div className="space-y-1 rounded-xl bg-brand-gray p-3 text-sm">
            <div className="flex justify-between text-gray-500">
              <span>Subtotal</span>
              <span>{formatDOP(quote.subtotal)}</span>
            </div>
            <div className="flex justify-between text-gray-500">
              <span>ITBIS (18%)</span>
              <span>{formatDOP(quote.itbis)}</span>
            </div>
            <div className="flex justify-between font-semibold text-gray-900">
              <span>Total</span>
              <span>{formatDOP(quote.total)}</span>
            </div>
          </div>

          <Button
            variant="secondary"
            onClick={() => downloadFile(`/quotes/${quote.id}/pdf`, `${quote.code}.pdf`)}
          >
            Descargar PDF
          </Button>

          {quote.status === 'pendiente' && (
            <div className="flex gap-2">
              <Button onClick={() => approve.mutate()} disabled={approve.isPending}>
                Aprobar
              </Button>
              <Button variant="secondary" onClick={() => setShowRejectForm((v) => !v)}>
                Rechazar
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
              <p className="mb-1 text-xs font-medium text-gray-500">Historial</p>
              <ul className="space-y-1 text-xs text-gray-500">
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

  const createMaterial = useMutation({
    mutationFn: async () =>
      (
        await api.post(`/projects/${projectId}/materials`, {
          product_id: productId ? Number(productId) : null,
          description,
          quantity,
        })
      ).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['materials', projectId] })
      setShowForm(false)
      setProductId('')
      setDescription('')
      setQuantity(1)
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
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">Lista inteligente generada al aprobar cotizaciones.</p>
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
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base"
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
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </Field>
          <Field label="Cantidad">
            <input
              type="number"
              min="0"
              step="0.01"
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base"
              value={quantity}
              onChange={(e) => setQuantity(Number(e.target.value))}
            />
          </Field>
          <Button onClick={() => createMaterial.mutate()} disabled={createMaterial.isPending || !description}>
            {createMaterial.isPending ? 'Guardando…' : 'Agregar material'}
          </Button>
        </Card>
      )}

      <div>
        <p className="mb-2 text-sm font-semibold text-gray-900">
          Lista de compra ({purchaseList.length})
        </p>
        <div className="space-y-2">
          {purchaseList.map((m) => (
            <MaterialRow key={m.id} material={m} onStatusChange={(status) => updateStatus.mutate({ id: m.id, status })} />
          ))}
          {purchaseList.length === 0 && <p className="text-sm text-gray-500">Nada pendiente de comprar.</p>}
        </div>
      </div>

      {others.length > 0 && (
        <div>
          <p className="mb-2 text-sm font-semibold text-gray-900">Otros materiales</p>
          <div className="space-y-2">
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
        <p className="text-sm font-medium text-gray-900">
          {material.quantity} × {material.description}
        </p>
        <Badge tone={material.status === 'pendiente_compra' ? 'amber' : material.status === 'instalado' ? 'green' : 'gray'}>
          {MATERIAL_STATUS_LABELS[material.status]}
        </Badge>
      </div>
      <select
        className="rounded-xl border border-gray-200 bg-white px-2 py-2 text-xs"
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

  if (!execution) return <p className="text-sm text-gray-500">Cargando…</p>

  const allDone = execution.stages.every((s) => s.completed)
  const anyDone = execution.stages.some((s) => s.completed)

  return (
    <div className="space-y-4">
      <Card>
        <div className="mb-2 flex items-center justify-between">
          <p className="text-sm font-medium text-gray-700">Avance</p>
          <p className="text-sm font-semibold text-gray-900">{execution.progress_percent}%</p>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-brand-gray">
          <div className="h-full rounded-full bg-brand-blue" style={{ width: `${execution.progress_percent}%` }} />
        </div>
      </Card>

      <div className="space-y-2">
        {execution.stages.map((stage) => (
          <Card key={stage.id} className="flex items-center gap-3">
            <span
              className={`flex h-8 w-8 items-center justify-center rounded-full text-sm ${
                stage.completed ? 'bg-green-100 text-green-700' : 'bg-brand-gray text-gray-400'
              }`}
            >
              {stage.completed ? '✓' : stage.order + 1}
            </span>
            <span className={`text-sm font-medium ${stage.completed ? 'text-gray-900' : 'text-gray-500'}`}>
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

      <div className="space-y-3">
        {entries?.map((entry) => (
          <Card key={entry.id}>
            <p className="text-xs text-gray-400">{entry.entry_date}</p>
            <p className="mt-1 text-sm text-gray-800">{entry.comment}</p>
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
        {entries?.length === 0 && <p className="text-sm text-gray-500">Aún no hay entradas en la bitácora.</p>}
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
      <p className="text-sm text-gray-500">Documento previo generado desde una cotización aprobada.</p>

      {approvedWithoutPreInvoice.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-700">Cotizaciones aprobadas sin prefactura</p>
          {approvedWithoutPreInvoice.map((quote) => (
            <Card key={quote.id} className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-900">{quote.code}</p>
                <p className="text-xs text-gray-500">{formatDOP(quote.total)}</p>
              </div>
              <Button
                variant="secondary"
                className="w-auto px-4"
                onClick={() => generate.mutate(quote.id)}
                disabled={generate.isPending}
              >
                Generar prefactura
              </Button>
            </Card>
          ))}
        </div>
      )}

      <div className="space-y-3">
        {preInvoices?.map((pfc) => (
          <Card key={pfc.id}>
            <div className="flex items-center justify-between">
              <p className="font-medium text-gray-900">{pfc.code}</p>
              <Badge tone={pfc.status === 'facturada' ? 'green' : 'blue'}>
                {pfc.status === 'facturada' ? 'Facturada' : 'Pendiente'}
              </Badge>
            </div>
            <ul className="mt-2 space-y-1 text-sm text-gray-600">
              {pfc.items.map((item) => (
                <li key={item.id} className="flex justify-between">
                  <span>
                    {item.quantity} × {item.description}
                  </span>
                  <span>{formatDOP(item.subtotal)}</span>
                </li>
              ))}
            </ul>
            <div className="mt-2 space-y-1 rounded-xl bg-brand-gray p-3 text-sm">
              <div className="flex justify-between text-gray-500">
                <span>Subtotal</span>
                <span>{formatDOP(pfc.subtotal)}</span>
              </div>
              <div className="flex justify-between text-gray-500">
                <span>ITBIS (18%)</span>
                <span>{formatDOP(pfc.itbis)}</span>
              </div>
              <div className="flex justify-between font-semibold text-gray-900">
                <span>Total</span>
                <span>{formatDOP(pfc.total)}</span>
              </div>
            </div>
            {pfc.status === 'pendiente' && isAdmin && (
              <div className="mt-3 space-y-2 border-t border-gray-100 pt-3">
                <Field label="Tipo de NCF">
                  <select
                    className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base"
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
                {convertError && <p className="text-sm text-red-600">{convertError}</p>}
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
        {preInvoices?.length === 0 && <p className="text-sm text-gray-500">Aún no hay prefacturas.</p>}
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
      <p className="text-sm text-gray-500">Facturas emitidas (solo lectura).</p>

      {hasSurveyReference && (
        <Card className="space-y-2">
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
            Referencia del levantamiento
          </p>
          {survey?.notes && <p className="text-sm text-gray-700">{survey.notes}</p>}
          {survey?.observations && <p className="text-sm text-gray-700">{survey.observations}</p>}
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

      {invoices?.map((invoice) => (
        <InvoiceCard
          key={invoice.id}
          invoice={invoice}
          expanded={expandedId === invoice.id}
          onToggle={() => setExpandedId(expandedId === invoice.id ? null : invoice.id)}
        />
      ))}
      {invoices?.length === 0 && <p className="text-sm text-gray-500">Aún no hay facturas.</p>}
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
            <p className="font-medium text-gray-900">{invoice.code}</p>
            {invoice.ncf && <p className="text-xs text-gray-500">NCF: {invoice.ncf}</p>}
          </div>
          <p className="text-sm font-semibold text-gray-800">{formatDOP(invoice.total)}</p>
        </div>
      </button>
      {expanded && (
        <div className="mt-3 space-y-3 border-t border-gray-100 pt-3">
          <ul className="space-y-1 text-sm text-gray-600">
            {invoice.items.map((item) => (
              <li key={item.id} className="flex justify-between">
                <span>
                  {item.quantity} × {item.description}
                </span>
                <span>{formatDOP(item.subtotal)}</span>
              </li>
            ))}
          </ul>
          <div className="space-y-1 rounded-xl bg-brand-gray p-3 text-sm">
            <div className="flex justify-between text-gray-500">
              <span>Subtotal</span>
              <span>{formatDOP(invoice.subtotal)}</span>
            </div>
            <div className="flex justify-between text-gray-500">
              <span>ITBIS (18%)</span>
              <span>{formatDOP(invoice.itbis)}</span>
            </div>
            <div className="flex justify-between font-semibold text-gray-900">
              <span>Total</span>
              <span>{formatDOP(invoice.total)}</span>
            </div>
          </div>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-gray-500">Factura (con precios)</p>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  className="w-auto flex-1 px-3 py-2 text-sm"
                  onClick={() => viewFile(`/invoices/${invoice.id}/pdf`)}
                >
                  Ver
                </Button>
                <Button
                  variant="secondary"
                  className="w-auto flex-1 px-3 py-2 text-sm"
                  onClick={() => downloadFile(`/invoices/${invoice.id}/pdf`, `${invoice.code}.pdf`)}
                >
                  Descargar
                </Button>
              </div>
            </div>
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-gray-500">Detalle de trabajo (sin precios)</p>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  className="w-auto flex-1 px-3 py-2 text-sm"
                  onClick={() => viewFile(`/invoices/${invoice.id}/pdf?variant=global`)}
                >
                  Ver
                </Button>
                <Button
                  variant="secondary"
                  className="w-auto flex-1 px-3 py-2 text-sm"
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
              <p className="mb-1 text-xs font-medium text-gray-500">Historial</p>
              <ul className="space-y-1 text-xs text-gray-500">
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
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">Siempre pertenecen a este proyecto.</p>
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
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </Field>
          <Field label="Descripción">
            <Textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
          </Field>
          <Field label="Cotización relacionada (opcional)">
            <select
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base"
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

      <div className="space-y-3">
        {extensions?.map((ext) => (
          <Card key={ext.id}>
            <div className="flex items-center justify-between">
              <p className="font-medium text-gray-900">{ext.code}</p>
              <Badge tone={ext.status === 'aprobada' ? 'green' : ext.status === 'rechazada' ? 'red' : 'blue'}>
                {EXTENSION_STATUS_LABELS[ext.status]}
              </Badge>
            </div>
            <p className="mt-1 text-sm font-medium text-gray-800">{ext.title}</p>
            {ext.description && <p className="text-sm text-gray-500">{ext.description}</p>}
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
        {extensions?.length === 0 && <p className="text-sm text-gray-500">Aún no hay ampliaciones.</p>}
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

  const [showForm, setShowForm] = useState(false)
  const [problem, setProblem] = useState('')
  const [expandedId, setExpandedId] = useState<number | null>(null)

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['tickets', projectId] })
  }

  const createTicket = useMutation({
    mutationFn: async () => (await api.post(`/projects/${projectId}/tickets`, { problem })).data,
    onSuccess: () => {
      invalidate()
      setShowForm(false)
      setProblem('')
    },
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">Soporte técnico del proyecto.</p>
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
          <Button onClick={() => createTicket.mutate()} disabled={createTicket.isPending || !problem}>
            {createTicket.isPending ? 'Guardando…' : 'Crear ticket'}
          </Button>
        </Card>
      )}

      <div className="space-y-3">
        {tickets?.map((ticket) => (
          <TicketCard
            key={ticket.id}
            ticket={ticket}
            expanded={expandedId === ticket.id}
            onToggle={() => setExpandedId(expandedId === ticket.id ? null : ticket.id)}
            onChanged={invalidate}
          />
        ))}
        {tickets?.length === 0 && <p className="text-sm text-gray-500">Aún no hay tickets.</p>}
      </div>
    </div>
  )
}

function TicketCard({
  ticket,
  expanded,
  onToggle,
  onChanged,
}: {
  ticket: Ticket
  expanded: boolean
  onToggle: () => void
  onChanged: () => void
}) {
  const [solution, setSolution] = useState(ticket.solution ?? '')

  const { data: history } = useQuery({
    queryKey: ['ticket-history', ticket.id],
    queryFn: async () => (await api.get<TicketHistoryEntry[]>(`/tickets/${ticket.id}/history`)).data,
    enabled: expanded,
  })

  const updateTicket = useMutation({
    mutationFn: async (payload: { solution?: string; status?: TicketStatus }) =>
      (await api.put(`/tickets/${ticket.id}`, payload)).data,
    onSuccess: onChanged,
  })

  return (
    <Card>
      <button className="w-full text-left" onClick={onToggle}>
        <div className="flex items-center justify-between">
          <p className="font-medium text-gray-900">{ticket.code}</p>
          <Badge tone={TICKET_STATUS_TONE[ticket.status]}>{TICKET_STATUS_LABELS[ticket.status]}</Badge>
        </div>
        <p className="mt-1 text-sm text-gray-500">{ticket.problem}</p>
      </button>

      {expanded && (
        <div className="mt-3 space-y-3 border-t border-gray-100 pt-3">
          {ticket.solution && (
            <p className="text-sm text-gray-600">
              <span className="font-medium text-gray-800">Solución:</span> {ticket.solution}
            </p>
          )}

          {ticket.status !== 'cerrado' && (
            <div className="space-y-2">
              <Field label="Solución">
                <Textarea rows={2} value={solution} onChange={(e) => setSolution(e.target.value)} />
              </Field>
              <div className="flex flex-wrap gap-2">
                {ticket.status === 'abierto' && (
                  <Button
                    variant="secondary"
                    className="w-auto px-4"
                    onClick={() => updateTicket.mutate({ status: 'en_proceso' })}
                    disabled={updateTicket.isPending}
                  >
                    Tomar ticket
                  </Button>
                )}
                <Button
                  className="w-auto px-4"
                  onClick={() => updateTicket.mutate({ solution, status: 'resuelto' })}
                  disabled={updateTicket.isPending || !solution}
                >
                  Marcar resuelto
                </Button>
                {ticket.status === 'resuelto' && (
                  <Button
                    variant="ghost"
                    className="w-auto px-4"
                    onClick={() => updateTicket.mutate({ status: 'cerrado' })}
                    disabled={updateTicket.isPending}
                  >
                    Cerrar
                  </Button>
                )}
              </div>
            </div>
          )}

          {history && history.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-medium text-gray-500">Historial</p>
              <ul className="space-y-1 text-xs text-gray-500">
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
