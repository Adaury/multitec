import { useEffect, useState } from 'react'

/** `true` mientras el navegador dice que hay red. Es una pista, no una garantía (puede haber WiFi
 * sin internet): por eso la cola de pendientes también se detiene sola ante un fallo de red real. */
export function useOnline(): boolean {
  const [online, setOnline] = useState(() => navigator.onLine)
  useEffect(() => {
    const up = () => setOnline(true)
    const down = () => setOnline(false)
    window.addEventListener('online', up)
    window.addEventListener('offline', down)
    return () => {
      window.removeEventListener('online', up)
      window.removeEventListener('offline', down)
    }
  }, [])
  return online
}
