<?php

namespace App\Http\Middleware;

use App\Support\ApiException;
use Closure;
use Illuminate\Http\Request;

/**
 * Solo el dueño de la plataforma (is_platform_admin). Actúa sobre TODAS las empresas, por eso el filtro por empresa se
 * apaga en estas rutas y cada escritura lleva su company_id explícito.
 */
class PlatformAdmin
{
    public function handle(Request $request, Closure $next)
    {
        $user = $request->attributes->get('user');
        if (! $user || ! $user->is_platform_admin) {
            throw new ApiException(403, 'Solo el administrador de la plataforma puede hacer esto');
        }
        app()->forgetInstance('company_id');

        return $next($request);
    }
}
