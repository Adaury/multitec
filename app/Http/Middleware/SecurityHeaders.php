<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;

/**
 * Cabeceras de seguridad. Mismo contenido que frontend/security-headers.ts y deploy/Caddyfile del sistema original.
 * La CSP es la segunda línea de defensa contra XSS: aunque se colara un script, solo cargan los del propio sitio y no
 * puede mandar datos a otro dominio (connect-src 'self'). Lo que ya trae su propia cabecera (p. ej. /uploads con su CSP
 * más estricta) se respeta: solo se pone lo que falta.
 */
class SecurityHeaders
{
    public const CSP = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
        ."media-src 'self' blob:; connect-src 'self'; "
        .'frame-src https://www.openstreetmap.org https://maps.google.com https://www.google.com; '
        ."worker-src 'self'; manifest-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'";

    public function handle(Request $request, Closure $next)
    {
        $response = $next($request);
        $h = $response->headers;
        $defaults = [
            'Content-Security-Policy' => self::CSP,
            'X-Content-Type-Options' => 'nosniff',
            'X-Frame-Options' => 'DENY',
            'Referrer-Policy' => 'strict-origin-when-cross-origin',
            // GPS del levantamiento, micrófono del asistente y cámara para fotos: solo este sitio.
            'Permissions-Policy' => 'geolocation=(self), microphone=(self), camera=(self)',
        ];
        if ($request->isSecure() || $request->header('x-forwarded-proto') === 'https') {
            $defaults['Strict-Transport-Security'] = 'max-age=2592000';
        }
        foreach ($defaults as $k => $v) {
            if (! $h->has($k)) {
                $h->set($k, $v);
            }
        }
        // La API nunca se guarda en cachés compartidas: lleva datos de una empresa.
        if ($request->is('api/*')) {
            $h->set('Cache-Control', 'no-store, private');
        }

        return $response;
    }
}
