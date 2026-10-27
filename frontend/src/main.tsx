import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import './lib/themeStore'
import './index.css'
import App from './App.tsx'
import { queryClient } from './lib/queryClient'
import { clearAppCache, ErrorBoundary } from './components/ErrorBoundary'

// Una pantalla de la app que no se puede descargar (el servidor ya tiene una versión nueva y el teléfono guardó la
// vieja): se limpia la copia guardada y se recarga UNA vez. Si vuelve a pasar, lo atrapa ErrorBoundary.
window.addEventListener('vite:preloadError', () => {
  try {
    if (sessionStorage.getItem('multitec_reloaded') === '1') return
    sessionStorage.setItem('multitec_reloaded', '1')
  } catch {
    return
  }
  void clearAppCache().then(() => window.location.reload())
})

// iPhone: pide que el navegador no borre el almacenamiento de la app (la cola de levantamientos sin
// enviar y las fotos) cuando hace falta espacio. Si no lo concede, no pasa nada: es solo un seguro.
void navigator.storage?.persist?.().catch(() => {})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  </StrictMode>,
)
