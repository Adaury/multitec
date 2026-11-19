<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Survey;
use App\Support\ApiException;
use App\Support\Gemini;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;

/**
 * Funciones de IA (Gemini). Sin GEMINI_API_KEY todas responden 503 «IA no configurada» y el resto del sistema sigue igual.
 * Cada ruta lleva el límite `throttle:ai` (30 llamadas por minuto y usuario).
 */
class AiController extends Controller
{
    /** Vocabulario del oficio que ayuda a transcribir bien marcas y términos. */
    private const DOMAIN_PROMPT = 'Levantamiento técnico de seguridad electrónica en República Dominicana. Vocabulario: '
        .'cámaras IP de 2, 4, 5 y 8 megapíxeles, Hikvision, Dahua, Uniview, Ezviz, Hilook, Axis, Ubiquiti, TP-Link, NVR, DVR, '
        .'16 y 32 canales, disco duro, switch PoE de 8, 16 y 24 puertos, patch panel, rack, gabinete de 6U, 9U y 12U, organizador, '
        .'bandeja, UPS, regleta, cable UTP categoría 6, Cat6, conector RJ45, canaleta, tubería EMT, caja de cable, fuente de poder, '
        .'balun, access point, router, control de acceso, cerradura magnética, huella, intercom, videoportero, alarma, sensores, cerco eléctrico.';

    private const VOICE_SCHEMA = [
        'type' => 'object',
        'properties' => ['notes' => ['type' => 'string'], 'measurements' => ['type' => 'string'], 'observations' => ['type' => 'string']],
        'required' => ['notes', 'measurements', 'observations'],
    ];

    private function survey(int $projectId): Survey
    {
        return Survey::with('assets')->where('project_id', $projectId)->first()
            ?? throw new ApiException(404, 'Levantamiento no encontrado');
    }

    /** Ruta absoluta de un archivo subido, solo si es de esta empresa (misma regla que el resto de descargas). */
    private function absolute(?string $path): ?string
    {
        if (! $path || ! \App\Support\Uploads::owns($path)) {
            return null;
        }
        $abs = Storage::disk('local')->path($path);

        return is_file($abs) ? $abs : null;
    }

    /** Resumen profesional del levantamiento (con las fotos, si las hay). Guarda el resumen y devuelve el levantamiento. */
    public function summarizeSurvey(int $project_id)
    {
        $survey = $this->survey($project_id);
        $block = 'Notas: '.($survey->notes ?: '(sin notas)')."\nMedidas: ".($survey->measurements ?: '(sin medidas)')
            ."\nObservaciones: ".($survey->observations ?: '(sin observaciones)');
        $photos = [];
        foreach ($survey->assets->where('kind', 'photo') as $a) {
            if ($abs = $this->absolute($a->file_path)) {
                $photos[] = $abs;
            }
        }
        $photos = array_slice($photos, 0, 6); // el límite de la petición es ~20 MB: seis fotos reducidas caben de sobra

        if (! $photos) {
            $msg = ['role' => 'user', 'content' => 'Organiza la siguiente información de un levantamiento técnico de seguridad electrónica '
                .'(CCTV, redes, control de acceso, etc.) en un resumen profesional y claro en español, en párrafos cortos. '
                .'No inventes datos que no estén presentes.'."\n\n".$block];
        } else {
            // La instrucción sobre las fotos va primero: con el texto por delante el modelo tiende a olvidar que hay imágenes.
            $msg = ['role' => 'user', 'images' => $photos, 'content' => 'Estas fotos son de un levantamiento técnico de seguridad electrónica '
                .'(CCTV, redes, control de acceso, etc.). Descríbelas brevemente. Luego organiza esta información adicional en un resumen '
                .'profesional en español, en párrafos cortos, sin inventar datos que no estén presentes:'."\n\n".$block];
        }
        $summary = trim(Gemini::chat([$msg], null, ['temperature' => 0.2, 'num_predict' => 1500]));
        if ($summary === '') {
            throw new ApiException(502, 'La IA no devolvió ningún resumen. Intenta de nuevo.');
        }
        $survey->update(['ai_summary' => $summary]);

        return $this->survey($project_id)->load('assets.markers')->toOut();
    }

    /**
     * Transcribe una nota de voz ya subida y reparte el texto en Notas/Medidas/Observaciones. No modifica el levantamiento
     * (salvo la descripción del audio): el técnico revisa el resultado y decide aplicarlo.
     */
    public function transcribe(int $project_id, int $asset_id)
    {
        $survey = $this->survey($project_id);
        $asset = $survey->assets->first(fn ($a) => $a->id === $asset_id && $a->kind === 'audio');
        $abs = $asset ? $this->absolute($asset->file_path) : null;
        if (! $abs) {
            throw new ApiException(404, 'Nota de voz no encontrada');
        }
        try {
            $transcript = Gemini::transcribe($abs, self::DOMAIN_PROMPT);
        } catch (ApiException $e) {
            if ($e->status === 503) {
                throw $e; // IA sin configurar: el mensaje ya es claro
            }
            throw new ApiException(400, 'No se pudo transcribir el audio. '.$e->getMessage());
        }
        if ($transcript === '') {
            throw new ApiException(422, 'No se entendió nada en el audio. Habla más cerca o repite.');
        }
        $asset->update(['description' => mb_substr($transcript, 0, 255)]);

        return ['transcript' => $transcript] + $this->classifyVoice($transcript);
    }

    /** Reparte lo dictado entre los tres campos. Si la IA falla, degrada a poner todo en Notas para no perder nada. */
    private function classifyVoice(string $transcript): array
    {
        $fallback = ['notes' => $transcript, 'measurements' => '', 'observations' => '', 'classified' => false];
        $prompt = 'Un técnico de seguridad electrónica (CCTV, redes, control de acceso) dictó en voz alta lo que ve durante un levantamiento '
            ."en sitio. Tu única tarea es COPIAR cada frase del dictado al campo que le corresponde, en español:\n"
            ."- notes: qué hay que instalar o hacer (equipos, cantidades, ubicaciones, trabajos).\n"
            ."- measurements: distancias, alturas, metrajes y dimensiones, con su unidad.\n"
            ."- observations: condiciones del sitio, riesgos, restricciones, pedidos del cliente.\n\n"
            ."Reglas estrictas:\n"
            ."1. Usa las mismas palabras del técnico. NO agregues verbos, frases ni datos que él no dijo (por ejemplo no escribas \"comprar\", ni \"no hay restricciones\").\n"
            ."2. Conserva las cantidades y números exactos y NUNCA los omitas: \"tres cámaras\" se queda como \"tres cámaras\" (o \"3 cámaras\"), jamás como \"cámaras\".\n"
            ."3. Cada frase del dictado va en UN solo campo; no repitas la misma información en dos campos.\n"
            ."4. Si un campo no tiene contenido en el dictado, déjalo como \"\" (vacío). Nunca escribas \"ninguna\", \"no hay\" ni \"N/A\".\n\n"
            ."Dictado nuevo:\n".$transcript;
        try {
            $data = Gemini::json([['role' => 'user', 'content' => $prompt]], self::VOICE_SCHEMA, ['temperature' => 0]); // copiar, no «crear»
        } catch (ApiException) {
            return $fallback;
        }
        $out = [];
        foreach (['notes', 'measurements', 'observations'] as $k) {
            $out[$k] = trim((string) ($data[$k] ?? ''));
        }

        return array_filter($out, fn ($v) => $v !== '') ? $out + ['classified' => true] : $fallback;
    }

    /**
     * El técnico aplicó un dictado. En el original esto alimentaba un aprendizaje por empresa; esa tabla no se migró, así que
     * aquí solo se valida y se acepta (204) para que la pantalla funcione igual.
     */
    public function voiceFeedback(Request $r, int $project_id)
    {
        $this->survey($project_id);
        if (! is_string($r->input('transcript')) || mb_strlen($r->input('transcript')) > 20000) {
            throw new ApiException(422, 'transcript inválido');
        }

        return response()->noContent();
    }

    // ---- alta rápida y preguntas ---------------------------------------------------------------------

    /** De una frase («Juan Pérez, 809 555 1234, cámaras») saca nombre, teléfono y tipo. Nunca falla por la IA: sin ella usa las reglas. */
    public function intakeParse(Request $r)
    {
        $text = $r->input('text');
        $types = $r->input('survey_types', []);
        if (! is_string($text) || mb_strlen($text) > 2000 || ! is_array($types) || count($types) > 30
            || array_filter($types, fn ($t) => ! is_string($t) || mb_strlen($t) > 200)) {
            throw new ApiException(422, 'Texto (máx. 2000 caracteres) o lista de tipos (máx. 30) inválidos');
        }

        return \App\Support\Intake::parse($text, array_values($types));
    }

    private const ASK_SYSTEM = 'Eres un asistente que responde preguntas sobre proyectos de seguridad electrónica usando únicamente la información '
        ."de los expedientes proporcionados (puede haber uno o varios, separados por '---'). Si la respuesta no está en los expedientes, dilo "
        .'claramente en vez de inventar. Si hay varios proyectos, aclara a cuál te refieres en la respuesta.';

    /**
     * Pregunta sobre un proyecto (project_id) o, sin él, sobre los 3 proyectos visibles que más se parecen a la pregunta.
     * El técnico pregunta sobre el trabajo, no sobre el dinero: su contexto va sin montos.
     */
    public function ask(Request $r)
    {
        $user = $r->attributes->get('user');
        $question = $r->input('question');
        if (! is_string($question) || trim($question) === '' || mb_strlen($question) > 2000) {
            throw new ApiException(422, 'La pregunta es obligatoria (máximo 2000 caracteres)');
        }
        $money = $user->role !== 'tecnico';
        $pid = $r->input('project_id');
        if ($pid !== null) {
            $project = \App\Models\Project::with('client')->find((int) $pid);
            if (! $project || ! \App\Support\Access::canSeeProject($user, $project->id)) { // el id va en el cuerpo, no en la ruta
                throw new ApiException(404, 'Proyecto no encontrado');
            }
            $context = \App\Support\ProjectContext::build($project, $money);

            return ['answer' => $this->answer($context, $question), 'projects' => [$project->code]];
        }

        // Sin proyecto: se puntúan los expedientes visibles por las palabras de la pregunta que aparecen en ellos.
        $terms = array_values(array_unique(array_filter(
            preg_split('/[^a-z0-9]+/', \App\Support\Intake::fold($question)),
            fn ($w) => strlen($w) > 3,
        )));
        $ranked = [];
        $projects = \App\Support\Access::projectScope(\App\Models\Project::with('client'), $user)->orderByDesc('id')->limit(200)->get();
        foreach ($projects as $p) {
            $ctx = \App\Support\ProjectContext::build($p, $money);
            $folded = \App\Support\Intake::fold($ctx);
            $score = 0;
            foreach ($terms as $t) {
                $score += min(5, substr_count($folded, $t));
            }
            if ($score > 0) {
                $ranked[] = [$score, $p, $ctx];
            }
        }
        usort($ranked, fn ($a, $b) => $b[0] <=> $a[0]);
        $top = array_slice($ranked, 0, 3);
        if (! $top) {
            return ['answer' => 'No encontré ningún proyecto relacionado con tu pregunta. Indica el proyecto o usa palabras que aparezcan en su expediente (cliente, equipos, ubicación).', 'projects' => []];
        }

        return [
            'answer' => $this->answer(implode("\n\n---\n\n", array_column($top, 2)), $question),
            'projects' => array_map(fn ($t) => $t[1]->code, $top),
        ];
    }

    private function answer(string $context, string $question): string
    {
        $text = trim(Gemini::chat([
            ['role' => 'system', 'content' => self::ASK_SYSTEM."\n\nExpediente(s):\n".$context],
            ['role' => 'user', 'content' => $question],
        ], null, ['temperature' => 0.2, 'num_predict' => 1200]));
        if ($text === '') {
            throw new ApiException(502, 'La IA no devolvió respuesta. Intenta de nuevo.');
        }

        return $text;
    }

    // ---- ingeniería, presupuesto y cotización desde el levantamiento --------------------------------------------

    private const ENGINEERING_KEYS = ['recommended_equipment', 'distribution', 'conduits', 'wiring', 'technical_design', 'observations'];

    private function project(int $id): \App\Models\Project
    {
        return \App\Models\Project::with('client')->find($id) ?? throw new ApiException(404, 'Proyecto no encontrado');
    }

    private function draftEngineering(string $context): array
    {
        $schema = ['type' => 'object', 'required' => self::ENGINEERING_KEYS,
            'properties' => array_fill_keys(self::ENGINEERING_KEYS, ['type' => 'string'])];
        $d = Gemini::json([['role' => 'user', 'content' => 'Eres un ingeniero de sistemas de seguridad electrónica. A partir del siguiente expediente de proyecto, '
            .'redacta un borrador de ingeniería técnica en español. Sé concreto y práctico; si falta información para alguna sección, '
            ."indícalo brevemente en vez de inventar.\n\n".$context]], $schema, ['temperature' => 0.2, 'num_predict' => 3000]);

        return array_map(fn ($k) => trim((string) ($d[$k] ?? '')), array_combine(self::ENGINEERING_KEYS, self::ENGINEERING_KEYS));
    }

    /** Borrador de ingeniería a partir del expediente. No guarda nada: la pantalla lo muestra para revisarlo. */
    public function engineeringDraft(int $project_id)
    {
        return $this->draftEngineering(\App\Support\ProjectContext::build($this->project($project_id)));
    }

    /** Vista previa de las líneas que la IA armaría. No guarda nada. */
    public function budgetSuggestions(int $project_id)
    {
        [$items, $warnings] = \App\Support\AiEngine::computeItems(\App\Support\ProjectContext::build($this->project($project_id)), $project_id);

        return ['items' => array_map(fn ($i) => [
            'product_id' => $i['product_id'] ?? null, 'description' => $i['description'], 'quantity' => (float) $i['quantity'], 'unit_price' => (float) ($i['unit_price'] ?? 0),
        ], $items), 'warnings' => $warnings];
    }

    private function engineeringIsEmpty(?\App\Models\Engineering $e): bool
    {
        return $e !== null && ! ($e->recommended_equipment || $e->distribution || $e->conduits || $e->wiring || $e->technical_design || $e->observations);
    }

    /**
     * Presupuesto + Cotización (y, si el proyecto aún no tiene ingeniería, un borrador) de una sola vez. La cotización queda
     * «pendiente»: aprobar sigue siendo una decisión humana. Nada se guarda si la IA falla antes de armar las líneas.
     */
    public function generate(Request $r, int $project_id)
    {
        $user = $r->attributes->get('user');

        return $this->runGeneration($project_id, $user->id);
    }

    private function runGeneration(int $projectId, int $userId): array
    {
        $project = $this->project($projectId);
        $context = \App\Support\ProjectContext::build($project);
        [$items, $warnings, $notes] = \App\Support\AiEngine::computeItems($context, $projectId);
        if (! $items) {
            throw new ApiException(400, 'La IA no pudo derivar materiales del levantamiento');
        }
        // Una línea inválida (cantidad 0, por ejemplo) no debe tumbar toda la cotización: se omite y se avisa.
        $valid = [];
        foreach ($items as $it) {
            if (($it['quantity'] ?? 0) > 0 && is_finite((float) $it['quantity']) && trim((string) ($it['description'] ?? '')) !== '') {
                $it['description'] = mb_substr((string) $it['description'], 0, 500);
                $valid[] = $it;
            } else {
                $warnings[] = 'Se omitió «'.mb_substr((string) ($it['description'] ?? 'una línea'), 0, 80).'»: la IA le dio una cantidad o un dato inválido (revísala a mano).';
            }
        }
        if (! $valid) {
            throw new ApiException(400, 'La IA no pudo armar ninguna línea válida del levantamiento. Revisa las cantidades y vuelve a intentar.');
        }

        $result = \Illuminate\Support\Facades\DB::transaction(function () use ($projectId, $userId, $valid) {
            $b = \App\Models\Budget::create(['code' => \App\Support\Codes::next('PRE'), 'project_id' => $projectId, 'ai_generated' => true,
                'notes' => 'Generado automáticamente desde el levantamiento', 'created_by' => $userId, 'created_at' => now()]);
            foreach ($valid as $it) {
                $b->items()->create(['product_id' => $it['product_id'] ?? null, 'description' => $it['description'], 'quantity' => $it['quantity'],
                    'unit_price' => $it['unit_price'] ?? 0, 'note' => null]);
            }
            $b->load('items');
            $b->update(['total' => \App\Support\Money::sum($b->items), 'updated_at' => now()]);

            $q = \App\Models\Quote::create(['code' => \App\Support\Codes::next('COT'), 'project_id' => $projectId, 'source_budget_id' => $b->id,
                'notes' => $b->notes, 'created_by' => $userId, 'created_at' => now()]);
            foreach ($b->items as $i) {
                $q->items()->create(['product_id' => $i->product_id, 'description' => $i->description, 'quantity' => $i->quantity, 'unit_price' => $i->unit_price,
                    'subtotal' => \App\Support\Money::fromCents(\App\Support\Money::line($i->quantity, $i->unit_price)), 'note' => $i->note]);
            }
            [$sub, $tax, $total] = \App\Support\Money::totals($b->items);
            $q->update(['subtotal' => $sub, 'itbis' => $tax, 'total' => $total]);
            \App\Models\QuoteHistory::add($q->id, 'creada', "Generada desde presupuesto {$b->code}");

            return [$b, $q];
        });
        [$budget, $quote] = $result;
        \App\Support\Notify::quotePending($quote);

        // Borrador de ingeniería: «best effort» y solo si el proyecto no tiene ingeniería propia (no pisa lo que oficina editó).
        // Si falla, la cotización ya generada no se pierde.
        $drafted = false;
        $eng = \App\Models\Engineering::where('project_id', $projectId)->first();
        if ($this->engineeringIsEmpty($eng)) {
            try {
                $d = $this->draftEngineering($context);
                if ($notes) {
                    $d['observations'] = trim($d['observations']."\n".implode("\n", $notes));
                }
                $eng->update($d + ['ai_generated' => true]);
                $drafted = true;
            } catch (ApiException $e) {
                \Illuminate\Support\Facades\Log::warning("Borrador de ingeniería omitido para el proyecto $projectId: ".$e->getMessage());
            }
        }

        return [
            'budget' => \App\Models\Budget::with('items')->find($budget->id)->toOut(), 'quote' => \App\Models\Quote::with('items')->find($quote->id)->toOut(),
            'engineering_drafted' => $drafted, 'warnings' => $warnings, 'engineering_pending' => false,
        ];
    }

    // Trabajos de generación. En el original corrían en un hilo del servidor; en hosting compartido no hay hilos, así que la
    // generación se hace dentro de la misma petición (Gemini responde en segundos) y el resultado queda en caché una hora, con
    // el mismo contrato que usa la pantalla (start → status).

    private const JOB_TTL = 3600;

    private function jobKey(int $projectId): string
    {
        return 'gen:'.app('company_id').':'.$projectId;
    }

    private function jobDict(array $job): array
    {
        return array_intersect_key($job, array_flip(['project_id', 'label', 'status', 'started_at', 'finished_at', 'result', 'error']));
    }

    public function startGeneration(Request $r, int $project_id)
    {
        $user = $r->attributes->get('user');
        $project = $this->project($project_id);
        $cache = \Illuminate\Support\Facades\Cache::store();
        $key = $this->jobKey($project_id);
        // Si ya hay una en marcha para el proyecto, no se crea una segunda cotización.
        $lock = $cache->lock($key.':lock', 300);
        if (! $lock->get()) {
            return response()->json($this->jobDict($cache->get($key) ?? ['project_id' => $project_id, 'label' => $project->client->name, 'status' => 'running']), 202);
        }
        $job = ['project_id' => $project_id, 'user_id' => $user->id, 'label' => $project->client->name, 'status' => 'running',
            'started_at' => now()->toIso8601String(), 'finished_at' => null, 'result' => null, 'error' => null];
        $cache->put($key, $job, self::JOB_TTL);
        try {
            $job['result'] = $this->runGeneration($project_id, $user->id);
            $job['status'] = 'done';
        } catch (ApiException $e) {
            $job['status'] = 'error';
            $job['error'] = $e->getMessage();
        } catch (\Throwable $e) {
            report($e);
            $job['status'] = 'error';
            $job['error'] = 'La IA no pudo armar la cotización esta vez. Tu levantamiento quedó guardado; intenta de nuevo.';
        } finally {
            $job['finished_at'] = now()->toIso8601String();
            $cache->put($key, $job, self::JOB_TTL);
            $lock->release();
        }
        $ids = (array) $cache->get('genuser:'.app('company_id').':'.$user->id, []);
        $cache->put('genuser:'.app('company_id').':'.$user->id, array_values(array_unique(array_merge($ids, [$project_id]))), self::JOB_TTL);

        return response()->json($this->jobDict($job), 202);
    }

    public function generationStatus(int $project_id)
    {
        $this->project($project_id); // 404 si es de otra empresa: el resultado de la IA no se filtra entre empresas
        $job = \Illuminate\Support\Facades\Cache::get($this->jobKey($project_id));

        return $job ? $this->jobDict($job) : ['project_id' => $project_id, 'status' => 'none'];
    }

    /** Las generaciones de este usuario en marcha o terminadas hace poco (la pantalla lo pregunta al abrirse). */
    public function myGenerationJobs(Request $r)
    {
        $user = $r->attributes->get('user');
        $out = [];
        foreach ((array) \Illuminate\Support\Facades\Cache::get('genuser:'.app('company_id').':'.$user->id, []) as $pid) {
            $job = \Illuminate\Support\Facades\Cache::get($this->jobKey((int) $pid));
            if ($job && ($job['user_id'] ?? null) === $user->id && \App\Support\Access::canSeeProject($user, (int) $pid)) {
                $out[] = $this->jobDict($job);
            }
        }

        return $out;
    }
}
