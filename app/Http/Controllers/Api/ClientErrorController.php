<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;

/**
 * Errores de arranque que reporta el navegador (boot-check.js). Es PÚBLICO a propósito (la persona todavía no entró:
 * justo falla al abrir), así que se protege: límite por IP (en la ruta), tamaños topados, y el texto no puede
 * fabricar líneas falsas en el log (sin saltos de línea ni caracteres de control).
 */
class ClientErrorController extends Controller
{
    private function oneLine($v, int $max): string
    {
        return mb_substr((string) preg_replace('/[\x00-\x1f\x7f]+/', ' ', is_scalar($v) ? (string) $v : ''), 0, $max);
    }

    public function report(Request $r)
    {
        Log::warning(sprintf('Error en el navegador [%s] %s | %s | %s | UA=%s | IP=%s',
            $this->oneLine($r->input('kind', 'error'), 30), $this->oneLine($r->input('message'), 500),
            $this->oneLine($r->input('detail'), 1500), $this->oneLine($r->input('url'), 300),
            $this->oneLine($r->userAgent(), 200), $r->ip()));

        return response()->noContent();
    }
}
