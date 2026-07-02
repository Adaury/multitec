import { useCallback, useRef, useState } from 'react'

interface UseSpeechDictationOptions {
  onResult: (text: string) => void
  lang?: string
}

function getSpeechRecognitionCtor(): (new () => any) | undefined {
  if (typeof window === 'undefined') return undefined
  const w = window as unknown as { SpeechRecognition?: new () => any; webkitSpeechRecognition?: new () => any }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition
}

export function useSpeechDictation({ onResult, lang = 'es-DO' }: UseSpeechDictationOptions) {
  const [listening, setListening] = useState(false)
  const recognitionRef = useRef<any>(null)
  const supported = Boolean(getSpeechRecognitionCtor())

  const start = useCallback(() => {
    const Ctor = getSpeechRecognitionCtor()
    if (!Ctor) return

    const recognition = new Ctor()
    recognition.lang = lang
    recognition.continuous = true
    recognition.interimResults = false
    recognition.onresult = (event: any) => {
      const transcript = Array.from(event.results as ArrayLike<{ 0: { transcript: string } }>)
        .map((r) => r[0].transcript)
        .join(' ')
      onResult(transcript)
    }
    recognition.onend = () => setListening(false)
    recognition.onerror = () => setListening(false)

    recognitionRef.current = recognition
    recognition.start()
    setListening(true)
  }, [lang, onResult])

  const stop = useCallback(() => {
    recognitionRef.current?.stop()
    setListening(false)
  }, [])

  return { supported, listening, start, stop }
}
