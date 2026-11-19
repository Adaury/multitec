<?php

namespace App\Support;

use Illuminate\Support\Facades\Log;

/**
 * Conversación del Inicio: el asistente pregunta «¿qué toca hoy?» y entiende lo que el técnico contesta ("un levantamiento de cámaras
 * para Juan Pérez", "continuar con la ferretería", "qué tengo hoy"). Primero reglas (instantáneas y predecibles); la IA solo entra
 * cuando las reglas no reconocen la frase, con una respuesta mínima. Si falla, se pide repetir: nunca se inventa una acción.
 */
class Conversation
{
    public const INTENTS = ['new_survey', 'open_project', 'agenda', 'quotes', 'tickets', 'none'];
    public const PROMPT_VOICE = 'Un técnico le dice a su asistente qué va a hacer hoy. Frases como: un levantamiento de cámaras para Juan Pérez, '
        .'continuar con Ferretería López, qué tengo hoy, cotizar una alarma, atender un ticket, visitar a don Ramón, control de acceso, cerco eléctrico, redes.';

    private const TICKET = ['ticket', 'tickets', 'soporte', 'averia', 'averias', 'reparar', 'reparacion', 'garantia', 'falla'];
    private const CONTINUE = ['continuar', 'continuo', 'seguir', 'sigo', 'retomar', 'retomo', 'terminar', 'termino', 'abrir', 'abre'];
    private const NEW = ['levantamiento', 'levantamientos', 'levantar', 'cotizar', 'cotizarle', 'instalar', 'instalacion', 'instalarle', 'presupuesto',
        'nuevo', 'nueva', 'medir', 'medicion', 'visitar', 'ir donde', 'pasar donde', 'ir a casa', 'pasar por'];
    private const QUOTES = ['cotizaciones', 'pendientes de aprobar', 'esperando respuesta'];
    private const AGENDA = ['agenda', 'calendario', 'visitas', 'visita', 'pendiente', 'pendientes'];
    private const AGENDA_PHRASES = ['que tengo', 'que hay', 'que toca', 'que me toca', 'como esta el dia', 'para hoy'];
    private const NONE_PHRASES = ['nada', 'ninguna', 'solo viendo', 'solo mirando', 'despues', 'luego', 'ahora no'];
    private const NAME_STOP = ['de', 'del', 'en', 'y', 'que', 'con', 'para', 'por', 'un', 'una', 'el', 'la', 'los', 'las', 'hoy', 'manana', 'tipo', 'su', 'al', 'a', 'quiere', 'necesita', 'tiene'];
    private const TITLES = '(?:se[nñ]or|se[nñ]ora|don|do[nñ]a|doctor|doctora|ingeniero|ingeniera|licenciado|licenciada)';
    private const SCHEMA = [
        'type' => 'object',
        'properties' => ['intent' => ['type' => 'string', 'enum' => self::INTENTS], 'client' => ['type' => 'string']],
        'required' => ['intent', 'client'],
    ];

    private static function typeWords(): array
    {
        static $w;

        return $w ??= array_merge(['camara', 'camaras', 'alarma', 'alarmas', 'acceso', 'cerco', 'red', 'redes', 'seguridad', 'sistema', 'levantamiento', 'cotizacion', 'instalacion'],
            ...array_values(Intake::SYNONYMS_PUBLIC));
    }

    private static function words(string $folded): array
    {
        preg_match_all('/[a-z0-9]+/', $folded, $m);

        return $m[0];
    }

    private static function hasWord(string $folded, array $words): bool
    {
        $tokens = array_flip(self::words($folded));
        foreach ($words as $w) {
            if (str_contains($w, ' ') ? str_contains($folded, $w) : isset($tokens[$w])) {
                return true;
            }
        }

        return false;
    }

    /** El nombre del cliente dentro de una frase libre: lo que sigue al último marcador («para», «el cliente», «se llama»…). */
    public static function extractClientName(string $text): string
    {
        $t = self::TITLES;
        // «a» solo cuenta si le sigue un tratamiento o un nombre propio ("visitar a don Ramón"): si no, «voy a medir» daría el cliente «Medir».
        $rx = '/\b(?:para\s+(?:el|la)\s+client[ea]|(?:el|la)\s+client[ea](?:\s+se\s+llama|\s+es)?|se\s+llama|casa\s+de|donde|para|con|'
            ."a(?=\\s+(?:(?:el|la)\\s+)?$t\\b)|a(?=\\s+(?-i:[A-ZÁÉÍÓÚÑ])))\\s+(?:(?:el|la|del)\\s+)?(?:$t\\s+)?/iu";
        $best = '';
        if (preg_match_all($rx, $text, $ms, PREG_OFFSET_CAPTURE)) {
            foreach ($ms[0] as [$m, $off]) {
                $words = [];
                foreach (preg_split('/\s+/u', trim(substr($text, $off + strlen($m)))) ?: [] as $raw) {
                    $word = trim($raw, ",.;:¿?¡!\"'");
                    $f = Intake::fold($word);
                    if ($word === '' || in_array($f, self::NAME_STOP, true) || in_array($f, self::typeWords(), true) || preg_match('/\d/', $word)) {
                        break;
                    }
                    $words[] = $word;
                    if (count($words) === 4) {
                        break;
                    }
                }
                $cand = implode(' ', $words);
                if (mb_strlen($cand) >= 3) {
                    $best = $cand; // gana el último marcador: «levantamiento para cámaras para Juan Pérez»
                }
            }
        }

        return $best !== '' && $best === mb_strtolower($best) ? mb_convert_case($best, MB_CASE_TITLE) : $best;
    }

    /** El proyecto abierto cuyo cliente se nombra en la frase (todas las palabras significativas del nombre, o al menos dos). */
    public static function matchProject(string $text, array $projects): ?array
    {
        $tokens = array_flip(self::words(Intake::fold($text)));
        $best = null;
        foreach ($projects as $p) {
            $name = array_values(array_filter(self::words(Intake::fold($p['client_name'])), fn ($t) => strlen($t) >= 3));
            if (! $name) {
                continue;
            }
            $hits = count(array_filter($name, fn ($t) => isset($tokens[$t])));
            if (($hits === count($name) || $hits >= 2) && ($best === null || $hits > $best[0])) {
                $best = [$hits, $p];
            }
        }

        return $best[1] ?? null;
    }

    public static function classifyByRules(string $text): ?string
    {
        $f = Intake::fold($text);
        if (trim($f) === '') {
            return null;
        }
        if (self::hasWord($f, self::TICKET)) {
            return 'tickets';
        }
        if (self::hasWord($f, self::CONTINUE)) {
            return 'open_project';
        }
        foreach (self::QUOTES as $p) {
            if (str_contains($f, $p)) {
                return 'quotes';
            }
        }
        if (self::hasWord($f, self::NEW)) {
            return 'new_survey';
        }
        if (self::hasWord($f, self::AGENDA)) {
            return 'agenda';
        }
        foreach (self::AGENDA_PHRASES as $p) {
            if (str_contains($f, $p)) {
                return 'agenda';
            }
        }
        // Decir solo el tipo de trabajo («unas cámaras para…») también es pedir un levantamiento.
        if (array_intersect(self::words($f), array_merge(...array_values(Intake::SYNONYMS_PUBLIC)))) {
            return 'new_survey';
        }
        foreach (self::NONE_PHRASES as $p) {
            if (str_contains($f, $p)) {
                return 'none';
            }
        }

        return null;
    }

    /** @return array{0: ?string, 1: string} [intención, cliente]; [null, ''] si la IA no está o falla */
    private static function classifyWithModel(string $text): array
    {
        if (! Gemini::configured()) {
            return [null, ''];
        }
        $prompt = "Un técnico de seguridad electrónica le dice a su asistente qué quiere hacer hoy. Clasifica la frase en UNA intención:\n"
            ."- new_survey: hacer un levantamiento o una cotización nueva para un cliente.\n- open_project: continuar o abrir un proyecto que ya existe.\n"
            ."- agenda: saber qué tiene pendiente o agendado hoy.\n- quotes: revisar cotizaciones pendientes.\n- tickets: atender un ticket de soporte o una avería.\n"
            ."- none: no quiere hacer nada ahora o no es ninguna de las anteriores.\nEn \"client\" copia el nombre del cliente si lo dijo, o \"\" si no.\n\nFrase: $text";
        try {
            $d = Gemini::json([['role' => 'user', 'content' => $prompt]], self::SCHEMA, ['temperature' => 0, 'num_predict' => 256]);
        } catch (ApiException) {
            Log::warning('Conversación: la IA no respondió; se pide repetir');

            return [null, ''];
        }
        $intent = $d['intent'] ?? null;

        return [in_array($intent, self::INTENTS, true) ? $intent : null, trim((string) ($d['client'] ?? ''))];
    }

    /** Qué quiere hacer el técnico: intención y lo que se pudo sacar de la frase (cliente, teléfono, tipo, proyecto). */
    public static function understand(string $text, array $surveyTypes, array $projects): array
    {
        $r = ['intent' => null, 'client_name' => '', 'phone' => Intake::extractPhone($text), 'survey_type' => Intake::matchSurveyType($text, $surveyTypes),
            'project' => null, 'ai_used' => false];
        $intent = self::classifyByRules($text);
        $project = self::matchProject($text, $projects);
        if ($intent === null && $project !== null) {
            $intent = 'open_project'; // solo nombró a un cliente con proyecto abierto
        }
        if ($intent === null && trim($text) !== '') {
            [$intent, $aiClient] = self::classifyWithModel($text);
            if ($intent === 'none') {
                $intent = null; // que la IA diga «nada» de una frase que las reglas no reconocieron es no haber entendido
            }
            $r['ai_used'] = $intent !== null;
            if ($aiClient !== '' && $intent === 'new_survey') {
                $r['client_name'] = $aiClient;
            }
        }
        if ($intent === 'open_project') {
            $r['project'] = $project;
        } elseif ($intent === 'new_survey' && $r['client_name'] === '') {
            $r['client_name'] = self::extractClientName($text);
        }
        $r['intent'] = $intent;

        return $r;
    }
}
