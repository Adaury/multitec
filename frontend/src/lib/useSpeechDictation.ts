import { useCallback, useEffect, useRef, useState } from 'react'

interface UseSpeechDictationOptions {
  onResult: (text: string) => void
  lang?: string
}

function getSpeechRecognitionCtor(): (new () => any) | undefined {
  if (typeof window === 'undefined') return undefined
  const w = window as unknown as { SpeechRecognition?: new () => any; webkitSpeechRecognition?: new () => any }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition
}

const ERROR_MESSAGES: Record<string, string> = {
  'not-allowed': 'Permiso de micrófono denegado. Actívalo en el navegador.',
  'service-not-allowed': 'Permiso de micrófono denegado. Actívalo en el navegador.',
  'audio-capture': 'No se encontró un micrófono.',
  network: 'El dictado del navegador necesita internet.',
}

export function useSpeechDictation({ onResult, lang = 'es-DO' }: UseSpeechDictationOptions) {
  const [listening, setListening] = useState(false)
  const [interim, setInterim] = useState('')
  const [error, setError] = useState<string | null>(null)
  const recognitionRef = useRef<any>(null)
  const supported = Boolean(getSpeechRecognitionCtor())

  // El reconocimiento sigue vivo entre renders: siempre debe llamar al onResult más reciente
  // (con el valor actual del campo), no al de cuando se pulsó el botón.
  const onResultRef = useRef(onResult)
  useEffect(() => {
    onResultRef.current = onResult
  }, [onResult])

  useEffect(() => () => recognitionRef.current?.abort?.(), [])

  const start = useCallback(() => {
    const Ctor = getSpeechRecognitionCtor()
    if (!Ctor) return

    setError(null)
    setInterim('')
    const recognition = new Ctor()
    recognition.lang = lang
    recognition.continuous = true
    recognition.interimResults = true
    recognition.onresult = (event: any) => {
      // event.results acumula TODO lo dicho en la sesión; solo se procesa desde resultIndex
      // para no volver a agregar frases ya entregadas.
      let finalText = ''
      let interimText = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        const text: string = result[0].transcript
        if (result.isFinal) finalText += text
        else interimText += text
      }
      setInterim(interimText)
      const cleaned = finalText.trim()
      if (cleaned) onResultRef.current(cleaned)
    }
    recognition.onend = () => {
      setListening(false)
      setInterim('')
    }
    recognition.onerror = (event: any) => {
      // 'no-speech' y 'aborted' son normales (silencio / parada manual), no son un fallo.
      const message = ERROR_MESSAGES[event?.error]
      if (message) setError(message)
      setListening(false)
    }

    recognitionRef.current = recognition
    try {
      recognition.start()
      setListening(true)
    } catch {
      setListening(false)
    }
  }, [lang])

  const stop = useCallback(() => {
    recognitionRef.current?.stop()
  }, [])

  return { supported, listening, interim, error, start, stop }
}
