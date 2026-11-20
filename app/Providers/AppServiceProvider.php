<?php

namespace App\Providers;

use Illuminate\Cache\RateLimiting\Limit;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        //
    }

    /**
     * Límites de intentos. Cada uno tiene su PROPIO contador: con `throttle:10,1` (sin nombre) todas las rutas limitadas
     * comparten el mismo contador por IP, y alguien que abre el portal 11 veces bloquearía el inicio de sesión de toda
     * su oficina.
     */
    public function boot(): void
    {
        // Proxies de confianza (X-Forwarded-For): vacío = ninguno (la IP es la de la conexión). Detrás de Cloudflare u otro
        // proxy, se listan sus direcciones aquí (o «*» solo si el servidor NO es alcanzable sin pasar por ese proxy).
        $trusted = trim((string) config('app.trusted_proxies'));
        if ($trusted !== '') {
            \Illuminate\Http\Middleware\TrustProxies::at($trusted === '*' ? '*' : array_map('trim', explode(',', $trusted)));
        }

        $byIp = fn (Request $r) => $r->ip();
        $byUserOrIp = fn (Request $r) => (string) ($r->attributes->get('user')?->id ?? $r->ip());

        RateLimiter::for('login', fn (Request $r) => Limit::perMinute(10)->by($byIp($r)));
        RateLimiter::for('ai', fn (Request $r) => Limit::perMinute(30)->by('ai:'.$byUserOrIp($r)));
        RateLimiter::for('refresh', fn (Request $r) => Limit::perMinute(30)->by($byIp($r)));
        RateLimiter::for('change-password', fn (Request $r) => Limit::perMinute(10)->by($byUserOrIp($r)));
        RateLimiter::for('geo', fn (Request $r) => Limit::perMinute(30)->by($byUserOrIp($r)));
        RateLimiter::for('portal', fn (Request $r) => Limit::perMinute(30)->by($byIp($r)));
        RateLimiter::for('signup', fn (Request $r) => Limit::perHour(5)->by($byIp($r)));
        RateLimiter::for('signup-check', fn (Request $r) => Limit::perMinute(30)->by('check:'.$byIp($r)));
        RateLimiter::for('experience', fn (Request $r) => Limit::perHour(5)->by($byIp($r)));
        RateLimiter::for('client-errors', fn (Request $r) => Limit::perMinute(20)->by($byIp($r)));
    }
}
