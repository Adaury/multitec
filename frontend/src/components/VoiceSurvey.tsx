import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { VoiceSurveyResult } from '../lib/types'
import { Button, Card, Field, Textarea } from './ui'

const MAX_SECONDS = 5 * 60
// La transcripción local (Whisper en CPU) + el reparto con IA pueden tardar más de lo normal.
const TRANSCRIBE_TIMEOUT_MS = 180_000

function pickMimeType(): string {
  if (typeof MediaRecorder === 'undefined') return ''
  for (const type of ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4']) {
    if (MediaRecorder.isTypeSupported(type)) return type
  }
  return ''
}

function formatTime(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

function errorText(error: any, fallback: string): string {
  const detail = error?.response?.data?.detail
  return typeof detail === 'string' ? detail : fallback
}

export async function transcribeAsset(projectId: number, assetId: number): Promise<VoiceSurveyResult> {
  const { data } = await api.post<VoiceSurveyResult>(
    `/projects/${projectId}/survey/assets/${assetId}/transcribe`,
    undefined,
    { timeout: TRANSCRIBE_TIMEOUT_MS },
  )
  return data
}

/** Graba al técnico hablando libremente, sube el audio al levantamiento y lo transcribe en el
 * servidor (Whisper local). Entrega el resultado a `onTranscribed` para que lo revise. */
export function VoiceRecorderCard({
  projectId,
  disabled,
  large,
  onTranscribed,
}: {
  projectId: number
  disabled?: boolean
  /** Botón de micrófono grande y centrado, para la pantalla móvil de levantamiento rápido. */
  large?: boolean
  onTranscribed: (result: VoiceSurveyResult) => void
}) {
  const queryClient = useQueryClient()
  const [state, setState] = useState<'idle' | 'recording' | 'processing'>('idle')
  const [seconds, setSeconds] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<number | null>(null)

  function clearTimer() {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current)
      timerRef.current = null
    }
  }

  function releaseMic() {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }

  useEffect(
    () => () => {
      clearTimer()
      recorderRef.current?.state === 'recording' && recorderRef.current.stop()
      releaseMic()
    },
    [],
  )

  async function process(blob: Blob, mimeType: string) {
    setState('processing')
    try {
      const extension = mimeType.includes('mp4') ? 'm4a' : 'webm'
      const form = new FormData()
      form.append('kind', 'audio')
      form.append('file', new File([blob], `levantamiento-voz-${Date.now()}.${extension}`, { type: mimeType }))
      const asset = (await api.post<{ id: number }>(`/projects/${projectId}/survey/assets`, form)).data
      // El audio ya quedó guardado: se refresca la lista aunque la transcripción falle.
      queryClient.invalidateQueries({ queryKey: ['survey', projectId] })
      onTranscribed(await transcribeAsset(projectId, asset.id))
    } catch (err: any) {
      setError(
        errorText(err, 'No se pudo procesar el audio. La grabación quedó guardada; puedes transcribirla desde la lista de audios.'),
      )
    } finally {
      queryClient.invalidateQueries({ queryKey: ['survey', projectId] })
      setState('idle')
    }
  }

  async function start() {
    setError(null)
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setError(
        'Este navegador no puede grabar aquí. El micrófono solo funciona en HTTPS o en localhost ' +
          '(usa http://localhost:5173 o el enlace https).',
      )
      return
    }
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      setError('No se pudo usar el micrófono. Revisa el permiso del navegador.')
      return
    }
    const mimeType = pickMimeType()
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
    chunksRef.current = []
    recorder.ondataavailable = (e) => e.data.size > 0 && chunksRef.current.push(e.data)
    recorder.onstop = () => {
      clearTimer()
      releaseMic()
      const type = recorder.mimeType || mimeType || 'audio/webm'
      const blob = new Blob(chunksRef.current, { type })
      if (blob.size === 0) {
        setError('No se grabó nada. Intenta de nuevo.')
        setState('idle')
        return
      }
      void process(blob, type.split(';')[0])
    }
    streamRef.current = stream
    recorderRef.current = recorder
    recorder.start(1000)
    setSeconds(0)
    setState('recording')
    timerRef.current = window.setInterval(() => {
      setSeconds((s) => {
        if (s + 1 >= MAX_SECONDS) recorderRef.current?.stop()
        return s + 1
      })
    }, 1000)
  }

  function stop() {
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
  }

  if (large) {
    const recording = state === 'recording'
    const processing = state === 'processing'
    return (
      <div className="flex flex-col items-center gap-3 py-4 text-center">
        <button
          type="button"
          onClick={recording ? stop : start}
          disabled={disabled || processing}
          aria-label={recording ? 'Detener grabación' : 'Empezar a narrar'}
          className={`flex h-32 w-32 items-center justify-center rounded-full text-6xl text-white shadow-xl transition active:scale-95 disabled:opacity-50 ${
            recording ? 'animate-pulse bg-red-600' : 'bg-brand-blue'
          }`}
        >
          {processing ? '⏳' : recording ? '⏹' : '🎙️'}
        </button>
        <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {processing ? 'Transcribiendo…' : recording ? `Grabando · ${formatTime(seconds)}` : 'Toca y narra el levantamiento'}
        </p>
        <p className="max-w-xs text-sm text-gray-500 dark:text-gray-400">
          {processing
            ? 'Puede tardar hasta ~1 minuto.'
            : recording
              ? 'Cuenta qué hay que instalar, las medidas y lo que observes. Toca de nuevo para terminar.'
              : 'Equipos y cantidades, medidas, y condiciones del sitio. Puedes grabar varias veces.'}
        </p>
        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      </div>
    )
  }

  return (
    <Card className="space-y-2">
      <p className="font-medium text-gray-800 dark:text-gray-200">🎙️ Levantamiento por voz</p>
      <p className="text-sm text-gray-500 dark:text-gray-400">
        Pulsa, recorre el sitio y cuenta qué hay que instalar, las medidas y lo que observes. La IA
        reparte lo dicho en Notas, Medidas y Observaciones para que lo revises antes de aplicarlo.
      </p>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      {state === 'processing' ? (
        <Button disabled>Transcribiendo… (puede tardar hasta ~1 min)</Button>
      ) : state === 'recording' ? (
        <Button onClick={stop} className="!bg-red-600 hover:!bg-red-700">
          ⏹ Detener y procesar · 🔴 {formatTime(seconds)}
        </Button>
      ) : (
        <Button onClick={start} disabled={disabled}>
          🎙️ Empezar a hablar
        </Button>
      )}
    </Card>
  )
}

/** Revisión del resultado: el técnico puede corregir cada campo antes de aplicarlo. */
export function VoiceReviewCard({
  projectId,
  result,
  busy,
  onApply,
  onApplyAndGenerate,
  onDiscard,
}: {
  projectId: number
  result: VoiceSurveyResult
  busy: boolean
  onApply: (fields: Pick<VoiceSurveyResult, 'notes' | 'measurements' | 'observations'>) => void
  onApplyAndGenerate: (fields: Pick<VoiceSurveyResult, 'notes' | 'measurements' | 'observations'>) => void
  onDiscard: () => void
}) {
  const [notes, setNotes] = useState(result.notes)
  const [measurements, setMeasurements] = useState(result.measurements)
  const [observations, setObservations] = useState(result.observations)
  const fields = { notes, measurements, observations }
  const empty = !notes.trim() && !measurements.trim() && !observations.trim()

  // Aprendizaje: se guarda lo que dijo, cómo lo repartió la IA y cómo lo dejó el técnico. Es
  // best-effort: si falla no debe frenar al técnico en el sitio, así que no se espera ni se muestra.
  function learn() {
    api
      .post(`/projects/${projectId}/survey/voice-feedback`, {
        transcript: result.transcript,
        ai: { notes: result.notes, measurements: result.measurements, observations: result.observations },
        final: fields,
        classified: result.classified,
      })
      .catch(() => {})
  }

  return (
    <Card className="space-y-3 ring-2 ring-brand-blue/30">
      <p className="font-medium text-gray-800 dark:text-gray-200">Revisa lo que entendí</p>
      <details className="rounded-xl bg-brand-gray p-3 text-sm dark:bg-gray-800">
        <summary className="cursor-pointer text-gray-600 dark:text-gray-300">Ver lo que dijiste (texto original)</summary>
        <p className="mt-2 whitespace-pre-line text-gray-700 dark:text-gray-300">{result.transcript}</p>
      </details>
      {!result.classified && (
        <p className="text-sm text-amber-600 dark:text-amber-400">
          La IA no pudo repartir el texto automáticamente: todo quedó en Notas. Muévelo a mano si hace falta.
        </p>
      )}
      <Field label="Notas">
        <Textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
      </Field>
      <Field label="Medidas">
        <Textarea rows={2} value={measurements} onChange={(e) => setMeasurements(e.target.value)} />
      </Field>
      <Field label="Observaciones">
        <Textarea rows={2} value={observations} onChange={(e) => setObservations(e.target.value)} />
      </Field>
      <p className="text-xs text-gray-400">Se agrega al final de lo que ya tengas escrito en cada campo.</p>
      <div className="flex flex-col gap-2 md:flex-row">
        <Button variant="secondary" onClick={() => {
            learn()
            onApply(fields)
          }} disabled={busy || empty}>
          Agregar al levantamiento
        </Button>
        <Button onClick={() => {
            learn()
            onApplyAndGenerate(fields)
          }} disabled={busy || empty}>
          {busy ? 'Trabajando…' : '🤖 Agregar y generar cotización'}
        </Button>
        <Button variant="ghost" onClick={onDiscard} disabled={busy}>
          Descartar
        </Button>
      </div>
    </Card>
  )
}
