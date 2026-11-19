<?php

namespace App\Http\Middleware;

use App\Models\Company;
use App\Models\User;
use App\Support\Access;
use App\Support\ApiException;
use App\Support\Audit;
use Closure;
use Firebase\JWT\JWT;
use Firebase\JWT\Key;
use Illuminate\Http\Request;

/** Valida el Bearer JWT (HS256) y deja al usuario y su empresa disponibles. Equivale a get_current_user. */
class JwtAuth
{
    /** Con la contraseña temporal sin cambiar, solo se puede ver el perfil y cambiarla. */
    private const PASSWORD_CHANGE_ALLOWED = ['api/auth/me', 'api/auth/change-password', 'api/auth/logout'];
    private const SUPPORT_READ_ONLY = 'Modo soporte de solo lectura: vuelve a entrar con «Permitir cambios» para modificar datos.';

    public function handle(Request $request, Closure $next)
    {
        $unauth = new ApiException(401, 'No se pudo validar las credenciales', ['WWW-Authenticate' => 'Bearer']);
        $token = $request->bearerToken();
        if (! $token) {
            throw new ApiException(401, 'Not authenticated', ['WWW-Authenticate' => 'Bearer']);
        }
        try {
            $payload = (array) JWT::decode($token, new Key(config('app.jwt_secret'), 'HS256'));
        } catch (\Throwable $e) {
            \Log::warning('JWT decode falló: '.get_class($e).' '.$e->getMessage());
            throw $unauth;
        }
        $user = User::with('company')->find((int) ($payload['sub'] ?? 0));
        if (! $user || ! $user->is_active) {
            \Log::warning('JWT usuario no válido: sub='.($payload['sub'] ?? 'null').' encontrado='.var_export((bool) $user, true));
            throw $unauth;
        }
        $reason = $user->company?->accessBlockReason();
        if ($reason) {
            throw new ApiException(403, $reason);
        }
        if ($user->must_change_password && ! in_array($request->path(), self::PASSWORD_CHANGE_ALLOWED, true)) {
            throw new ApiException(403, 'Debes cambiar tu contraseña temporal antes de continuar');
        }

        if (isset($payload['support_company'])) {
            $user = $this->supportUser($request, $user, $payload);
        } else {
            app()->instance('company_id', $user->company_id);
        }
        $request->attributes->set('user', $user);
        // Un técnico solo abre lo suyo: las rutas con project_id / client_id / visit_id se validan aquí (404 si no).
        if ($request->route()) {
            Access::enforce($user, $request->route()->parameters());
        }

        return $next($request);
    }

    /**
     * Modo soporte: el administrador de la plataforma entra a otra empresa como su administrador, por tiempo limitado.
     * El usuario se modifica SOLO en memoria (nunca se guarda: su cuenta real no cambia). En solo lectura, toda escritura
     * se rechaza; con cambios permitidos, cada escritura queda anotada en la auditoría de la empresa atendida.
     */
    private function supportUser(Request $request, User $user, array $payload): User
    {
        $ended = new ApiException(401, 'La sesión de soporte terminó', ['WWW-Authenticate' => 'Bearer']);
        if (! $user->is_platform_admin) {
            throw $ended;
        }
        $target = Company::find((int) $payload['support_company']);
        if (! $target) {
            throw $ended;
        }
        $allow = (bool) ($payload['support_write'] ?? false);
        $path = $request->path();
        $isWrite = ! in_array($request->method(), ['GET', 'HEAD', 'OPTIONS'], true) && $path !== 'api/auth/logout';
        if ($isWrite && (! $allow || str_starts_with($path, 'api/auth/') || str_starts_with($path, 'api/platform/'))) {
            throw new ApiException(403, self::SUPPORT_READ_ONLY);
        }
        app()->instance('company_id', $target->id);
        if ($isWrite) {
            Audit::log('support_change', $user, entity: 'support', detail: ['metodo' => $request->method(), 'ruta' => '/'.$path],
                request: $request, companyId: $target->id);
        }
        $user->company_id = $target->id;
        $user->setRelation('company', $target);
        $user->role = 'admin';
        $user->must_change_password = false;
        $user->support_mode = true;
        $user->support_write = $allow;
        $user->support_expires_at = date('c', (int) $payload['exp']);

        return $user;
    }
}
