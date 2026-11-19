<?php

namespace App\Support;

use App\Models\AuditLog;
use App\Models\User;
use Illuminate\Http\Request;

/** Bitácora: quién hizo qué, cuándo y desde dónde. Nunca guarda claves ni tokens. */
class Audit
{
    private const SECRET = ['password', 'token', 'secret', 'clave', 'contrasena'];

    public static function log(
        string $action,
        ?User $user = null,
        ?string $email = null,
        ?string $entity = null,
        ?int $entityId = null,
        ?array $detail = null,
        ?Request $request = null,
        ?int $companyId = null,
    ): void {
        $safe = null;
        if ($detail) {
            $safe = array_filter($detail, function ($v, $k) {
                foreach (self::SECRET as $s) {
                    if (str_contains(strtolower((string) $k), $s)) {
                        return false;
                    }
                }
                return true;
            }, ARRAY_FILTER_USE_BOTH);
            $safe = mb_substr(json_encode($safe, JSON_UNESCAPED_UNICODE), 0, 2000) ?: null;
        }
        AuditLog::create([
            'company_id' => $companyId ?? $user?->company_id,
            'user_id' => $user?->id,
            'user_email' => $user?->email ?? $email,
            'action' => $action,
            'entity' => $entity,
            'entity_id' => $entityId,
            'detail' => $safe,
            'ip' => $request?->ip(),
            'created_at' => now(),
        ]);
    }
}
