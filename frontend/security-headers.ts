// Cabeceras de seguridad de la versión compilada (`vite preview`, la que usan los técnicos y el túnel).
// deploy/Caddyfile repite las mismas para producción: si cambias una, cámbiala allá también.
//
// La CSP es la segunda línea de defensa contra XSS: aunque se colara un script, solo cargan los
// del propio sitio y no puede mandar datos a otro dominio (connect-src 'self'). El build no tiene
// scripts en línea, por eso script-src no necesita 'unsafe-inline'.
export const CSP = [
  "default-src 'self'",
  "script-src 'self'",
  // React pinta estilos con el atributo style="..."; sin 'unsafe-inline' no se verían.
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "media-src 'self' blob:",
  "connect-src 'self'",
  // Mapas incrustados del proyecto (ver src/lib/maps.ts → embedUrl).
  'frame-src https://www.openstreetmap.org https://maps.google.com https://www.google.com',
  "worker-src 'self'",
  "manifest-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join('; ')

export const securityHeaders: Record<string, string> = {
  'Content-Security-Policy': CSP,
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  // GPS del levantamiento, micrófono del asistente y cámara para fotos: solo este sitio.
  'Permissions-Policy': 'geolocation=(self), microphone=(self), camera=(self)',
}
