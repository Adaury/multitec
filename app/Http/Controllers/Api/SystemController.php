<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use Illuminate\Support\Facades\DB;

class SystemController extends Controller
{
    /**
     * Salud del sistema para el indicador de la app. overall: ok | degraded (se puede trabajar sin IA) | down (sin
     * base de datos). La IA y la voz todavía no están migradas a esta versión: se reportan como no disponibles, y
     * el sistema queda en «degraded» (se trabaja a mano), que es la verdad.
     */
    public function status()
    {
        $started = microtime(true);
        try {
            DB::select('SELECT 1');
            $database = true;
        } catch (\Throwable) {
            $database = false;
        }

        // No se llama a Google en cada consulta de estado (cuesta cuota y tiempo): basta con que haya clave.
        $ready = \App\Support\Gemini::configured();
        $ai = ['reachable' => $ready, 'model' => $ready ? (string) config('services.gemini.model') : 'IA no configurada', 'installed' => $ready, 'warm' => $ready];

        return [
            // ok = todo listo; degraded = se puede trabajar pero sin IA; down = sin base de datos (igual que el original).
            'overall' => ! $database ? 'down' : ($ready ? 'ok' : 'degraded'),
            'api' => true,
            'database' => $database,
            'ai' => $ai,
            'voice_loaded' => $ready,
            'checked_in_ms' => (int) round((microtime(true) - $started) * 1000),
        ];
    }
}
