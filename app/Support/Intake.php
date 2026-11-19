<?php

namespace App\Support;

use Illuminate\Support\Facades\Log;

/**
 * Alta rápida de un levantamiento: saca nombre, teléfono y tipo de lo que el usuario dice o escribe
 * («Juan Pérez, 809 555 1234, cámaras»). Primero reglas deterministas (teléfono y tipo se detectan sin IA); la IA solo ayuda a
 * separar el nombre y a entender frases libres. Si la IA no está configurada o falla, el resultado sale igual de las reglas.
 */
class Intake
{
    private const SCHEMA = [
        'type' => 'object',
        'properties' => ['name' => ['type' => 'string'], 'company' => ['type' => 'string'], 'phone' => ['type' => 'string'], 'survey_type' => ['type' => 'string']],
        'required' => ['name', 'company', 'phone', 'survey_type'],
    ];

    /** Palabra clave del tipo -> sinónimos que dice la gente (la clave se busca dentro del nombre del tipo). */
    /** Sinónimos por tipo de levantamiento (también los usa la conversación del asistente). */
    public const SYNONYMS_PUBLIC = self::SYNONYMS;

    private const SYNONYMS = [
        'cámara' => ['camara', 'camaras', 'cctv', 'video', 'vigilancia', 'dvr', 'nvr'],
        'alarma' => ['alarma', 'alarmas', 'sensor', 'sensores', 'sirena', 'panico'],
        'acceso' => ['acceso', 'huella', 'biometrico', 'tarjeta', 'torniquete', 'cerradura', 'marcador'],
        'cerco' => ['cerco', 'electrico', 'electrificado', 'perimetral'],
        'red' => ['red', 'redes', 'cableado', 'wifi', 'internet', 'fibra', 'router', 'switch'],
        'interco' => ['intercomunicador', 'interfon', 'interfono', 'portero', 'videoportero', 'citofono'],
    ];

    private const FILLERS = '/^(?:el\s+cliente\s+(?:es|se\s+llama)|la\s+cliente\s+(?:es|se\s+llama)|cliente|se\s+llama|mi\s+cliente\s+es|el\s+nombre\s+es|nombre|llamado|es)\s+/iu';
    private const PHONE_CUT = '/[,;.]|\s+(?:tel[eé]fono|tel|n[uú]mero|celular|cel|whatsapp|su\s+n[uú]mero|y\s+su|para|tipo|de\s+tipo|quiere|necesita)\b/iu';

    /** Minúsculas y sin tildes, para comparar lo dictado sin importar la ortografía. */
    public static function fold(string $t): string
    {
        return strtr(mb_strtolower($t), ['á' => 'a', 'é' => 'e', 'í' => 'i', 'ó' => 'o', 'ú' => 'u', 'ü' => 'u', 'ñ' => 'n']);
    }

    /** El número más largo de 7 a 15 dígitos, formateado a la dominicana si tiene 10. */
    public static function extractPhone(string $text): string
    {
        $best = '';
        preg_match_all('/\+?\d[\d\s().-]{5,}\d/', $text, $m);
        foreach ($m[0] as $chunk) {
            $d = preg_replace('/\D/', '', $chunk);
            if (strlen($d) >= 7 && strlen($d) <= 15 && strlen($d) > strlen($best)) {
                $best = $d;
            }
        }
        if (strlen($best) === 11 && str_starts_with($best, '1')) {
            $best = substr($best, 1);
        }

        return strlen($best) === 10 ? substr($best, 0, 3).'-'.substr($best, 3, 3).'-'.substr($best, 6) : $best;
    }

    /** El tipo de la lista que mejor encaja con lo que se dijo; '' si ninguno. */
    public static function matchSurveyType(string $text, array $types): string
    {
        $folded = self::fold($text);
        preg_match_all('/[a-z0-9]+/', $folded, $w);
        $words = array_flip($w[0]);
        foreach ($types as $label) {
            if (str_contains($folded, self::fold((string) $label))) {
                return (string) $label;
            }
        }
        foreach (self::SYNONYMS as $key => $syns) {
            $hit = false;
            foreach ($syns as $s) {
                if (isset($words[$s]) || (strlen($s) > 5 && str_contains($folded, $s))) {
                    $hit = true;
                    break;
                }
            }
            if ($hit) {
                foreach ($types as $label) {
                    if (str_contains(self::fold((string) $label), self::fold($key))) {
                        return (string) $label;
                    }
                }
            }
        }

        return '';
    }

    /** El nombre al inicio de la frase, sin muletillas ni lo que viene después (teléfono, tipo). */
    public static function extractName(string $text): string
    {
        $c = preg_replace(self::FILLERS, '', trim($text));
        $c = preg_split('/\d/', (string) $c, 2)[0];
        $c = preg_split(self::PHONE_CUT, (string) $c, 2)[0];
        $c = trim((string) preg_replace('/\s+/u', ' ', (string) $c), " ,.;:-");

        return $c !== '' && $c === mb_strtolower($c) ? mb_convert_case($c, MB_CASE_TITLE) : $c;
    }

    public static function rules(string $text, array $types): array
    {
        return ['name' => self::extractName($text), 'company' => '', 'phone' => self::extractPhone($text), 'survey_type' => self::matchSurveyType($text, $types)];
    }

    public static function parse(string $text, array $types): array
    {
        $result = self::rules($text, $types) + ['ai_used' => false];
        if (trim($text) === '' || ! Gemini::configured()) {
            return $result;
        }
        $prompt = "Del siguiente texto dicho por un técnico de seguridad electrónica, extrae los datos de su cliente. Copia lo que se dijo; no inventes nada:\n"
            ."- name: nombre y apellido de la persona (sin muletillas como \"el cliente se llama\").\n"
            ."- company: empresa o negocio, o \"\" si no se menciona.\n"
            ."- phone: teléfono tal como se dijo, o \"\" si no hay.\n"
            .'- survey_type: uno de '.json_encode(array_values($types), JSON_UNESCAPED_UNICODE).", o \"\" si no encaja.\n\nTexto: $text";
        try {
            $d = Gemini::json([['role' => 'user', 'content' => $prompt]], self::SCHEMA, ['temperature' => 0]);
        } catch (ApiException) {
            Log::warning('Alta rápida: la IA no respondió, se usan solo las reglas');

            return $result;
        }
        $aiName = trim((string) ($d['name'] ?? ''));
        $aiCompany = trim((string) ($d['company'] ?? ''));
        if ($aiName !== '' && $result['name'] === '') {
            $result['name'] = $aiName;
        } elseif ($aiName !== '' && mb_strlen($aiName) < mb_strlen($result['name']) && str_contains(self::fold($result['name']), self::fold($aiName))) {
            $result['name'] = $aiName; // la IA recortó restos de la frase que las reglas dejaron
        }
        if ($aiCompany !== '') {
            $result['company'] = $aiCompany;
        }
        if ($result['phone'] === '') {
            $result['phone'] = self::extractPhone((string) ($d['phone'] ?? ''));
        }
        $aiType = trim((string) ($d['survey_type'] ?? ''));
        if ($result['survey_type'] === '' && in_array($aiType, $types, true)) {
            $result['survey_type'] = $aiType;
        }
        $result['ai_used'] = true;

        return $result;
    }
}
