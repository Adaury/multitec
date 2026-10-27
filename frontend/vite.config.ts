import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import { devMovil } from './dev-movil.ts'
import { securityHeaders } from './security-headers.ts'

// Los E2E locales levantan su propio backend en otro puerto (ver e2e/isolated.ts) y lo pasan
// por esta variable; sin ella el proxy sigue apuntando al backend normal de desarrollo.
const apiTarget = process.env.E2E_API_TARGET ?? 'http://127.0.0.1:8000'

// Lo mismo en desarrollo (`vite`) y sirviendo la versión compilada (`vite preview`).
// xfwd añade X-Forwarded-For con la IP real: sin él, el backend ve a todos como 127.0.0.1 y el
// límite de intentos de login (por IP) sería uno solo compartido por toda la empresa.
const forward = { target: apiTarget, xfwd: true }
const proxy = {
  '/api': forward,
  '/uploads': forward,
  // Documentación interactiva de la API (Swagger/ReDoc) a través del mismo puerto de la
  // web, para abrirla desde el celular en la red local sin exponer el puerto del backend.
  '/docs': forward,
  '/redoc': forward,
  '/openapi.json': forward,
}

export default defineConfig({
  plugins: [
    react(),
    // Solo en `vite` (desarrollo): http://localhost:5173/dev/movil
    devMovil(),
    VitePWA({
      registerType: 'autoUpdate',
      // Limpieza forzada: `PWA_RESET=1 npm run build` genera un service worker que se desinstala solo, borra la copia
      // guardada de la app y recarga las pestañas abiertas. Sirve cuando un teléfono se quedó con una versión vieja y
      // muestra la pantalla en blanco. Después se compila normal y el teléfono instala la versión buena.
      selfDestroying: process.env.PWA_RESET === '1',
      includeAssets: ['icons/apple-touch-icon.png'],
      manifest: {
        name: 'Multitec ERP',
        short_name: 'Multitec',
        description: 'ERP especializado en seguridad electrónica',
        theme_color: '#0a63e2',
        background_color: '#f5f6f8',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
    }),
  ],
  server: {
    // Escucha en IPv4 e IPv6: multitec.test (hosts) resuelve a 127.0.0.1 y Vite por defecto
    // solo escuchaba en [::1], así que http://multitec.test:5173 no conectaba.
    host: true,
    proxy,
    // Permite servir la app a través del túnel de ngrok (dominio *.ngrok-free.app,
    // distinto cada vez) además de localhost — sin esto Vite rechaza la petición
    // por el chequeo de Host contra DNS rebinding.
    allowedHosts: true,
  },
  // Versión compilada (la que usan los técnicos y la que va por el túnel): ~40 archivos en vez de
  // los cientos de módulos sueltos del modo desarrollo, y con el service worker de la PWA activo.
  preview: {
    host: true,
    proxy,
    allowedHosts: true,
    // Solo aquí y no en `server` (desarrollo): el modo dev inyecta scripts en línea para el HMR
    // y la CSP los bloquearía.
    headers: securityHeaders,
  },
})
