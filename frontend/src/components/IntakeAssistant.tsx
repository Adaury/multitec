import { useState } from 'react'
import { api } from '../lib/api'
import { SURVEY_TYPES } from '../lib/surveyTypes'
import { useSpeechDictation } from '../lib/useSpeechDictation'
import type { IntakeParseResult } from '../lib/types'
import { Button, Field, Input, Textarea } from './ui'

export interface IntakeData {
  name: string
  phone: string
  survey_type: string
}

type Key = 'name' | 'phone' | 'type'
type Phase = Key | 'all' | 'confirm'
interface Bubble {
  from: 'ai' | 'me'
  text: string
}

const QUESTIONS: Record<Key, string> = {
  name: '¿Cómo se llama el cliente?',
  phone: '¿Cuál es su número de teléfono?',
  type: '¿Qué tipo de levantamiento es?',
}
const ORDER: Key[] = ['name', 'phone', 'type']

/** 10 dígitos → 809-555-1234; otra cosa se deja tal cual (limpia de ruido). */
function formatPhone(raw: string): string {
  let digits = raw.replace(/\D/g, '')
  if (digits.length === 11 && digits.startsWith('1')) digits = digits.slice(1)
  if (digits.length === 10) return `${digits.slice(0, 3)}-${digits.slice(3, 6)}-${digits.slice(6)}`
  return digits.length >= 7 ? digits : raw.trim()
}

function titleCase(text: string): string {
  const t = text.trim().replace(/\s+/g, ' ')
  return t === t.toLowerCase() ? t.replace(/\b\p{L}/gu, (c) => c.toUpperCase()) : t
}

function MicButton({ onText, disabled }: { onText: (text: string) => void; disabled?: boolean }) {
  const dictation = useSpeechDictation({ onResult: onText })
  if (!dictation.supported) return null
  return (
    <div className="space-y-1">
      <button
        type="button"
        disabled={disabled}
        onClick={dictation.listening ? dictation.stop : dictation.start}
        aria-label={dictation.listening ? 'Detener dictado' : 'Dictar con la voz'}
        className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl text-xl ${
          dictation.listening ? 'animate-pulse bg-red-500 text-white' : 'bg-brand-gray dark:bg-gray-800'
        }`}
      >
        🎙️
      </button>
      {dictation.error && <p className="text-xs text-red-600 dark:text-red-400">{dictation.error}</p>}
    </div>
  )
}

/** Asistente que va preguntando los datos básicos del cliente: nombre, teléfono y tipo de
 * levantamiento. Se contesta escribiendo, dictando o tocando una opción. También se puede decir
 * todo de una vez ("Juan Pérez, 809 555 1234, cámaras") y la IA local separa los datos. */
export function IntakeAssistant({
  initialName = '',
  initialSurveyType = '',
  startWithAll = false,
  busy,
  submitLabel = 'Crear cliente y continuar',
  busyLabel = 'Guardando…',
  onComplete,
  onManual,
}: {
  initialName?: string
  initialSurveyType?: string
  /** Arranca en "decir todo de una vez" en vez de preguntar paso a paso. */
  startWithAll?: boolean
  busy?: boolean
  submitLabel?: string
  busyLabel?: string
  onComplete: (data: IntakeData) => void
  /** Si se pasa, ofrece un enlace para llenar los datos a mano. */
  onManual?: () => void
}) {
  const [data, setData] = useState<IntakeData>({ name: initialName, phone: '', survey_type: initialSurveyType })
  const [done, setDone] = useState<Record<Key, boolean>>({
    name: Boolean(initialName),
    phone: false,
    type: Boolean(initialSurveyType),
  })
  const firstPending = (d: Record<Key, boolean>): Phase => ORDER.find((k) => !d[k]) ?? 'confirm'
  const [phase, setPhase] = useState<Phase>(() => (startWithAll ? 'all' : firstPending(done)))
  const [log, setLog] = useState<Bubble[]>([])
  const [draft, setDraft] = useState('')
  const [parsing, setParsing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function advance(nextDone: Record<Key, boolean>, bubbles: Bubble[]) {
    const next = firstPending(nextDone)
    setDone(nextDone)
    setDraft('')
    setError(null)
    setLog([...log, ...bubbles, ...(next !== 'confirm' ? [{ from: 'ai' as const, text: QUESTIONS[next as Key] }] : [])])
    setPhase(next)
  }

  function answer(key: Key, value: string, shown = value) {
    const patch: Partial<IntakeData> =
      key === 'name'
        ? { name: titleCase(value) }
        : key === 'phone'
          ? { phone: value ? formatPhone(value) : '' }
          : { survey_type: value }
    setData({ ...data, ...patch })
    advance({ ...done, [key]: true }, [
      { from: 'ai', text: QUESTIONS[key] },
      { from: 'me', text: shown || 'Omitir' },
    ])
  }

  async function interpretAll() {
    const text = draft.trim()
    if (!text) return
    setParsing(true)
    setError(null)
    try {
      const { data: parsed } = await api.post<IntakeParseResult>(
        '/ai/intake-parse',
        { text, survey_types: [...SURVEY_TYPES] },
        { timeout: 90_000 },
      )
      const merged: IntakeData = {
        name: parsed.name ? titleCase(parsed.name) : data.name,
        phone: parsed.phone || data.phone,
        survey_type: parsed.survey_type || data.survey_type,
      }
      setData(merged)
      const nextDone = { name: Boolean(merged.name), phone: Boolean(merged.phone), type: Boolean(merged.survey_type) }
      const found = [merged.name && `nombre ${merged.name}`, merged.phone && `teléfono ${merged.phone}`, merged.survey_type]
        .filter(Boolean)
        .join(' · ')
      advance(nextDone, [
        { from: 'me', text },
        { from: 'ai', text: found ? `Entendí: ${found}.` : 'No pude sacar datos de lo que dijiste.' },
      ])
    } catch {
      setError('No se pudo interpretar. Contesta las preguntas una por una.')
      setPhase(firstPending(done))
      setDraft('')
    } finally {
      setParsing(false)
    }
  }

  const append = (text: string) => setDraft((prev) => [prev, text].filter(Boolean).join(' '))

  return (
    <div className="space-y-3">
      {log.length > 0 && (
        <div className="space-y-2">
          {log.map((b, i) => (
            <p
              key={i}
              className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm ${
                b.from === 'ai'
                  ? 'bg-brand-gray text-gray-800 dark:bg-gray-800 dark:text-gray-100'
                  : 'ml-auto bg-brand-blue text-white'
              }`}
            >
              {b.text}
            </p>
          ))}
        </div>
      )}

      {(phase === 'name' || phase === 'phone') && (
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault()
            const value = draft.trim()
            if (phase === 'name' && !value) return
            answer(phase, value)
          }}
        >
          <p className="font-medium text-gray-900 dark:text-gray-100">🤖 {QUESTIONS[phase]}</p>
          <div className="flex items-start gap-2">
            <Input
              autoFocus
              type={phase === 'phone' ? 'tel' : 'text'}
              inputMode={phase === 'phone' ? 'tel' : 'text'}
              autoCapitalize={phase === 'name' ? 'words' : 'none'}
              placeholder={phase === 'name' ? 'Ej. Juan Pérez' : 'Ej. 809 555 1234'}
              aria-label={QUESTIONS[phase]}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
            />
            <MicButton onText={append} />
          </div>
          <div className="flex gap-2">
            <Button type="submit" disabled={phase === 'name' && !draft.trim()}>
              Siguiente
            </Button>
            {phase === 'phone' && (
              <Button type="button" variant="secondary" onClick={() => answer('phone', '', '')}>
                Omitir
              </Button>
            )}
          </div>
        </form>
      )}

      {phase === 'type' && (
        <div className="space-y-3">
          <p className="font-medium text-gray-900 dark:text-gray-100">🤖 {QUESTIONS.type}</p>
          <div className="grid gap-2">
            {SURVEY_TYPES.map((t) => (
              <Button key={t} type="button" variant="secondary" className="!py-3 text-left" onClick={() => answer('type', t)}>
                {t}
              </Button>
            ))}
          </div>
          <Button type="button" variant="ghost" onClick={() => answer('type', '', '')}>
            Omitir
          </Button>
        </div>
      )}

      {phase === 'all' && (
        <div className="space-y-3">
          <p className="font-medium text-gray-900 dark:text-gray-100">
            🤖 Dime todo de una vez: nombre, teléfono y qué tipo de levantamiento es.
          </p>
          <div className="flex items-start gap-2">
            <Textarea
              autoFocus
              rows={3}
              placeholder="Ej. Juan Pérez, 809 555 1234, cámaras de seguridad"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
            />
            <MicButton onText={append} disabled={parsing} />
          </div>
          <Button type="button" onClick={interpretAll} disabled={parsing || !draft.trim()}>
            {parsing ? 'Interpretando con IA… (hasta ~15 s)' : '🤖 Interpretar'}
          </Button>
          <Button type="button" variant="ghost" disabled={parsing} onClick={() => setPhase(firstPending(done))}>
            Mejor pregunta por pregunta
          </Button>
        </div>
      )}

      {phase === 'confirm' && (
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault()
            if (data.name.trim()) onComplete({ ...data, name: data.name.trim(), phone: data.phone.trim() })
          }}
        >
          <p className="font-medium text-gray-900 dark:text-gray-100">🤖 Revisa y corrige si hace falta</p>
          <Field label="Nombre del cliente">
            <Input value={data.name} onChange={(e) => setData({ ...data, name: e.target.value })} />
          </Field>
          <Field label="Teléfono">
            <Input type="tel" inputMode="tel" value={data.phone} onChange={(e) => setData({ ...data, phone: e.target.value })} />
          </Field>
          <Field label="Tipo de levantamiento">
            <select
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
              value={data.survey_type}
              onChange={(e) => setData({ ...data, survey_type: e.target.value })}
            >
              <option value="">Sin especificar</option>
              {SURVEY_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </Field>
          <Button type="submit" disabled={busy || !data.name.trim()}>
            {busy ? busyLabel : submitLabel}
          </Button>
        </form>
      )}

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {(phase === 'name' || phase === 'phone' || phase === 'type') && (
          <button type="button" onClick={() => setPhase('all')} className="text-sm text-brand-blue">
            🎙️ Decir todo de una vez
          </button>
        )}
        {onManual && (
          <button type="button" onClick={onManual} className="text-sm text-gray-500 dark:text-gray-400">
            Prefiero escribirlos yo
          </button>
        )}
      </div>
    </div>
  )
}
