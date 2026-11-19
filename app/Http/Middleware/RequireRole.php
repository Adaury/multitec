<?php

namespace App\Http\Middleware;

use App\Support\ApiException;
use Closure;
use Illuminate\Http\Request;

class RequireRole
{
    public function handle(Request $request, Closure $next, string ...$roles)
    {
        $user = $request->attributes->get('user');
        if (! $user || ! in_array($user->role, $roles, true)) {
            throw new ApiException(403, 'No tienes permisos para esta acción');
        }

        return $next($request);
    }
}
