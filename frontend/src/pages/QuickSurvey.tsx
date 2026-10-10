import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { formatDOP } from '../lib/format'
import { shrinkImage } from '../lib/imageUpload'
import { useGeolocation } from '../lib/useGeolocation'
import { assistantCallName } from '../lib/assistantName'
import { useAuthStore } from '../lib/authStore'
import { SURVEY_TYPES, surveyDescription } from '../lib/surveyTypes'
import type { Client, ClientInput, GenerateFromSurveyOut, Project, VoiceSurveyResult } from '../lib/types'
import { Button, Card, Field, Input } from '../components/ui'
import { ClientCombobox } from '../components/ClientCombobox'
import { IntakeAssistant, type IntakeData } from '../components/IntakeAssistant'
import { MapPreview } from '../components/MapPreview'
import { VoiceRecorderCard, VoiceReviewCard } from '../components/VoiceSurvey'

type Step = 'datos' | 'narrar' | 'listo'
type Fields = Pick<VoiceSurveyResult, 'notes' | 'measurements' | 'observations'>

function apiError(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail
  return typeof detail === 'string' ? detail : fallback
}

/** Levantamiento en sitio en un toque: cliente + ubicación → narrar → cotización. Pensado para
 * el celular (ver el botón "+" de la barra inferior), de pantalla completa y sin menús. */
export function QuickSurvey() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const photoInputRef = useRef<HTMLInputElement>(null)

  const [step, setStep] = useState<Step>('datos')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // --- Paso 1: cliente y ubicación ---
  const { data: clients } = useQuery({
    queryKey: ['clients'],
    queryFn: async () => (await api.get<Client[]>('/clients')).data,
  })
  const [selected, setSelected] = useState<Client | null>(null)
  const [creatingNew, setCreatingNew] = useState(false)
  // Cliente nuevo: por defecto lo llena el asistente (pregunta nombre, teléfono y tipo); también
  // se puede escribir a mano.
  const [manualEntry, setManualEntry] = useState(false)
  const [startAll, setStartAll] = useState(false)
  const user = useAuthStore((s) => s.user)
  const [newClient, setNewClient] = useState({ name: '', phone: '', company: '' })
  const [surveyType, setSurveyType] = useState('')
  const [address, setAddress] = useState('')
  const [locationUrl, setLocationUrl] = useState('')
  // En un levantamiento el técnico ya está en la obra: la ubicación se toma sola al abrir la pantalla.
  const gps = useGeolocation(setLocationUrl, { auto: true })

  // --- Paso 2: narración ---
  const [project, setProject] = useState<Project | null>(null)
  const [clientName, setClientName] = useState('')
  const [voiceResult, setVoiceResult] = useState<VoiceSurveyResult | null>(null)
  const [saved, setSaved] = useState<Fields>({ notes: '', measurements: '', observations: '' })
  const [segments, setSegments] = useState(0)
  const [photos, setPhotos] = useState(0)
  const [result, setResult] = useState<GenerateFromSurveyOut | null>(null)

  const canStart = !busy && (selected !== null || (creatingNew && newClient.name.trim().length > 0))

  /** Arranca el alta de un cliente nuevo con el asistente; `typed` es lo que ya se escribió en el buscador. */
  function startNewClient(typed: string, all = false) {
    setNewClient({ ...newClient, name: typed })
    setManualEntry(false)
    setStartAll(all)
    setCreatingNew(true)
  }

  /** `intake` llega del asistente (ya con nombre, teléfono y tipo); sin él se usan los campos. */
  async function start(intake?: IntakeData) {
    setBusy(true)
    setError(null)
    try {
      let client = selected
      const place = { address: address.trim() || null, location_url: locationUrl.trim() || null }
      const projectType = (intake?.survey_type ?? surveyType) || null
      if (creatingNew) {
        const payload: ClientInput = {
          name: (intake?.name ?? newClient.name).trim(),
          company: newClient.company.trim() || null,
          rnc: null,
          phone: (intake?.phone ?? newClient.phone).trim() || null,
          email: null,
          notes: null,
          ...place,
        }
        client = (await api.post<Client>('/clients', payload)).data
      } else if (client && ((place.address && !client.address) || (place.location_url && !client.location_url))) {
        // Cliente existente: solo se completan los datos de ubicación que le faltaban.
        const { id: _id, ...rest } = client
        client = (
          await api.put<Client>(`/clients/${client.id}`, {
            ...rest,
            address: client.address || place.address,
            location_url: client.location_url || place.location_url,
          })
        ).data
      }
      if (!client) return
      const created = (
        // La ubicación capturada queda en el proyecto (la obra), además de completar la del cliente.
        await api.post<Project>('/projects', {
          client_id: client.id,
          description: surveyDescription(projectType),
          survey_type: projectType,
          ...place,
        })
      ).data
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      setProject(created)
      setClientName(client.name)
      setStep('narrar')
    } catch (err) {
      setError(apiError(err, 'No se pudo crear el cliente o el proyecto'))
    } finally {
      setBusy(false)
    }
  }

  async function saveFields(fields: Fields): Promise<boolean> {
    if (!project) return false
    const append = (current: string, added: string) => [current.trim(), added.trim()].filter(Boolean).join('\n')
    const merged: Fields = {
      notes: append(saved.notes, fields.notes),
      measurements: append(saved.measurements, fields.measurements),
      observations: append(saved.observations, fields.observations),
    }
    setError(null)
    try {
      await api.put(`/projects/${project.id}/survey`, merged)
      setSaved(merged)
      setSegments((n) => n + 1)
      setVoiceResult(null)
      queryClient.invalidateQueries({ queryKey: ['survey', project.id] })
      return true
    } catch (err) {
      setError(apiError(err, 'No se pudo guardar el levantamiento'))
      return false
    }
  }

  async function generate() {
    if (!project) return
    setBusy(true)
    setError(null)
    try {
      const data = (await api.post<GenerateFromSurveyOut>(`/projects/${project.id}/generate-from-survey`)).data
      queryClient.invalidateQueries({ queryKey: ['quotes', project.id] })
      queryClient.invalidateQueries({ queryKey: ['budgets', project.id] })
      queryClient.invalidateQueries({ queryKey: ['engineering', project.id] })
      setResult(data)
      setStep('listo')
    } catch (err) {
      setError(apiError(err, 'No se pudo generar la cotización. Tu levantamiento quedó guardado; intenta de nuevo.'))
    } finally {
      setBusy(false)
    }
  }

  async function applyAndGenerate(fields: Fields) {
    if (await saveFields(fields)) await generate()
  }

  async function uploadPhoto(file: File) {
    if (!project) return
    setError(null)
    try {
      const form = new FormData()
      form.append('kind', 'photo')
      form.append('file', await shrinkImage(file))
      await api.post(`/projects/${project.id}/survey/assets`, form)
      setPhotos((n) => n + 1)
    } catch (err) {
      setError(apiError(err, 'No se pudo subir la foto'))
    }
  }

  function reset() {
    setStep('datos')
    setProject(null)
    setSelected(null)
    setCreatingNew(false)
    setManualEntry(false)
    setStartAll(false)
    setNewClient({ name: '', phone: '', company: '' })
    setSurveyType('')
    setAddress('')
    setLocationUrl('')
    setVoiceResult(null)
    setSaved({ notes: '', measurements: '', observations: '' })
    setSegments(0)
    setPhotos(0)
    setResult(null)
    setError(null)
  }

  // ---------------------------------------------------------------- render
  if (step === 'listo' && result && project) {
    return (
      <div className="space-y-4 py-4">
        <Card className="space-y-3 text-center">
          <p className="text-5xl">✅</p>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Cotización lista</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {clientName} · {project.code}
          </p>
          <p className="text-3xl font-bold text-brand-blue">{formatDOP(result.quote.total)}</p>
          <p className="text-xs text-gray-400">
            {result.quote.code} · queda <b>pendiente</b>: tú o el cliente la aprueban después.
          </p>
        </Card>
        {result.warnings.length > 0 && (
          <Card className="space-y-1">
            <p className="text-sm font-medium text-amber-600 dark:text-amber-400">Revisa antes de enviarla</p>
            <ul className="list-disc space-y-1 pl-5 text-sm text-gray-700 dark:text-gray-300">
              {result.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </Card>
        )}
        <Button onClick={() => navigate(`/proyectos/${project.id}`)}>Ver y ajustar la cotización</Button>
        <Button variant="secondary" onClick={reset}>
          ＋ Otro levantamiento
        </Button>
      </div>
    )
  }

  if (step === 'narrar' && project) {
    return (
      <div className="space-y-4 py-4">
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate text-lg font-semibold text-gray-900 dark:text-gray-100">{clientName}</p>
            <p className="text-xs text-gray-500">{project.code} · Levantamiento</p>
          </div>
          <button
            onClick={() => navigate(`/proyectos/${project.id}`)}
            className="shrink-0 rounded-full bg-brand-gray px-3 py-1.5 text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300"
          >
            Salir
          </button>
        </div>

        {voiceResult ? (
          <VoiceReviewCard
            projectId={project.id}
            key={voiceResult.transcript}
            result={voiceResult}
            busy={busy}
            onApply={saveFields}
            onApplyAndGenerate={applyAndGenerate}
            onDiscard={() => setVoiceResult(null)}
          />
        ) : (
          <VoiceRecorderCard large projectId={project.id} disabled={busy} onTranscribed={setVoiceResult} />
        )}

        {error && <p className="text-center text-sm text-red-600 dark:text-red-400">{error}</p>}

        {!voiceResult && (
          <div className="space-y-3">
            <input
              ref={photoInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) void uploadPhoto(file)
                e.target.value = ''
              }}
            />
            <Button variant="secondary" onClick={() => photoInputRef.current?.click()} disabled={busy}>
              📷 Tomar foto {photos > 0 && `(${photos})`}
            </Button>
            {segments > 0 && (
              <>
                <Card className="space-y-1 text-sm text-gray-600 dark:text-gray-300">
                  <p className="font-medium text-gray-800 dark:text-gray-200">
                    Guardado en el levantamiento ({segments} {segments === 1 ? 'grabación' : 'grabaciones'})
                  </p>
                  {saved.notes && <p className="line-clamp-3 whitespace-pre-line">{saved.notes}</p>}
                </Card>
                <Button onClick={generate} disabled={busy}>
                  {busy ? 'Generando cotización… (~1 min)' : '🤖 Generar cotización'}
                </Button>
              </>
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4 py-4">
      <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Nuevo levantamiento</h1>

      {!selected && !creatingNew && (
        <Card className="space-y-3 bg-blue-50 ring-blue-100 dark:bg-blue-950 dark:ring-blue-900">
          <p className="text-base font-semibold text-gray-900 dark:text-gray-100">
            🤖 Hola, {assistantCallName(user)}. Soy tu asistente de levantamientos.
          </p>
          <div className="space-y-1 text-sm text-gray-700 dark:text-gray-300">
            <p>Te puedo ayudar a:</p>
            <ul className="list-disc space-y-0.5 pl-5">
              <li>Buscar un cliente, o crearlo: te pregunto nombre, teléfono y tipo de levantamiento.</li>
              <li>Tomar tu ubicación actual y abrir el mapa.</li>
              <li>Entenderlo todo si me lo dices de una vez, hablando.</li>
              <li>Después, grabar tu levantamiento y armar la cotización.</li>
            </ul>
            <p className="pt-1 font-medium">¿Por dónde empezamos?</p>
          </div>
          <div className="grid gap-2">
            <Button onClick={() => startNewClient('', false)}>🆕 Cliente nuevo</Button>
            <Button variant="secondary" onClick={() => startNewClient('', true)}>
              🎙️ Decir todo de una vez
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                const input = document.getElementById('client-search')
                input?.scrollIntoView({ behavior: 'smooth', block: 'center' })
                input?.focus()
              }}
            >
              🔎 Buscar un cliente
            </Button>
          </div>
        </Card>
      )}

      <Card className="space-y-3">
        <p className="font-medium text-gray-800 dark:text-gray-200">1 · Cliente</p>
        {selected ? (
          <div className="flex items-center justify-between gap-2 rounded-xl bg-blue-50 px-4 py-3 dark:bg-blue-950">
            <div className="min-w-0">
              <p className="truncate font-medium text-gray-900 dark:text-gray-100">{selected.name}</p>
              <p className="truncate text-xs text-gray-500">{selected.company || selected.phone || 'Cliente existente'}</p>
            </div>
            <button onClick={() => setSelected(null)} className="shrink-0 text-sm text-brand-blue">
              Cambiar
            </button>
          </div>
        ) : creatingNew && !manualEntry ? (
          <div className="space-y-3">
            <IntakeAssistant
              initialName={newClient.name}
              initialSurveyType={surveyType}
              startWithAll={startAll}
              busy={busy || gps.locating}
              busyLabel={busy ? 'Preparando…' : 'Buscando tu ubicación…'}
              submitLabel="🎙️ Comenzar levantamiento"
              onComplete={(intake) => {
                setNewClient({ ...newClient, name: intake.name, phone: intake.phone })
                setSurveyType(intake.survey_type)
                void start(intake)
              }}
              onManual={() => setManualEntry(true)}
            />
            <button onClick={() => setCreatingNew(false)} className="text-sm text-brand-blue">
              ← Buscar un cliente existente
            </button>
          </div>
        ) : creatingNew ? (
          <div className="space-y-3">
            <Field label="Nombre del cliente">
              <Input
                autoFocus
                value={newClient.name}
                onChange={(e) => setNewClient({ ...newClient, name: e.target.value })}
              />
            </Field>
            <Field label="Teléfono">
              <Input
                type="tel"
                inputMode="tel"
                value={newClient.phone}
                onChange={(e) => setNewClient({ ...newClient, phone: e.target.value })}
              />
            </Field>
            <Field label="Empresa (opcional)">
              <Input value={newClient.company} onChange={(e) => setNewClient({ ...newClient, company: e.target.value })} />
            </Field>
            <div className="flex flex-wrap gap-x-4 gap-y-1">
              <button onClick={() => setManualEntry(false)} className="text-sm text-brand-blue">
                🤖 Que el asistente me pregunte
              </button>
              <button onClick={() => setCreatingNew(false)} className="text-sm text-gray-500 dark:text-gray-400">
                ← Buscar un cliente existente
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            <ClientCombobox
              inputId="client-search"
              clients={clients ?? []}
              value={null}
              onSelect={setSelected}
              onCreateNew={(typed) => startNewClient(typed)}
            />
            {/* Visible siempre: antes de escribir nada no hay lista, así que el alta no puede
                depender solo del renglón "Crear cliente nuevo" del menú. */}
            <Button variant="secondary" onClick={() => startNewClient('', false)}>
              ＋ Cliente nuevo · el asistente te pregunta
            </Button>
          </div>
        )}
      </Card>

      <Card className="space-y-3">
        <p className="font-medium text-gray-800 dark:text-gray-200">2 · Ubicación</p>
        <Button variant="secondary" onClick={gps.capture} disabled={gps.locating}>
          {gps.locating ? 'Buscando señal GPS…' : locationUrl ? '📍 Actualizar mi ubicación' : '📍 Usar mi ubicación actual'}
        </Button>
        {gps.note && <p className="text-sm text-gray-600 dark:text-gray-400">{gps.note}</p>}
        <Field label="Dirección o referencia (opcional)">
          <Input placeholder="Ej. Calle 5 #12, frente al colmado" value={address} onChange={(e) => setAddress(e.target.value)} />
        </Field>
        <Field label="Enlace de Google Maps (opcional)">
          <Input placeholder="Se llena solo con el GPS, o pega uno" value={locationUrl} onChange={(e) => setLocationUrl(e.target.value)} />
        </Field>
        <MapPreview place={{ address, location_url: locationUrl }} />
      </Card>

      {!(creatingNew && !manualEntry) && (
        <Card className="space-y-3">
          <p className="font-medium text-gray-800 dark:text-gray-200">3 · Tipo de levantamiento</p>
          <div className="flex flex-wrap gap-2">
            {SURVEY_TYPES.map((t) => (
              <button
                key={t}
                type="button"
                aria-pressed={surveyType === t}
                onClick={() => setSurveyType(surveyType === t ? '' : t)}
                className={`rounded-full px-4 py-2 text-sm font-medium ${
                  surveyType === t
                    ? 'bg-brand-blue text-white'
                    : 'bg-brand-gray text-gray-800 dark:bg-gray-800 dark:text-gray-100'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </Card>
      )}

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      {/* Con el asistente, su propio botón final arranca el levantamiento. */}
      {!(creatingNew && !manualEntry) && (
        <Button onClick={() => start()} disabled={!canStart}>
          {busy ? 'Preparando…' : '🎙️ Comenzar levantamiento'}
        </Button>
      )}
    </div>
  )
}
