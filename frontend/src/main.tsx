import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import './lib/themeStore'
import './index.css'
import App from './App.tsx'
import { queryClient } from './lib/queryClient'

// iPhone: pide que el navegador no borre el almacenamiento de la app (la cola de levantamientos sin
// enviar y las fotos) cuando hace falta espacio. Si no lo concede, no pasa nada: es solo un seguro.
void navigator.storage?.persist?.().catch(() => {})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
