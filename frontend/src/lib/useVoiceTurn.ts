import { useCallback, useEffect, useRef, useState } from 'react'
import { pickMimeType } from './audioRecording'

const MAX_SECONDS = 12 // una orden al asistente es corta; más que esto es que se quedó abierto
const SILENCE_AFTER_SPEECH_MS = 1400 // pausa que se toma como "ya terminé de hablar"
const SPEECH_LEVEL = 0.035 // volumen (RMS) a partir del cual se considera que hay voz

const DENIED =
  'El micrófono está bloqueado. En el iPhone: toca "aA" junto a la dirección → Configuración del sitio web → ' +
  'Micrófono → Permitir. Mientras tanto puedes escribir.'

/** Un turno de voz: graba lo que dice el técnico y entrega el audio para transcribirlo en el
 * servidor. Se usa esto en vez del dictado del navegador porque en iPhone ese dictado falla seguido
 * (no arranca sin un toque, se corta solo, no entrega resultado). Grabar funciona igual en todos.
 *
 * Termina sola al notar una pausa después de hablar, al tocar de nuevo, o a los 12 s. El micrófono
 * se suelta al terminar: con el micrófono abierto, el iPhone baja o corta la voz del asistente. */
export function useVoiceTurn(onAudio: (audio: Blob, extension: string) => void) {
  const supported =
    typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== 'undefined'
  const [recording, setRecording] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const contextRef = useRef<AudioContext | null>(null)
  const timersRef = useRef<number[]>([])
  const cancelledRef = useRef(false)
  const onAudioRef = useRef(onAudio)
  useEffect(() => {
    onAudioRef.current = onAudio
  }, [onAudio])

  const cleanup = useCallback(() => {
    timersRef.current.forEach((id) => window.clearInterval(id))
    timersRef.current = []
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    recorderRef.current = null
    setRecording(false)
  }, [])

  const stop = useCallback(() => {
    const recorder = recorderRef.current
    if (recorder && recorder.state !== 'inactive') recorder.stop()
  }, [])

  /** Corta sin enviar nada (se cerró la conversación). */
  const cancel = useCallback(() => {
    cancelledRef.current = true
    stop()
    cleanup()
  }, [cleanup, stop])

  const start = useCallback(async (): Promise<boolean> => {
    if (!supported || recorderRef.current) return false
    setError(null)
    cancelledRef.current = false
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      })
    } catch (err) {
      const name = (err as { name?: string }).name
      setError(
        name === 'NotAllowedError' || name === 'SecurityError'
          ? DENIED
          : 'No encontré un micrófono en este dispositivo. Puedes escribir.',
      )
      return false
    }
    streamRef.current = stream

    const mimeType = pickMimeType()
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
    const chunks: Blob[] = []
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunks.push(event.data)
    }
    recorder.onstop = () => {
      const type = recorder.mimeType || mimeType || 'audio/webm'
      const cancelled = cancelledRef.current
      cleanup()
      if (cancelled) return
      const blob = new Blob(chunks, { type })
      // Menos que esto no es voz: un toque accidental.
      if (blob.size > 1200) onAudioRef.current(blob, type.includes('mp4') ? 'm4a' : 'webm')
    }
    recorderRef.current = recorder
    recorder.start()
    setRecording(true)

    timersRef.current.push(window.setTimeout(stop, MAX_SECONDS * 1000))

    // Detección de pausa: opcional. Si el navegador no deja medir el volumen (contexto de audio
    // suspendido fuera de un toque), simplemente se termina tocando el botón o por el tope.
    try {
      const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
      if (Ctor) {
        const context = contextRef.current ?? new Ctor()
        contextRef.current = context
        if (context.state === 'suspended') await context.resume()
        const analyser = context.createAnalyser()
        analyser.fftSize = 1024
        context.createMediaStreamSource(stream).connect(analyser)
        const samples = new Float32Array(analyser.fftSize)
        let spoke = false
        let quietSince = 0
        timersRef.current.push(
          window.setInterval(() => {
            analyser.getFloatTimeDomainData(samples)
            let sum = 0
            for (const value of samples) sum += value * value
            const level = Math.sqrt(sum / samples.length)
            const now = Date.now()
            if (level >= SPEECH_LEVEL) {
              spoke = true
              quietSince = 0
            } else if (spoke) {
              if (!quietSince) quietSince = now
              else if (now - quietSince >= SILENCE_AFTER_SPEECH_MS) stop()
            }
          }, 120),
        )
      }
    } catch {
      // sin medidor de volumen: queda el botón y el tope de tiempo
    }
    return true
  }, [cleanup, stop, supported])

  useEffect(
    () => () => {
      cancelledRef.current = true
      const recorder = recorderRef.current
      if (recorder && recorder.state !== 'inactive') recorder.stop()
      streamRef.current?.getTracks().forEach((track) => track.stop())
      timersRef.current.forEach((id) => window.clearInterval(id))
      void contextRef.current?.close().catch(() => {})
    },
    [],
  )

  return { supported, recording, error, start, stop, cancel }
}
