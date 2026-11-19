<?php

namespace App\Support;

/** Tipos de punto marcados sobre las fotos del levantamiento. */
class SurveyPoints
{
    /** clave => patrón que reconoce el tipo en una etiqueta (null = "otro"). */
    public const KINDS = [
        'camara' => '/c[áa]mara|cctv|\bdomo\b|bullet|\bptz\b/iu',
        'grabador' => '/\bnvr\b|\bdvr\b|grabador/iu',
        'switch' => '/\bswitch(es)?\b/iu',
        'gabinete' => '/gabinete|\brack\b/iu',
        'punto_red' => '/punto de red|access point|\brouter\b|\bwifi\b|\bwi-fi\b|\bap\b/iu',
        'acceso' => '/cerradura|lector|control de acceso|huella|chapa|cerco/iu',
        'sensor' => '/sensor|alarma|sirena|panel de alarma|detector/iu',
        'otro' => null,
    ];

    public static function keys(): array
    {
        return array_keys(self::KINDS);
    }

    public static function infer(?string $label): string
    {
        foreach (self::KINDS as $key => $pattern) {
            if ($pattern && preg_match($pattern, (string) $label)) {
                return $key;
            }
        }

        return 'otro';
    }

    public static function markerKind(?string $kind, ?string $label): string
    {
        return $kind && array_key_exists($kind, self::KINDS) ? $kind : self::infer($label);
    }

    public const LABELS = [
        'camara' => 'Cámara', 'grabador' => 'NVR / DVR', 'switch' => 'Switch', 'gabinete' => 'Gabinete / rack',
        'punto_red' => 'Punto de red / WiFi', 'acceso' => 'Cerradura / lector', 'sensor' => 'Sensor / alarma', 'otro' => 'Otro',
    ];

    /** Cuántos puntos hay marcados por tipo en todas las fotos del levantamiento. @return array<string,int> */
    public static function markerCounts(int $projectId): array
    {
        $survey = \App\Models\Survey::with('assets.markers')->where('project_id', $projectId)->first();
        $counts = [];
        foreach ($survey?->assets ?? [] as $asset) {
            if ($asset->kind !== 'photo') {
                continue;
            }
            foreach ($asset->markers as $m) {
                $k = self::markerKind($m->kind, $m->label);
                $counts[$k] = ($counts[$k] ?? 0) + 1;
            }
        }

        return $counts;
    }

    /** Bloque de texto para el contexto de la IA: cantidades exactas, no una interpretación. */
    public static function context(array $counts): string
    {
        $lines = [];
        foreach ($counts as $k => $n) {
            if ($n) {
                $lines[] = '- '.(self::LABELS[$k] ?? 'Otro').": $n";
            }
        }

        return $lines ? "\n== Puntos marcados en las fotos del levantamiento (cantidades EXACTAS: úsalas tal cual) ==\n".implode("\n", $lines) : '';
    }
}
