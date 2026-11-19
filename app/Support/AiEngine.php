<?php

namespace App\Support;

use App\Models\CalculationParameter;
use App\Models\CatalogRule;
use App\Models\Product;
use App\Models\TechnicalRule;
use Illuminate\Support\Facades\Log;

/**
 * Motor de IA de cotizaciones (puerto del original): interpretar el expediente (Gemini) → emparejar con el catálogo (texto primero,
 * IA solo para lo ambiguo) → reglas de accesorios → cantidades marcadas en fotos → cálculos (cable, paquetes, almacenamiento, mano de
 * obra, capacidad). Todo lo aritmético es determinista; la IA solo interpreta lenguaje y desempata productos parecidos.
 */
class AiEngine
{
    // ---- Motor 3: texto ---------------------------------------------------------------------------

    public static function norm(string $t): string
    {
        $t = mb_strtolower(trim($t));
        $t = preg_replace('/\p{Mn}/u', '', \Normalizer::normalize($t, \Normalizer::FORM_D) ?: $t);

        return trim((string) preg_replace('/\s+/u', ' ', (string) $t));
    }

    private static function terms(array $p): array
    {
        $t = [self::norm($p['name'])];
        foreach (array_merge($p['tags'] ?? [], $p['synonyms'] ?? []) as $x) {
            $t[] = self::norm((string) $x);
        }

        return array_values(array_unique(array_filter($t)));
    }

    /** Primer producto cuyo nombre/etiqueta/sinónimo aparece como palabra completa (plural simple tolerado). */
    public static function findProductByText(string $description, array $catalog): ?int
    {
        $d = self::norm($description);
        if ($d === '') {
            return null;
        }
        foreach ($catalog as $p) {
            foreach (self::terms($p) as $term) {
                if (preg_match('/\b'.preg_quote($term, '/').'(?:s|es)?\b/u', $d)) {
                    return $p['id'];
                }
            }
        }

        return null;
    }

    // ---- Motor 1: interpretar -----------------------------------------------------------------------

    private const ENTITIES_SCHEMA = [
        'type' => 'object',
        'properties' => ['entities' => ['type' => 'array', 'items' => [
            'type' => 'object',
            'properties' => ['description' => ['type' => 'string'], 'quantity' => ['type' => 'number'], 'unit' => ['type' => 'string']],
            'required' => ['description', 'quantity'],
        ]]],
        'required' => ['entities'],
    ];
    private const STOP = ['el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'de', 'del', 'al', 'en', 'con', 'y', 'o'];
    private const NOT_FOR_SALE = ['celular', 'celulares', 'smartphone', 'movil', 'computadora', 'computador', 'laptop', 'internet',
        'casa', 'edificio', 'cuarto', 'vivienda', 'apartamento', 'local', 'oficina'];

    private static function ascii(string $s): string
    {
        return strtolower((string) preg_replace('/[^\x20-\x7E]/', '', preg_replace('/\p{Mn}/u', '', \Normalizer::normalize($s, \Normalizer::FORM_D) ?: $s)));
    }

    /** Medidas del sitio («40 metros», «Altura de instalación 3.5 metros») no son materiales. */
    public static function isMeasurement(string $d): bool
    {
        $t = trim((string) preg_replace('/\s+/', ' ', self::ascii($d)));
        $t = trim((string) preg_replace('/[\d.,]+/', '', $t));

        return $t === '' || preg_match('/^(?:metros?|mts?|m|pies?|ft|cm|centimetros?|pulgadas?|kilometros?|km)$/', $t)
            || preg_match('/^(?:distancia|altura|longitud|profundidad|ancho|largo|metraje|recorrido|separacion)\b/', $t);
    }

    /** Lugares o cosas que el cliente ya tiene («el celular», «internet», «la casa»): no se cotizan. */
    public static function isNotForSale(string $d): bool
    {
        preg_match_all('/[a-z]+/', self::ascii($d), $m);
        $words = array_values(array_filter($m[0], fn ($w) => ! in_array($w, self::STOP, true)));

        return $words && ! array_diff($words, self::NOT_FOR_SALE);
    }

    /** «NVR de 16 canales» no son 16 NVR: si la cantidad es justo el número de una especificación, es 1 equipo. */
    private static function specNotQuantity(array $e): array
    {
        $d = self::ascii((string) ($e['description'] ?? ''));
        $q = $e['quantity'] ?? null;
        if (! $q || (float) $q != (int) $q) {
            return $e;
        }
        $leading = preg_match('/^\s*(\d+)\b/', $d, $lm) ? (int) $lm[1] : null;
        if (preg_match_all('/\b(\d+)\s*(?:canales?|puertos?|megapixel(?:es)?|mp|tb|gb)\b/', $d, $mm)) {
            foreach ($mm[1] as $n) {
                if ((int) $n === (int) $q && ! ($leading !== null && $leading === (int) $q)) {
                    return ['quantity' => 1] + $e;
                }
            }
        }

        return $e;
    }

    public static function interpret(string $context): array
    {
        $prompt = "Eres un especialista en seguridad electrónica interpretando el lenguaje de un técnico durante un levantamiento. A partir del expediente "
            ."del proyecto, identifica cada material, equipo, accesorio o servicio de mano de obra mencionado EXPLÍCITAMENTE, con su cantidad.\n\nReglas:\n"
            ."1. Convierte cantidades escritas en palabras a números (\"ocho cámaras\" → 8, \"doscientos metros\" → 200, \"diez\" → 10).\n"
            ."2. Incluye SOLO lo que el técnico menciona explícitamente, con la cantidad que él indique — no agregues accesorios ni productos por tu cuenta; eso se calcula aparte con reglas del catálogo.\n"
            ."3. Usa la descripción tal como la usó el técnico, sin intentar normalizarla contra ningún catálogo — eso es un paso aparte.\n"
            ."4. Las MEDIDAS (distancias, alturas, metrajes del sitio) y las OBSERVACIONES del cliente NO son materiales: no las incluyas. Solo incluye metros cuando sean de un cable o canalización (ej. \"200 metros de cable UTP\").\n"
            ."5. COPIA en la descripción todos los datos que el técnico dijo de un equipo: canales, puertos, megapíxeles, tamaño U, capacidad, tipo. Solo los que dijo: si no mencionó canales o puertos, no los agregues.\n"
            ."6. NO incluyas lugares ni cosas que el cliente ya tiene o usa para ver el sistema (el celular, la computadora, el internet, el rack o el cuarto donde se instala, la casa, el edificio): no se venden.\n\n"
            ."Expediente del proyecto:\n".$context;
        // temperature 0: el mismo levantamiento debe dar siempre la misma lista.
        $data = Gemini::json([['role' => 'user', 'content' => $prompt]], self::ENTITIES_SCHEMA, ['temperature' => 0, 'num_predict' => 2048]);
        $out = [];
        foreach ($data['entities'] ?? [] as $e) {
            if (! is_array($e) || ! isset($e['description']) || ! is_numeric($e['quantity'] ?? null)) {
                continue;
            }
            $e['quantity'] = (float) $e['quantity'];
            $d = (string) $e['description'];
            if (! self::isMeasurement($d) && ! self::isNotForSale($d)) {
                // specNotQuantity() existe para el modelo local del original (confundía «16 canales» con 16 equipos); con Gemini
                // rompe casos válidos como «4 cámaras de 4 megapíxeles», así que no se aplica.
                $out[] = $e;
            }
        }

        return $out;
    }

    // ---- Motor 2: emparejar con el catálogo ---------------------------------------------------------------

    private const STOPWORDS = ['de', 'del', 'la', 'las', 'el', 'los', 'con', 'para', 'por', 'un', 'una', 'unos', 'unas', 'y', 'o', 'en', 'al', 'a', 'sin', 'que', 'se', 'su', 'sus', 'x', 'mas'];
    private const CONFIDENT_SCORE = 10;
    private const CONFIDENT_MARGIN = 3;

    private static function tokens(string $t): array
    {
        $out = [];
        preg_match_all('/[a-z0-9]+/', self::norm($t), $m);
        foreach ($m[0] as $w) {
            if (in_array($w, self::STOPWORDS, true) || strlen($w) < 2) {
                continue;
            }
            $out[$w] = true;
            if (str_ends_with($w, 'es') && strlen($w) > 4) {
                $out[substr($w, 0, -2)] = true;
            } elseif (str_ends_with($w, 's') && strlen($w) > 3) {
                $out[substr($w, 0, -1)] = true;
            }
        }

        return array_keys($out);
    }

    /** Qué tan parecido es un producto a lo detectado: sinónimos (lo más fuerte), nombre, etiquetas y categoría; los números desempatan modelos. */
    public static function score(string $entityText, array $p): int
    {
        $entity = self::norm($entityText);
        $words = self::tokens($entityText);
        if (! $words) {
            return 0;
        }
        $score = 0;
        foreach ($p['synonyms'] ?? [] as $syn) {
            $phrase = self::norm((string) $syn);
            if ($phrase !== '' && preg_match('/\b'.preg_quote($phrase, '/').'\b/u', $entity)) {
                $score += 6;
            }
        }
        $score += 3 * count(array_intersect($words, self::tokens($p['name'])));
        foreach ($p['tags'] ?? [] as $tag) {
            $score += 2 * count(array_intersect($words, self::tokens((string) $tag)));
        }
        $score += count(array_intersect($words, self::tokens((string) ($p['category'] ?? ''))));
        preg_match_all('/\d+(?:\.\d+)?/', $entity, $w);
        preg_match_all('/\d+(?:\.\d+)?/', self::norm($p['name']), $h);
        if ($w[0] && $h[0]) {
            $score += array_intersect($w[0], $h[0]) ? 5 : -4;
        }

        return $score;
    }

    /** @return array{0: array<int,int>, 1: array<int,int>} [índice => id claro, índices ambiguos] */
    private static function confidentMatches(array $entities, array $catalog): array
    {
        $resolved = [];
        $ambiguous = [];
        foreach ($entities as $i => $e) {
            $ranked = [];
            foreach ($catalog as $p) {
                $ranked[] = [self::score($e['description'], $p), $p['id']];
            }
            usort($ranked, fn ($a, $b) => [$b[0], $a[1]] <=> [$a[0], $b[1]]);
            [$best, $bestId] = $ranked[0] ?? [0, null];
            $second = $ranked[1][0] ?? 0;
            if ($best <= 0) {
                continue; // no se parece a nada (mano de obra, un servicio): preguntarle a la IA solo la empuja a inventar
            }
            if ($best >= self::CONFIDENT_SCORE && $best - $second >= self::CONFIDENT_MARGIN) {
                $resolved[$i] = $bestId;
            } else {
                $ambiguous[] = $i;
            }
        }

        return [$resolved, $ambiguous];
    }

    /** Productos que van al prompt: todo el catálogo si es chico; si no, los más parecidos a cada entidad. */
    private static function shortlist(array $entities, array $catalog): array
    {
        if (count($catalog) <= 25) {
            return $catalog;
        }
        $per = max(3, min(6, intdiv(40, max(1, count($entities)))));
        $best = [];
        foreach ($entities as $e) {
            $scored = [];
            foreach ($catalog as $p) {
                $scored[] = [self::score($e['description'], $p), $p['id']];
            }
            usort($scored, fn ($a, $b) => [$b[0], $a[1]] <=> [$a[0], $b[1]]);
            foreach (array_slice($scored, 0, $per) as [$s, $id]) {
                if ($s > 0) {
                    $best[$id] = max($best[$id] ?? 0, $s);
                }
            }
        }
        if (! $best) {
            return array_slice($catalog, 0, 40);
        }
        uksort($best, fn ($a, $b) => [$best[$b], $a] <=> [$best[$a], $b]);
        $keep = array_flip(array_slice(array_keys($best), 0, 40));

        return array_values(array_filter($catalog, fn ($p) => isset($keep[$p['id']])));
    }

    /** Pregunta a Gemini solo por las ambiguas, con candidatos acotados. Si falla, devuelve [] (quedan al respaldo por texto). */
    private static function askModel(array $entities, array $catalog): array
    {
        if (! $entities) {
            return [];
        }
        $lines = [];
        foreach (self::shortlist($entities, $catalog) as $p) {
            $l = "- id={$p['id']}: {$p['name']} (categoría: {$p['category']}, unidad: ".($p['unit'] ?: 'unidad').')';
            if ($p['tags']) {
                $l .= "\n  etiquetas: ".implode(', ', $p['tags']);
            }
            if ($p['synonyms']) {
                $l .= "\n  sinónimos: ".implode(', ', $p['synonyms']);
            }
            $lines[] = $l;
        }
        $list = [];
        foreach ($entities as $i => $e) {
            $list[] = "$i: ".self::qty($e['quantity'])." x {$e['description']}";
        }
        $n = count($entities);
        $prompt = "Eres un especialista en catálogo de seguridad electrónica. Para cada elemento de la lista, elige el product_id del catálogo que le corresponde "
            ."(compara nombre, categoría, etiquetas y sinónimos). Si ninguno corresponde (mano de obra, servicios), usa 0.\n\n"
            ."Devuelve un objeto JSON compacto {\"product_ids\": [...]} con EXACTAMENTE $n enteros, uno por elemento y en el mismo orden.\n\n"
            ."Catálogo disponible:\n".implode("\n", $lines)."\n\nElementos:\n".implode("\n", $list);
        $schema = ['type' => 'object', 'properties' => ['product_ids' => ['type' => 'array', 'items' => ['type' => 'integer']]], 'required' => ['product_ids']];
        try {
            $ids = Gemini::json([['role' => 'user', 'content' => $prompt]], $schema, ['temperature' => 0, 'num_predict' => 40 + 8 * $n])['product_ids'] ?? [];
        } catch (ApiException) {
            Log::warning('Emparejamiento con IA omitido: se usan solo las coincidencias por texto');

            return [];
        }
        $valid = array_flip(array_column($catalog, 'id'));
        $out = [];
        foreach (array_slice(array_values((array) $ids), 0, $n) as $i => $id) {
            if (isset($valid[$id])) {
                $out[$i] = (int) $id;
            }
        }

        return $out;
    }

    private static function qty($q): string
    {
        return rtrim(rtrim(number_format((float) $q, 4, '.', ''), '0'), '.');
    }

    /** El modelo a veces elige un producto que el texto contradice (puntaje <= 0) cuando otro sí encaja: gana el texto. */
    private static function preferText(string $description, int $modelChoice, array $catalog): int
    {
        $scored = [];
        foreach ($catalog as $p) {
            $scored[] = [self::score($description, $p), $p['id']];
        }
        usort($scored, fn ($a, $b) => [$b[0], $a[1]] <=> [$a[0], $b[1]]);
        [$best, $bestId] = $scored[0];
        $chosen = 0;
        foreach ($scored as [$s, $id]) {
            if ($id === $modelChoice) {
                $chosen = $s;
                break;
            }
        }

        return $best > 0 && $chosen <= 0 ? $bestId : $modelChoice;
    }

    /** Texto primero, IA solo para lo ambiguo, y respaldo determinista por etiquetas/sinónimos. */
    public static function matchToCatalog(array $entities, array $catalog): array
    {
        if (! $entities) {
            return [];
        }
        [$resolved, $ambiguous] = self::confidentMatches($entities, $catalog);
        if ($ambiguous) {
            $sub = array_map(fn ($i) => $entities[$i], $ambiguous);
            foreach (self::askModel($sub, $catalog) as $si => $pid) {
                if ($pid) {
                    $resolved[$ambiguous[$si]] = self::preferText($sub[$si]['description'], $pid, $catalog);
                }
            }
        }
        $items = [];
        foreach ($entities as $i => $e) {
            $pid = $resolved[$i] ?? null;
            $pid ??= self::findProductByText($e['description'], $catalog);
            $items[] = ['product_id' => $pid, 'description' => $e['description'], 'quantity' => (float) $e['quantity']];
        }

        return $items;
    }

    // ---- Motor 4: reglas -----------------------------------------------------------------------------------

    /** «1 disco por cada 4 cámaras»: aritmética determinista con datos del catálogo, no con el modelo. */
    public static function expandWithRules(array $items, array $catalog, array $rules): array
    {
        $included = [];
        foreach ($items as $it) {
            if (! empty($it['product_id'])) {
                $included[$it['product_id']] = true;
            }
        }
        $bySource = [];
        foreach ($rules as $r) {
            $bySource[$r['source_product_id']][] = $r;
        }
        $added = [];
        $names = [];
        foreach ($items as $it) {
            $pid = $it['product_id'] ?? null;
            if (! $pid || ! isset($bySource[$pid])) {
                continue;
            }
            $srcQty = (float) ($it['quantity'] ?? 0);
            foreach ($bySource[$pid] as $rule) {
                $target = null;
                foreach ($catalog as $c) {
                    if (in_array($rule['target_tag'], $c['tags'] ?? [], true)) {
                        $target = $c;
                        break;
                    }
                }
                if (! $target || isset($included[$target['id']])) {
                    continue;
                }
                if (! empty($rule['per_source_units'])) {
                    if ($srcQty <= 0) {
                        continue;
                    }
                    $add = ceil($srcQty / $rule['per_source_units']) * $rule['quantity'];
                } else {
                    $add = $rule['quantity'];
                }
                $added[$target['id']] = ($added[$target['id']] ?? 0) + $add;
                $names[$target['id']] = $target['name'];
            }
        }
        foreach ($added as $id => $q) {
            $items[] = ['product_id' => $id, 'description' => $names[$id], 'quantity' => (float) $q];
        }

        return $items;
    }

    /** CatalogRule (todas) + TechnicalRule add_accessory, en la forma que espera expandWithRules. */
    private static function accessoryRules(): array
    {
        $out = [];
        foreach (CatalogRule::all() as $r) {
            $out[] = ['source_product_id' => $r->source_product_id, 'target_tag' => $r->target_tag,
                'per_source_units' => $r->per_source_units !== null ? (float) $r->per_source_units : null, 'quantity' => (float) $r->quantity];
        }
        foreach (TechnicalRule::where('action_type', TechnicalRule::ADD_ACCESSORY)->get() as $r) {
            $o = $r->toOut();
            $out[] = ['source_product_id' => $o['source_product_id'], 'target_tag' => $o['target_tag'],
                'per_source_units' => $o['per_source_units'] !== null ? (float) $o['per_source_units'] : null, 'quantity' => (float) $o['quantity']];
        }

        return $out;
    }

    private static function presentIds(array $items): array
    {
        $ids = [];
        foreach ($items as $it) {
            if (! empty($it['product_id'])) {
                $ids[$it['product_id']] = true;
            }
        }

        return $ids;
    }

    /** set_calculation_parameter: si varias reglas apuntan a la misma clave gana el valor más alto (el más conservador). */
    private static function paramOverrides(array $items, $technicalRules): array
    {
        $present = self::presentIds($items);
        $o = [];
        foreach ($technicalRules as $r) {
            $x = $r->toOut();
            if ($x['action_type'] !== TechnicalRule::SET_PARAMETER || ! isset($present[$x['source_product_id']]) || $x['parameter_key'] === null || $x['value'] === null) {
                continue;
            }
            if (! isset($o[$x['parameter_key']]) || $x['value'] > $o[$x['parameter_key']]) {
                $o[$x['parameter_key']] = (float) $x['value'];
            }
        }

        return $o;
    }

    private static function engineeringNotes(array $items, $technicalRules): array
    {
        $present = self::presentIds($items);
        $notes = [];
        foreach ($technicalRules as $r) {
            $x = $r->toOut();
            if ($x['action_type'] === TechnicalRule::FLAG_NOTE && isset($present[$x['source_product_id']]) && $x['engineering_note'] && ! in_array($x['engineering_note'], $notes, true)) {
                $notes[] = $x['engineering_note'];
            }
        }

        return $notes;
    }

    // ---- puntos marcados en las fotos ---------------------------------------------------------------------------

    private const ACCESSORY_WORDS = '/fuente|cable|conector|soporte|caja|base\b|balun|adaptador|disco|ba[ñn]o|jack|patch|canaleta|tubo|mano de obra|instalaci[óo]n|licencia|cubierta|ventilador|\bkit\b|paquete|combo/iu';

    public static function isKindLine(array $item, string $kind, array $categoryOf): bool
    {
        $pattern = SurveyPoints::KINDS[$kind] ?? null;
        if (! $pattern) {
            return false;
        }
        $desc = (string) ($item['description'] ?? '');
        $cat = $categoryOf[$item['product_id'] ?? -1] ?? '';
        if (preg_match($pattern, $cat)) {
            return true;
        }

        return (bool) preg_match($pattern, $desc) && ! preg_match(self::ACCESSORY_WORDS, $desc);
    }

    /** Cuadra lo cotizado con lo marcado: si lo marcado es MÁS y hay una sola línea, se sube; si no, solo se avisa. */
    public static function reconcile(array $items, array $counts, array $categoryOf): array
    {
        $warnings = [];
        foreach ($counts as $kind => $marked) {
            if ($kind === 'otro' || ! $marked) {
                continue;
            }
            $idx = array_keys(array_filter($items, fn ($it) => self::isKindLine($it, $kind, $categoryOf)));
            $quoted = array_sum(array_map(fn ($i) => (float) ($items[$i]['quantity'] ?? 0), $idx));
            $name = SurveyPoints::LABELS[$kind] ?? 'Otro';
            if (! $idx) {
                $warnings[] = "Marcaste $marked punto(s) de «{$name}» en las fotos pero la cotización no trae ese equipo: agrégalo.";
            } elseif ($quoted < $marked) {
                if (count($idx) === 1) {
                    $items[$idx[0]]['quantity'] = (float) $marked;
                    $warnings[] = "Se ajustó «{$items[$idx[0]]['description']}» de ".self::qty($quoted)." a $marked según los puntos marcados en las fotos.";
                } else {
                    $warnings[] = "Marcaste $marked punto(s) de «{$name}» en las fotos y la cotización suma ".self::qty($quoted).': revisa las cantidades.';
                }
            } elseif ($quoted > $marked) {
                $warnings[] = 'La cotización trae '.self::qty($quoted)." de «{$name}» y en las fotos hay $marked marcados: confirma que no sobren.";
            }
        }

        return [$items, $warnings];
    }

    // ---- Motor 5: cálculos ------------------------------------------------------------------------------------------

    private const DEFAULTS = ['cable_waste_margin_pct' => 0.05, 'labor_hourly_rate' => 200.0, 'labor_max_hours_per_technician' => 40.0,
        'storage_gb_per_megapixel_per_day' => 15.0, 'storage_retention_days' => 30.0];
    private const INDIVISIBLE = ['caja', 'cajas', 'unidad', 'unidades', 'rollo', 'rollos', 'bobina', 'bobinas', 'pieza', 'piezas', 'paquete', 'paquetes', 'kit', 'kits'];

    public static function param(string $key, array $overrides): float
    {
        if (isset($overrides[$key])) {
            return $overrides[$key];
        }
        $row = CalculationParameter::where('key', $key)->first();

        return $row ? (float) $row->value : self::DEFAULTS[$key];
    }

    public static function cableWaste(array $items, array $catalog, float $pct): array
    {
        if (! $pct) {
            return $items;
        }
        $cables = [];
        foreach ($catalog as $p) {
            if (in_array('cable', $p['tags'] ?? [], true)) {
                $cables[$p['id']] = $p;
            }
        }
        if (! $cables) {
            return $items;
        }
        foreach ($items as &$it) {
            if (isset($cables[$it['product_id'] ?? 0])) {
                $q = $it['quantity'] * (1 + $pct);
                $unit = strtolower(trim((string) ($cables[$it['product_id']]['unit'] ?? '')));
                // Una caja o un rollo no se compra a medias; el epsilon evita que 2.0000000001 salte a 3.
                $it['quantity'] = in_array($unit, self::INDIVISIBLE, true) ? (float) ceil($q - 1e-9) : round($q, 2);
            }
        }

        return $items;
    }

    /** «16 conectores RJ45» con bolsa de 100 → 1 bolsa. Si el técnico ya habló en paquetes, se respeta. */
    public static function loosePacks(array $items, array $packSizes): array
    {
        $out = [];
        $notices = [];
        foreach ($items as $it) {
            $size = isset($it['product_id']) ? ($packSizes[$it['product_id']] ?? null) : null;
            if (! $size || $size <= 1 || preg_match('/\b(caja|cajas|bolsa|bolsas|paquete|paquetes|pack|packs|funda|fundas|rollo|rollos|bobina|bobinas|kit|kits)\b/', self::norm((string) ($it['description'] ?? '')))) {
                $out[] = $it;
                continue;
            }
            $loose = (float) ($it['quantity'] ?? 0);
            $packs = max(1, (int) ceil($loose / $size - 1e-9));
            $out[] = ['quantity' => (float) $packs] + $it;
            $notices[] = ($it['description'] ?? 'Producto').': '.self::qty($loose)." unidades sueltas se cotizan como $packs paquete(s) de $size.";
        }

        return [$out, $notices];
    }

    public static function storage(array $items, array $resolution, array $capacity, float $gbPerMp, float $days): array
    {
        $need = 0.0;
        foreach ($items as $it) {
            $mp = isset($it['product_id']) ? ($resolution[$it['product_id']] ?? null) : null;
            if ($mp) {
                $need += $mp * $gbPerMp * $days * (float) ($it['quantity'] ?? 0);
            }
        }
        if ($need <= 0) {
            return $items;
        }
        foreach ($items as &$it) {
            $cap = isset($it['product_id']) ? ($capacity[$it['product_id']] ?? null) : null;
            if ($cap) {
                $it['quantity'] = (float) max(ceil($need / $cap), (float) ($it['quantity'] ?? 0));
            }
        }

        return $items;
    }

    /** Horas, técnicos y costo de mano de obra; null si no hay nada que estimar. */
    public static function labor(array $items, array $profiles, float $rate, float $maxHours): ?array
    {
        $byRole = [];
        $total = 0.0;
        foreach ($items as $it) {
            $pid = $it['product_id'] ?? null;
            if ($pid === null || ! isset($profiles[$pid]) || ! $profiles[$pid][0]) {
                continue;
            }
            $min = $profiles[$pid][0] * (float) ($it['quantity'] ?? 0);
            if ($min <= 0) {
                continue;
            }
            $total += $min;
            $role = $profiles[$pid][1] ?: 'Sin rol asignado';
            $byRole[$role] = ($byRole[$role] ?? 0) + $min / 60;
        }
        if ($total <= 0) {
            return null;
        }
        $hours = round($total / 60, 2);

        return ['total_hours' => $hours, 'technician_count' => max(1, $maxHours ? (int) ceil($hours / $maxHours) : 1), 'hourly_rate' => $rate,
            'labor_cost' => round($hours * $rate, 2), 'hours_by_role' => array_map(fn ($h) => round($h, 2), $byRole)];
    }

    private static function laborItem(array $e): array
    {
        $break = implode(', ', array_map(fn ($r, $h) => "$r: {$h}h", array_keys($e['hours_by_role']), $e['hours_by_role']));

        return ['product_id' => null, 'quantity' => $e['total_hours'], 'unit_price' => $e['hourly_rate'],
            'description' => "Mano de obra de instalación — {$e['technician_count']} técnico(s), {$e['total_hours']}h estimadas ($break)"];
    }

    private static function capacityWarning(array $items, array $hubIds, array $consumerIds, array $capacity, string $label): ?string
    {
        $total = 0.0;
        $known = false;
        foreach ($items as $it) {
            $pid = $it['product_id'] ?? null;
            if ($pid !== null && isset($hubIds[$pid]) && ($capacity[$pid] ?? null) !== null) {
                $known = true;
                $total += $capacity[$pid] * (float) ($it['quantity'] ?? 0);
            }
        }
        if (! $known) {
            return null;
        }
        $consumers = 0.0;
        foreach ($items as $it) {
            if (isset($consumerIds[$it['product_id'] ?? 0])) {
                $consumers += (float) ($it['quantity'] ?? 0);
            }
        }

        return $consumers <= $total ? null : "$label: capacidad total de ".self::qty($total).' canal(es)/puerto(s) para '.self::qty($consumers).' cámara(s) — faltan '.self::qty($consumers - $total).'.';
    }

    // ---- orquestación -----------------------------------------------------------------------------------------------------

    private static function catalog(): array
    {
        return Product::with('category')->orderBy('code')->get()->map(fn ($p) => [
            'id' => $p->id, 'name' => $p->name, 'category' => $p->category?->name, 'unit' => $p->unit, 'tags' => $p->tags ?: [], 'synonyms' => $p->synonyms ?: [],
        ])->all();
    }

    /**
     * Interpreta, resuelve, aplica reglas y cálculos. No guarda nada.
     *
     * @return array{0: array, 1: string[], 2: string[]} [líneas, avisos, notas de ingeniería]
     */
    public static function computeItems(string $context, ?int $projectId = null): array
    {
        $products = Product::with('category')->orderBy('code')->get();
        $catalog = self::catalog();
        $technical = TechnicalRule::all();
        $prices = $products->mapWithKeys(fn ($p) => [$p->id => (float) $p->price])->all();

        $items = self::matchToCatalog(self::interpret($context), $catalog);
        // Antes de las reglas de accesorios: solo lo que el técnico dijo suelto se pasa a paquetes.
        [$items, $packNotices] = self::loosePacks($items, $products->mapWithKeys(fn ($p) => [$p->id => $p->pack_size])->all());
        $items = self::expandWithRules($items, $catalog, self::accessoryRules());
        // Los puntos marcados en las fotos son el dato más fiable de cuántos equipos van: se cuadran ANTES de calcular lo que depende de cantidades.
        $pointWarnings = [];
        if ($projectId !== null && ($counts = SurveyPoints::markerCounts($projectId))) {
            [$items, $pointWarnings] = self::reconcile($items, $counts, $products->mapWithKeys(fn ($p) => [$p->id => $p->category?->name])->all());
        }
        $over = self::paramOverrides($items, $technical);
        $notes = self::engineeringNotes($items, $technical);

        $items = self::cableWaste($items, $catalog, self::param('cable_waste_margin_pct', $over));
        $items = self::storage(
            $items,
            $products->mapWithKeys(fn ($p) => [$p->id => $p->resolution_mp !== null ? (float) $p->resolution_mp : null])->all(),
            $products->mapWithKeys(fn ($p) => [$p->id => $p->storage_capacity_gb !== null ? (float) $p->storage_capacity_gb : null])->all(),
            self::param('storage_gb_per_megapixel_per_day', $over),
            self::param('storage_retention_days', $over),
        );
        // Líneas que la IA entendió pero no están en el catálogo (ej. «rack»): quedan con precio 0 y se avisa.
        $unmatched = [];
        foreach ($items as $it) {
            if (($it['product_id'] ?? null) === null) {
                $unmatched[] = "«{$it['description']}» no coincide con ningún producto del catálogo (precio 0): ponle precio o quítala.";
            }
        }
        $labor = self::labor(
            $items,
            $products->mapWithKeys(fn ($p) => [$p->id => [$p->install_minutes !== null ? (float) $p->install_minutes : null, $p->labor_role]])->all(),
            self::param('labor_hourly_rate', $over),
            self::param('labor_max_hours_per_technician', $over),
        );
        if ($labor) {
            $items[] = self::laborItem($labor);
        }

        $tagged = fn (string $tag) => array_flip(array_column(array_filter($catalog, fn ($p) => in_array($tag, $p['tags'], true)), 'id'));
        $cameras = $tagged('camara');
        $cap = $products->mapWithKeys(fn ($p) => [$p->id => $p->channel_capacity])->all();
        $capWarnings = array_values(array_filter([
            self::capacityWarning($items, $tagged('nvr'), $cameras, $cap, 'NVR'),
            self::capacityWarning($items, $tagged('poe-switch'), $cameras, $cap, 'Switch PoE'),
        ]));
        foreach ($items as &$it) {
            if (($it['product_id'] ?? null) !== null) {
                $it['unit_price'] = $prices[$it['product_id']] ?? 0;
            }
        }

        return [$items, array_merge($pointWarnings, $packNotices, $unmatched, $capWarnings), $notes];
    }
}
