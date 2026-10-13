import { useCallback, useEffect, useRef, useState } from 'react'

function pickVoice(lang: string): SpeechSynthesisVoice | null {
  const voices = window.speechSynthesis.getVoices().filter((v) => v.lang.toLowerCase().startsWith(lang))
  // Español de América primero (suena más cercano que el de España para un técnico dominicano).
  return voices.find((v) => /es[-_](US|MX|419|DO)/i.test(v.lang)) ?? voices.find((v) => v.localService) ?? voices[0] ?? null
}

const wait = (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms))

/** Voz del asistente con la síntesis del navegador (no usa servidor ni internet). `speak` devuelve
 * una promesa que se cumple cuando termina de hablar, para poder escuchar justo después. Si el
 * navegador no tiene voz, la promesa se cumple enseguida y la conversación sigue por texto.
 *
 * Los cuidados de aquí son por Safari en iPhone, donde la voz "a veces sí, a veces no":
 *  - llamar `cancel()` justo antes de `speak()` se traga la frase → solo se cancela si hay algo
 *    sonando, y se espera un instante antes de hablar;
 *  - la cola puede quedar en pausa para siempre → `resume()` antes de cada frase;
 *  - si el objeto de la frase se libera de memoria, `onend` nunca llega → se guarda la referencia;
 *  - las voces cargan tarde → se elige la voz al momento de hablar, no al montar. */
export function useSpeaker(lang = 'es') {
  const supported = typeof window !== 'undefined' && 'speechSynthesis' in window
  const [speaking, setSpeaking] = useState(false)
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null)

  useEffect(() => {
    if (!supported) return
    // Pedir las voces ya las pone a cargar (en Safari llegan después, con `voiceschanged`).
    window.speechSynthesis.getVoices()
    return () => window.speechSynthesis.cancel()
  }, [supported])

  const speak = useCallback(
    async (text: string): Promise<void> => {
      if (!supported || !text.trim()) return
      const synth = window.speechSynthesis
      if (synth.speaking || synth.pending) {
        synth.cancel()
        await wait(80)
      }
      await new Promise<void>((resolve) => {
        const voice = pickVoice(lang)
        const utterance = new SpeechSynthesisUtterance(text)
        utterance.lang = voice?.lang ?? 'es-US'
        if (voice) utterance.voice = voice
        utterance.rate = 1.02
        utteranceRef.current = utterance
        let finished = false
        const finish = () => {
          if (finished) return
          finished = true
          window.clearTimeout(guard)
          utteranceRef.current = null
          setSpeaking(false)
          resolve()
        }
        // Sin ninguna voz instalada no va a sonar nada: se espera lo mínimo y se sigue por texto.
        // Con voz, el tope cubre el caso en que `onend` no llega y la conversación se colgaría.
        const hasVoices = synth.getVoices().length > 0
        const guard = window.setTimeout(finish, hasVoices ? Math.min(20_000, 2500 + text.length * 90) : 1200)
        utterance.onend = finish
        utterance.onerror = finish
        setSpeaking(true)
        try {
          synth.resume()
          synth.speak(utterance)
        } catch {
          finish()
        }
      })
    },
    [supported, lang],
  )

  const stop = useCallback(() => {
    if (supported) window.speechSynthesis.cancel()
    setSpeaking(false)
  }, [supported])

  return { supported, speaking, speak, stop }
}
