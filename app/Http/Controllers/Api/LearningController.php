<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;

/**
 * Aprendizaje de la IA (eventos de corrección y ejemplos de dictado). En el original, el sistema registraba las ediciones que los
 * usuarios hacían sobre lo generado por IA y de ahí sacaba candidatos a reglas y sinónimos. Esas tablas no se migraron y esta versión
 * no registra esos eventos, así que las tres rutas existen (la pantalla no falla) pero responden vacío. Es una limitación conocida,
 * no un error: nada se está aprendiendo de las correcciones.
 */
class LearningController extends Controller
{
    public function events()
    {
        return [];
    }

    public function voiceExamples()
    {
        return [];
    }

    public function analyze()
    {
        return ['accessory_candidates' => [], 'stale_rule_candidates' => [], 'synonym_candidates' => []];
    }
}
