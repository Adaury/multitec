<?php

namespace App\Support;

use Illuminate\Http\Client\ConnectionException;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

/**
 * Cliente de Gemini (Google) por API. Es el único motor de IA de esta versión: no hay Ollama ni Whisper local porque
 * el hosting compartido no puede correrlos.
 *
 * - La clave va en la cabecera `x-goog-api-key`, nunca en la URL (los errores de HTTP incluyen la URL y la clave acabaría
 *   en el registro).
 * - Los mensajes de error son seguros de mostrar al usuario (sin clave, URL ni rutas).
 * - Lo que viaja en el prompt (datos de clientes, fotos, audios) sale de este servidor hacia Google.
 */
class Gemini
{
    private const DEFAULT_BASE = 'https://generativelanguage.googleapis.com/v1beta';
    private const RETRY = [429, 500, 502, 503, 504];
    private const MAX_ATTEMPTS = 3;
    private const DEFAULT_TOKENS = 2048;
    /** Con un tope muy justo el JSON sale cortado a medias; el costo de dar margen es mínimo. */
    private const MIN_TOKENS = 256;
    private const MAX_IMAGE_SIDE = 1600;

    public static function configured(): bool
    {
        return trim((string) config('services.gemini.key')) !== '';
    }

    private static function model(): string
    {
        return (string) config('services.gemini.model', 'gemini-2.5-flash');
    }

    /** @throws ApiException con un mensaje seguro de mostrar */
    private static function post(string $path, array $payload): array
    {
        $key = trim((string) config('services.gemini.key'));
        if ($key === '') {
            throw new ApiException(503, 'La IA no está configurada en el servidor (falta GEMINI_API_KEY en el .env).');
        }
        $last = null;
        for ($attempt = 1; $attempt <= self::MAX_ATTEMPTS; $attempt++) {
            try {
                $res = Http::withHeaders(['x-goog-api-key' => $key])->timeout(60)->acceptJson()->asJson()->post(rtrim((string) config('services.gemini.base_url', self::DEFAULT_BASE), '/').'/'.$path, $payload);
            } catch (ConnectionException $e) {
                // El texto de la excepción puede traer la URL: solo se registra el tipo.
                Log::warning('Gemini: fallo de red ('.class_basename($e).'), intento '.$attempt);
                $last = new ApiException(502, 'No se pudo conectar con el servicio de IA (Gemini). Intenta de nuevo en un momento.');
                if ($attempt < self::MAX_ATTEMPTS) {
                    usleep(1_500_000 * $attempt);
                }
                continue;
            }
            if ($res->successful()) {
                return (array) $res->json();
            }
            $code = $res->status();
            Log::warning("Gemini: HTTP $code: ".mb_substr($res->body(), 0, 500));
            $msg = match (true) {
                $code === 429 => 'El servicio de IA (Gemini) alcanzó su límite de uso. Espera un minuto e intenta de nuevo.',
                in_array($code, [401, 403], true) => 'Gemini rechazó la clave. Revisa GEMINI_API_KEY.',
                $code >= 500 => 'El servicio de IA (Gemini) no está disponible ahora. Intenta de nuevo en un momento.',
                default => 'Gemini no pudo procesar la solicitud.',
            };
            $last = new GeminiError($msg, 502, $code);
            if (! in_array($code, self::RETRY, true)) {
                throw $last;
            }
            if ($attempt < self::MAX_ATTEMPTS) {
                usleep(1_500_000 * $attempt);
            }
        }
        throw $last;
    }

    private static function textOf(array $data): string
    {
        $c = $data['candidates'] ?? [];
        if (! $c) {
            $block = $data['promptFeedback']['blockReason'] ?? null;
            throw new ApiException(502, 'Gemini no dio respuesta'.($block ? " (bloqueada: $block)." : '.'));
        }
        $text = '';
        foreach ($c[0]['content']['parts'] ?? [] as $p) {
            $text .= is_array($p) ? ($p['text'] ?? '') : '';
        }

        return $text;
    }

    private static function generate(string $system, array $contents, array $options, ?array $schema): string
    {
        $cfg = ['maxOutputTokens' => max((int) ($options['num_predict'] ?? self::DEFAULT_TOKENS), self::MIN_TOKENS)];
        if (isset($options['temperature'])) {
            $cfg['temperature'] = $options['temperature'];
        }
        $budget = config('services.gemini.thinking_budget');
        if ($budget !== null && $budget >= 0) {
            // Sin esto, gemini-2.5 gasta parte del tope de salida "pensando" y puede devolver el JSON vacío.
            $cfg['thinkingConfig'] = ['thinkingBudget' => (int) $budget];
        }
        if ($schema !== null) {
            $cfg['responseMimeType'] = 'application/json';
            $system = ($system !== '' ? $system."\n\n" : '').'Responde ÚNICAMENTE con un objeto JSON válido que cumpla este esquema, sin texto adicional:'."\n"
                .json_encode($schema, JSON_UNESCAPED_UNICODE);
        }
        $payload = ['contents' => $contents, 'generationConfig' => $cfg];
        if ($system !== '') {
            $payload['systemInstruction'] = ['parts' => [['text' => $system]]];
        }
        $path = 'models/'.self::model().':generateContent';
        if ($schema !== null) {
            // Esquema nativo si la API lo acepta; si responde 400 se reintenta sin él (el esquema ya va en el texto).
            $native = $payload;
            $native['generationConfig']['responseJsonSchema'] = $schema;
            try {
                return self::textOf(self::post($path, $native));
            } catch (GeminiError $e) {
                if ($e->geminiStatus !== 400) {
                    throw $e;
                }
                Log::info('Gemini rechazó responseJsonSchema; se reintenta con el esquema solo en el prompt');
            }
        }

        return self::textOf(self::post($path, $payload));
    }

    /**
     * Conversación: $messages = [['role' => system|user|assistant, 'content' => string, 'images' => [bytes|ruta, ...]], ...].
     * Con $schema devuelve el texto JSON (úsese json_decode); sin él, texto libre.
     */
    public static function chat(array $messages, ?array $schema = null, array $options = []): string
    {
        $system = [];
        $contents = [];
        foreach ($messages as $m) {
            $role = $m['role'] ?? 'user';
            $text = (string) ($m['content'] ?? '');
            if ($role === 'system') {
                $system[] = $text;
                continue;
            }
            $parts = $text !== '' ? [['text' => $text]] : [];
            foreach ($m['images'] ?? [] as $img) {
                $parts[] = self::imagePart($img);
            }
            if ($parts) {
                $contents[] = ['role' => $role === 'assistant' ? 'model' : 'user', 'parts' => $parts];
            }
        }

        return self::generate(implode("\n\n", $system), $contents, $options, $schema);
    }

    /** JSON ya decodificado; si el modelo devolvió algo que no es JSON, error claro en vez de un 500. */
    public static function json(array $messages, array $schema, array $options = []): array
    {
        $raw = trim(self::chat($messages, $schema, $options));
        $raw = preg_replace('/^```(?:json)?\s*|\s*```$/i', '', $raw);
        $data = json_decode((string) $raw, true);
        if (! is_array($data)) {
            Log::warning('Gemini devolvió una respuesta que no es JSON: '.mb_substr((string) $raw, 0, 300));
            throw new ApiException(502, 'La IA devolvió una respuesta que no pude leer. Intenta de nuevo.');
        }

        return $data;
    }

    /** Vector de búsqueda de un texto. @return float[] */
    public static function embed(string $text): array
    {
        $name = (string) config('services.gemini.embedding_model', 'gemini-embedding-001');
        $payload = ['model' => "models/$name", 'content' => ['parts' => [['text' => $text]]]];
        if ($dims = (int) config('services.gemini.embedding_dims', 768)) {
            $payload['outputDimensionality'] = $dims;
        }
        $values = self::post("models/$name:embedContent", $payload)['embedding']['values'] ?? null;
        if (! $values) {
            throw new ApiException(502, 'Gemini no devolvió el vector de búsqueda.');
        }

        return array_map('floatval', $values);
    }

    /** Audio → texto en español. Se envía tal cual (Gemini acepta wav, mp3, m4a/aac, ogg, flac; no hay ffmpeg en el hosting). */
    public static function transcribe(string $path, string $vocabulary = ''): string
    {
        $mime = self::audioMime($path);
        $instruction = 'Transcribe este audio en español, palabra por palabra y sin resumir. Responde SOLO con la transcripción. '
            .'Si no se entiende nada, responde con una cadena vacía.';
        if ($vocabulary !== '') {
            $instruction .= "\nContexto y vocabulario que puede aparecer (escribe bien estos términos): $vocabulary";
        }
        $contents = [['role' => 'user', 'parts' => [['text' => $instruction], self::inline($mime, (string) file_get_contents($path))]]];

        return trim(self::generate('', $contents, ['temperature' => 0, 'num_predict' => 4096], null));
    }

    // ---- adjuntos -----------------------------------------------------------------------------------

    private static function inline(string $mime, string $data): array
    {
        return ['inline_data' => ['mime_type' => $mime, 'data' => base64_encode($data)]];
    }

    private static function audioMime(string $path): string
    {
        $head = (string) file_get_contents($path, false, null, 0, 16);
        return match (true) {
            str_starts_with($head, 'RIFF') => 'audio/wav',
            str_starts_with($head, 'ID3'), ($head[0] ?? '') === "\xFF" => 'audio/mp3',
            str_starts_with($head, 'OggS') => 'audio/ogg',
            str_starts_with($head, 'fLaC') => 'audio/flac',
            substr($head, 4, 4) === 'ftyp' => 'audio/aac', // m4a / mp4 de iPhone
            str_starts_with($head, "\x1A\x45\xDF\xA3") => 'audio/webm',
            default => 'audio/mp3',
        };
    }

    /** Foto reducida (lado mayor 1600 px, JPEG, orientación respetada); si GD no la puede leer se manda cruda. */
    private static function imagePart(string $imageOrPath): array
    {
        $data = is_file($imageOrPath) ? (string) file_get_contents($imageOrPath) : $imageOrPath;
        if (str_starts_with($data, '%PDF')) {
            return self::inline('application/pdf', $data);
        }
        $img = function_exists('imagecreatefromstring') ? @imagecreatefromstring($data) : false;
        if (! $img) {
            $info = @getimagesizefromstring($data);

            return self::inline($info['mime'] ?? 'image/jpeg', $data);
        }
        if (function_exists('exif_read_data') && str_starts_with($data, "\xFF\xD8")) {
            $tmp = 'data://image/jpeg;base64,'.base64_encode($data);
            $o = @exif_read_data($tmp)['Orientation'] ?? 1;
            $img = match ($o) { 3 => imagerotate($img, 180, 0), 6 => imagerotate($img, -90, 0), 8 => imagerotate($img, 90, 0), default => $img };
        }
        [$w, $h] = [imagesx($img), imagesy($img)];
        $scale = min(1, self::MAX_IMAGE_SIDE / max($w, $h));
        if ($scale < 1) {
            $img = imagescale($img, (int) round($w * $scale), (int) round($h * $scale));
        }
        ob_start();
        imagejpeg($img, null, 85);

        return self::inline('image/jpeg', (string) ob_get_clean());
    }
}
