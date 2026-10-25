import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MessageCircle } from 'lucide-react'
import { api } from '../lib/api'
import { SURVEY_TYPES } from '../lib/surveyTypes'
import { useSpeaker } from '../lib/useSpeaker'
import { useVoiceTurn } from '../lib/useVoiceTurn'

interface TalkReply {
  intent: string
  reply: string
  navigate_to: string | null
  client_name: string
  client_id: number | null
  phone: string
  survey_type: string
  ai_used: boolean
  /** Lo que el servidor entendió del audio (solo cuando se habló). */
  heard?: string
}

interface Bubble {
  from: 'ai' | 'me'
  text: string
}

/** A dónde lleva la respuesta. Un levantamiento nuevo viaja con lo que ya se entendió (cliente,
 * tipo, teléfono) para que el técnico no lo repita. */
function destination(reply: TalkReply): string | null {
  if (!reply.navigate_to) return null
  if (reply.intent !== 'new_survey') return reply.navigate_to
  const params = new URLSearchParams()
  if (reply.client_id != null) params.set('cliente', String(reply.client_id))
  else if (reply.client_name) params.set('nombre', reply.client_name)
  else params.set('modo', 'voz')
  if (reply.survey_type) params.set('tipo', reply.survey_type)
  if (reply.phone) params.set('telefono', reply.phone)
  return `${reply.navigate_to}?${params.toString()}`
}

/** Conversación hablada con el asistente: saluda, pregunta "¿qué toca hoy?", escucha la respuesta y
 * lleva al técnico a donde corresponde.
 *
 * La voz del asistente es la del teléfono. Para escuchar, el teléfono solo GRABA y el servidor
 * transcribe (Whisper local) y entiende la frase: el dictado propio del navegador fallaba seguido
 * en iPhone. Siempre se puede escribir en vez de hablar. */
export function AssistantTalk({ opening }: { opening: string }) {
  const navigate = useNavigate()
  const speaker = useSpeaker()
  const [active, setActive] = useState(false)
  const [bubbles, setBubbles] = useState<Bubble[]>([])
  const [status, setStatus] = useState<'idle' | 'transcribing' | 'thinking'>('idle')
  const [typed, setTyped] = useState('')
  const endRef = useRef<HTMLDivElement>(null)
  // Un turno a la vez: mientras el asistente piensa o habla no se acepta otra respuesta (antes se
  // perdía en silencio). `busy` deshabilita los controles; el ref evita dobles envíos.
  const busyRef = useRef(false)
  const [busy, setBusy] = useState(false)
  const activeRef = useRef(false)

  const setBusyBoth = (value: boolean) => {
    busyRef.current = value
    setBusy(value)
  }

  const onAudioRef = useRef<(audio: Blob, extension: string) => void>(() => {})
  const voice = useVoiceTurn((audio, extension) => onAudioRef.current(audio, extension))

  const listen = useCallback(() => {
    if (activeRef.current && voice.supported) void voice.start()
  }, [voice])

  const say = useCallback(
    async (text: string) => {
      setBubbles((prev) => [...prev, { from: 'ai', text }])
      await speaker.speak(text)
    },
    [speaker],
  )

  /** Responde un turno: `ask` trae la respuesta del servidor (por texto o por audio). */
  const takeTurn = useCallback(
    async (ask: () => Promise<TalkReply>, typedText?: string) => {
      if (busyRef.current) return
      setBusyBoth(true)
      if (typedText) setBubbles((prev) => [...prev, { from: 'me', text: typedText }])
      setStatus(typedText ? 'thinking' : 'transcribing')
      try {
        const reply = await ask()
        setStatus('idle')
        if (reply.heard) setBubbles((prev) => [...prev, { from: 'me', text: reply.heard! }])
        await say(reply.reply)
        const target = destination(reply)
        if (target) {
          navigate(target)
          return
        }
        setBusyBoth(false)
        if (reply.intent !== 'none') listen()
      } catch {
        setStatus('idle')
        await say('No pude conectarme con el servidor. Puedes tocar una de las opciones de abajo.')
      } finally {
        setBusyBoth(false)
      }
    },
    [listen, navigate, say],
  )

  onAudioRef.current = (audio, extension) => {
    const form = new FormData()
    form.append('audio', audio, `turno.${extension}`)
    form.append('survey_types', JSON.stringify([...SURVEY_TYPES]))
    void takeTurn(async () => (await api.post<TalkReply>('/assistant/listen', form)).data)
  }

  const sendTyped = (text: string) => {
    const clean = text.trim()
    if (!clean) return
    voice.cancel()
    void takeTurn(
      async () => (await api.post<TalkReply>('/assistant/talk', { text: clean, survey_types: [...SURVEY_TYPES] })).data,
      clean,
    )
  }

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: 'nearest' })
  }, [bubbles, status, voice.recording])

  const start = async () => {
    activeRef.current = true
    setActive(true)
    setBubbles([])
    setBusyBoth(true)
    // Carga el modelo de voz del servidor mientras el asistente saluda: así el primer turno no
    // paga el arranque en frío.
    api.post('/ai/warmup').catch(() => {})
    await say(`${opening} ¿Qué toca hoy?`)
    setBusyBoth(false)
    listen()
  }

  const close = () => {
    activeRef.current = false
    speaker.stop()
    voice.cancel()
    setActive(false)
  }

  if (!active) {
    return (
      <button
        type="button"
        onClick={() => void start()}
        className="flex w-full items-center gap-4 rounded-2xl bg-brand-blue p-4 text-left text-white shadow active:scale-[0.99]"
      >
        <MessageCircle className="h-10 w-10 shrink-0" aria-hidden="true" />
        <span>
          <span className="block text-lg font-bold leading-tight">Hablar con el asistente</span>
          <span className="block text-sm text-blue-100">Te pregunto qué toca hoy y me lo dices hablando</span>
        </span>
      </button>
    )
  }

  const hint = voice.recording
    ? 'Te escucho… al terminar, espera un momento o toca el micrófono.'
    : status === 'transcribing'
      ? 'Escuchando lo que dijiste…'
      : status === 'thinking'
        ? 'Pensando…'
        : speaker.speaking
          ? ''
          : voice.supported
            ? 'Toca el micrófono para responder.'
            : ''

  return (
    <div className="space-y-3 rounded-2xl bg-white p-3 ring-1 ring-black/5 dark:bg-gray-900 dark:ring-white/10">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">Conversación con el asistente</p>
        <button type="button" onClick={close} className="text-sm text-gray-500 dark:text-gray-400" aria-label="Cerrar conversación">
          ✕
        </button>
      </div>

      <div className="max-h-64 space-y-2 overflow-y-auto" aria-live="polite">
        {bubbles.map((bubble, index) => (
          <p
            key={index}
            className={`max-w-[88%] rounded-2xl px-3 py-2 text-sm ${
              bubble.from === 'ai'
                ? 'bg-blue-50 text-gray-900 dark:bg-blue-950 dark:text-gray-100'
                : 'ml-auto bg-brand-blue text-white'
            }`}
          >
            {bubble.from === 'ai' ? '🤖 ' : ''}
            {bubble.text}
          </p>
        ))}
        {hint && <p className="text-xs text-gray-500 dark:text-gray-400">{hint}</p>}
        <div ref={endRef} />
      </div>

      <div className="flex items-center gap-2">
        {voice.supported && (
          <button
            type="button"
            onClick={voice.recording ? voice.stop : listen}
            disabled={busy}
            aria-label={voice.recording ? 'Terminar y enviar lo que dije' : 'Responder hablando'}
            className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl text-2xl disabled:opacity-50 ${
              voice.recording ? 'animate-pulse bg-red-500 text-white' : 'bg-brand-blue text-white'
            }`}
          >
            {voice.recording ? '⏹' : '🎙️'}
          </button>
        )}
        <form
          className="flex min-w-0 flex-1 gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            if (busy) return
            const text = typed
            setTyped('')
            sendTyped(text)
          }}
        >
          <input
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            placeholder="O escríbelo aquí"
            aria-label="Escribe lo que quieres hacer"
            className="min-w-0 flex-1 rounded-xl border border-gray-200 bg-white px-3 py-2 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
          />
          <button
            type="submit"
            disabled={!typed.trim() || busy}
            className="shrink-0 rounded-xl bg-brand-gray px-3 py-2 text-sm font-medium text-gray-800 disabled:opacity-50 dark:bg-gray-800 dark:text-gray-100"
          >
            Enviar
          </button>
        </form>
      </div>
      {voice.error && <p className="text-xs text-red-600 dark:text-red-400">{voice.error}</p>}
      {!voice.supported && (
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Este navegador no puede grabar voz: escribe lo que quieres hacer.
        </p>
      )}
    </div>
  )
}
