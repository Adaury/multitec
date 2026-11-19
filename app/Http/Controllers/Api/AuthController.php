<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\RefreshToken;
use App\Models\User;
use App\Support\ApiException;
use App\Support\Audit;
use App\Support\PasswordPolicy;
use Firebase\JWT\JWT;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

class AuthController extends Controller
{
    private const COOKIE = 'multitec_rt';
    private const MAX_FAILS = 5;       // intentos fallidos antes de bloquear (mi valor: ajustable)
    private const LOCK_SECONDS = 900;  // 15 minutos

    // ---- helpers -------------------------------------------------------

    private function hashPassword(string $plain): string
    {
        return password_hash($plain, PASSWORD_BCRYPT);
    }

    /** password_verify acepta los hashes $2b$ que generó Python (bcrypt). */
    private function verifyPassword(string $plain, string $hash): bool
    {
        if (strlen($plain) > 72) {
            return false;
        }
        return password_verify($plain, $hash);
    }

    private function accessToken(int $userId): string
    {
        $minutes = (int) config('app.access_token_minutes', 60);

        return JWT::encode(['sub' => (string) $userId, 'exp' => time() + $minutes * 60], config('app.jwt_secret'), 'HS256');
    }

    private function newRefreshToken(Request $r, int $userId): string
    {
        $raw = rtrim(strtr(base64_encode(random_bytes(48)), '+/', '-_'), '=');
        RefreshToken::create([
            'user_id' => $userId,
            'token_hash' => hash('sha256', $raw),
            'expires_at' => Carbon::now()->addDays((int) config('app.refresh_token_days', 30)),
            'created_at' => Carbon::now(),
            'user_agent' => Str::limit((string) $r->userAgent(), 255, ''),
            'ip' => $r->ip(),
            'last_used_at' => Carbon::now(),
        ]);

        return $raw;
    }

    private function tokenResponse(Request $r, int $userId, ?string $refresh = null): Response
    {
        $refresh ??= $this->newRefreshToken($r, $userId);
        $secure = $r->isSecure() || $r->header('x-forwarded-proto') === 'https';
        $cookie = cookie(self::COOKIE, $refresh, (int) config('app.refresh_token_days', 30) * 1440, '/api/auth', null, $secure, true, false, 'Strict');

        return response([
            'access_token' => $this->accessToken($userId),
            'refresh_token' => $refresh,
            'token_type' => 'bearer',
        ])->withCookie($cookie);
    }

    private function incomingRefresh(Request $r): ?string
    {
        return $r->input('refresh_token') ?: $r->cookie(self::COOKIE);
    }

    private function revokeAll(int $userId): void
    {
        RefreshToken::where('user_id', $userId)->where('revoked', false)->update(['revoked' => true]);
    }

    // ---- endpoints -----------------------------------------------------

    public function login(Request $r)
    {
        // Igual que OAuth2PasswordRequestForm: campos "username" y "password" (formulario).
        $username = mb_strtolower((string) $r->input('username', $r->input('email', '')));
        $password = (string) $r->input('password', '');
        $key = 'login:'.sha1($username.'|'.$r->ip());
        $keyAcct = 'login:'.sha1($username);

        foreach ([$key, $keyAcct] as $k) {
            if ((int) Cache::get($k.':n', 0) >= self::MAX_FAILS) {
                Audit::log('login_blocked', email: $username, request: $r);
                throw new ApiException(429, 'Demasiados intentos fallidos. Espera unos minutos e inténtalo de nuevo.', ['Retry-After' => (string) self::LOCK_SECONDS]);
            }
        }

        $user = User::with('company')->where('email', $username)->first();
        // Corre siempre, exista o no el correo, para que el tiempo no delate qué cuentas existen.
        $ok = $this->verifyPassword($password, $user->hashed_password ?? '$2y$12$abcdefghijklmnopqrstuuA2cGfVf3pXq2o1HfZq6cC7sU6oQ3O6a');
        if (! $user || ! $ok) {
            foreach ([$key, $keyAcct] as $k) {
                Cache::add($k.':n', 0, self::LOCK_SECONDS);
                Cache::increment($k.':n');
            }
            Audit::log('login_failed', email: $username, request: $r, companyId: $user?->company_id);
            throw new ApiException(401, 'Correo o contraseña incorrectos');
        }
        foreach ([$key, $keyAcct] as $k) {
            Cache::forget($k.':n');
        }
        if (! $user->is_active) {
            Audit::log('login_inactive', $user, request: $r);
            throw new ApiException(403, 'Usuario inactivo');
        }
        $reason = $user->company ? $user->company->accessBlockReason() : \App\Models\Company::SUSPENDED;
        if ($reason) {
            Audit::log('login_company_blocked', $user, request: $r);
            throw new ApiException(403, $reason);
        }
        $user->forceFill(['last_login_at' => Carbon::now()])->save();
        Audit::log('login', $user, request: $r);

        return $this->tokenResponse($r, $user->id);
    }

    public function refresh(Request $r)
    {
        $raw = $this->incomingRefresh($r);
        $row = $raw ? RefreshToken::where('token_hash', hash('sha256', $raw))->first() : null;
        if ($row && $row->revoked) {
            // Un token ya rotado que vuelve a usarse = posible robo: se cierra toda la sesión.
            $this->revokeAll($row->user_id);
            $row = null;
        }
        if ($row && $row->expires_at->lt(Carbon::now())) {
            $row = null;
        }
        if (! $row) {
            throw new ApiException(401, 'Refresh token inválido o expirado');
        }
        $user = User::with('company')->find($row->user_id);
        if (! $user || ! $user->is_active) {
            throw new ApiException(401, 'Usuario inactivo');
        }
        $reason = $user->company ? $user->company->accessBlockReason() : \App\Models\Company::SUSPENDED;
        if ($reason) {
            throw new ApiException(403, $reason);
        }
        $row->update(['revoked' => true]); // rotación: un solo uso

        return $this->tokenResponse($r, $user->id);
    }

    public function logout(Request $r)
    {
        $raw = $this->incomingRefresh($r);
        if ($raw) {
            RefreshToken::where('token_hash', hash('sha256', $raw))->update(['revoked' => true]);
        }

        return response()->noContent()->withCookie(cookie()->forget(self::COOKIE, '/api/auth'));
    }

    public function me(Request $r)
    {
        return $r->attributes->get('user')->toCurrent();
    }

    public function updateMe(Request $r)
    {
        $user = $r->attributes->get('user');
        $name = trim((string) $r->input('name', ''));
        if ($name === '' || mb_strlen($name) > 120) {
            throw new ApiException(422, 'El nombre no puede estar vacío');
        }
        $user->name = $name;
        if ($r->has('assistant_alias')) {
            $alias = trim((string) $r->input('assistant_alias'));
            $user->assistant_alias = $alias === '' ? null : mb_substr($alias, 0, 60);
        }
        $user->save();

        return $user->fresh('company')->toCurrent();
    }

    public function changePassword(Request $r)
    {
        $user = $r->attributes->get('user');
        $current = (string) $r->input('current_password', '');
        $new = (string) $r->input('new_password', '');
        if (! $this->verifyPassword($current, $user->hashed_password)) {
            throw new ApiException(400, 'La contraseña actual es incorrecta');
        }
        if ($new === $current) {
            throw new ApiException(400, 'La nueva contraseña debe ser distinta de la actual');
        }
        PasswordPolicy::enforce($new);
        DB::transaction(function () use ($user, $new, $r) {
            $user->update(['hashed_password' => $this->hashPassword($new), 'must_change_password' => false]);
            $this->revokeAll($user->id);
            Audit::log('password_changed', $user, request: $r);
        });

        return $this->tokenResponse($r, $user->id);
    }

    public function sessions(Request $r)
    {
        $user = $r->attributes->get('user');
        $mine = $r->cookie(self::COOKIE);
        $currentHash = $mine ? hash('sha256', $mine) : null;

        return RefreshToken::where('user_id', $user->id)->where('revoked', false)
            ->where('expires_at', '>', Carbon::now())->orderByDesc('created_at')->get()
            ->map(fn ($s) => [
                'id' => $s->id, 'user_agent' => $s->user_agent, 'ip' => $s->ip,
                'created_at' => $s->created_at, 'last_used_at' => $s->last_used_at,
                'current' => $s->token_hash === $currentHash,
            ])->values();
    }

    public function logoutAll(Request $r)
    {
        $this->revokeAll($r->attributes->get('user')->id);
        Audit::log('logout_all', $r->attributes->get('user'), request: $r);

        return response()->noContent()->withCookie(cookie()->forget(self::COOKIE, '/api/auth'));
    }
}
