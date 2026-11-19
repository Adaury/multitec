<?php

use App\Http\Middleware\JwtAuth;
use App\Http\Middleware\RequireRole;
use App\Support\ApiException;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
use Illuminate\Http\Request;
use Illuminate\Validation\ValidationException;
use Symfony\Component\HttpKernel\Exception\HttpExceptionInterface;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__.'/../routes/web.php',
        api: __DIR__.'/../routes/api.php',
        commands: __DIR__.'/../routes/console.php',
        health: '/up',
    )
    ->withMiddleware(function (Middleware $middleware): void {
        $middleware->alias(['jwt' => JwtAuth::class, 'role' => RequireRole::class, 'platform' => \App\Http\Middleware\PlatformAdmin::class]);
        // Confianza en proxies: se decide con TRUSTED_PROXIES (ver AppServiceProvider). Por defecto NINGUNA: si se confiara
        // en «*», cualquiera podría falsificar X-Forwarded-For y esquivar los límites de intentos por IP.
        $middleware->append(\App\Http\Middleware\SecurityHeaders::class);
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        $exceptions->shouldRenderJsonWhen(fn (Request $request) => $request->is('api/*') || $request->expectsJson());

        // Los errores esperados (sin sesión, no encontrado, dato inválido…) no se anotan en el registro: solo lo inesperado.
        $exceptions->dontReport([ApiException::class, ValidationException::class]);

        // Mismo formato de error que FastAPI: {"detail": ...}
        $exceptions->render(function (ApiException $e) {
            return response()->json(['detail' => $e->getMessage()], $e->status, $e->headers);
        });
        $exceptions->render(function (ValidationException $e) {
            $detail = [];
            foreach ($e->errors() as $field => $msgs) {
                foreach ($msgs as $m) {
                    $detail[] = ['loc' => ['body', $field], 'msg' => $m, 'type' => 'value_error'];
                }
            }
            return response()->json(['detail' => $detail], 422);
        });
        $exceptions->render(function (HttpExceptionInterface $e, Request $request) {
            if ($request->is('api/*')) {
                $msg = match (true) {
                    $e->getStatusCode() === 404 => 'Not Found',
                    $e->getStatusCode() === 429 => 'Demasiados intentos. Espera unos minutos e inténtalo de nuevo.',
                    default => $e->getMessage() ?: 'Error',
                };
                return response()->json(['detail' => $msg], $e->getStatusCode(), $e->getHeaders());
            }
        });
        // Cualquier otro error en la API: en producción nunca se muestran rutas, consultas ni trazas (ya quedó en el log).
        $exceptions->render(function (\Throwable $e, Request $request) {
            if ($request->is('api/*') && ! config('app.debug')) {
                return response()->json(['detail' => 'Error interno del servidor. Inténtalo de nuevo; si sigue, avisa a soporte.'], 500);
            }
        });
    })->create();
