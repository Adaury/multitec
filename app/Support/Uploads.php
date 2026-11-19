<?php

namespace App\Support;

class Uploads
{
    /** Carpetas anteriores a multi-empresa (sin prefijo c{id}/): sus archivos son de la empresa 1, la original. */
    public const LEGACY_DIRS = ['surveys', 'tickets', 'logbook', 'company'];

    /**
     * ¿Esta ruta de archivo es de la empresa? `uploads/c{id}/...` es de esa empresa; sin prefijo (archivos de antes de
     * multi-empresa) es de la empresa 1. Nunca acepta rutas que suban de carpeta.
     */
    public static function owns(?string $path, ?int $companyId = null): bool
    {
        $cid = $companyId ?? (int) app('company_id');
        $p = ltrim(str_replace('\\', '/', (string) $path), '/');
        if ($p === '' || str_contains($p, '..') || ! str_starts_with($p, 'uploads/')) {
            return false;
        }
        if (preg_match('#^uploads/c(\d+)/#', $p, $m)) {
            return (int) $m[1] === $cid;
        }

        return $cid === 1;
    }
}
