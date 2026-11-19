<?php

namespace App\Support;

use App\Models\Product;
use App\Models\Quote;

/**
 * Comparar una cotización ajena (competidor o proveedor) con el levantamiento y con la cotización propia. Dos partes separadas:
 *  1. LEER el documento (PDF o foto) y sacar sus líneas: aquí interviene la IA, por eso oficina puede corregir lo que entendió.
 *  2. COMPARAR: sin IA, con reglas fijas, así el resultado es el mismo cada vez y se puede explicar línea por línea.
 */
class QuoteCompare
{
    public const MAX_TEXT_CHARS = 14000;
    private const PRICE_TOLERANCE = 0.01; // 1 %: por debajo de esto el precio se da por igual
    private const MATCH_THRESHOLD = 0.34;
    private const STOP = ['de', 'del', 'la', 'el', 'los', 'las', 'para', 'con', 'y', 'en', 'un', 'una', 'por', 'x', 'ud', 'und', 'unidad'];
    private const SCHEMA = [
        'type' => 'object',
        'properties' => [
            'items' => ['type' => 'array', 'items' => [
                'type' => 'object',
                'properties' => ['description' => ['type' => 'string'], 'quantity' => ['type' => 'number'], 'unit_price' => ['type' => 'number']],
                'required' => ['description', 'quantity', 'unit_price'],
            ]],
            'total' => ['type' => ['number', 'null']],
        ],
        'required' => ['items'],
    ];

    // ---- 1. leer el documento ---------------------------------------------------------------------

    /** Texto de un PDF o de una foto. Gemini lee ambos (también PDF escaneados), así que no hace falta una librería de PDF. */
    public static function extractText(string $contents): string
    {
        $text = trim(Gemini::chat([['role' => 'user', 'images' => [$contents], 'content' => 'Transcribe el texto de esta cotización o factura tal como aparece, '
            .'una línea por producto, con su descripción, cantidad y precio unitario. Incluye el total si aparece. No inventes nada que no se vea.']],
            null, ['temperature' => 0, 'num_predict' => 4096]));
        if (mb_strlen($text) < 20) {
            throw new ApiException(400, 'No pude leer texto en ese archivo. Prueba con otro o pega el texto.');
        }

        return mb_substr($text, 0, self::MAX_TEXT_CHARS);
    }

    /** Solo líneas utilizables: con descripción, cantidad positiva y precio no negativo. */
    public static function cleanItems(array $raw): array
    {
        $out = [];
        foreach ($raw as $r) {
            if (! is_array($r) || ! is_numeric($r['quantity'] ?? 0) || ! is_numeric($r['unit_price'] ?? 0)) {
                continue;
            }
            $d = mb_substr(trim((string) ($r['description'] ?? '')), 0, 300);
            $q = (float) ($r['quantity'] ?? 0);
            $p = (float) ($r['unit_price'] ?? 0);
            if ($d !== '' && $q > 0 && $p >= 0) {
                $out[] = ['description' => $d, 'quantity' => $q, 'unit_price' => $p];
            }
        }

        return $out;
    }

    /** @return array{items: array, total: ?float} */
    public static function readItems(string $text): array
    {
        $prompt = 'Del siguiente texto de una cotización, saca cada línea de producto o servicio con su descripción, cantidad y precio UNITARIO '
            .'(si solo trae el total de la línea, divídelo entre la cantidad). Los precios son en pesos dominicanos salvo que diga otra cosa. '
            ."Ignora encabezados, datos del cliente y condiciones. Pon también el total del documento si aparece, o null.\n\n".$text;
        $d = Gemini::json([['role' => 'user', 'content' => $prompt]], self::SCHEMA, ['temperature' => 0, 'num_predict' => 4096]);
        $total = $d['total'] ?? null;

        return ['items' => self::cleanItems((array) ($d['items'] ?? [])), 'total' => is_numeric($total) ? (float) $total : null];
    }

    // ---- 2. comparar ------------------------------------------------------------------------------------

    private static function tokens(string $t): array
    {
        $plain = strtolower((string) iconv('UTF-8', 'ASCII//TRANSLIT//IGNORE', \Normalizer::normalize($t, \Normalizer::FORM_D) ?: $t));
        preg_match_all('/[a-z0-9]+/', $plain, $m);

        return array_values(array_unique(array_filter($m[0], fn ($w) => ! in_array($w, self::STOP, true) && strlen($w) > 1)));
    }

    public static function similarity(string $a, string $b): float
    {
        $ta = self::tokens($a);
        $tb = self::tokens($b);
        if (! $ta || ! $tb) {
            return 0.0;
        }

        return count(array_intersect($ta, $tb)) / count(array_unique(array_merge($ta, $tb)));
    }

    private static function priceState(float $ext, float $our): string
    {
        if ($our == 0 && $ext == 0) {
            return 'igual';
        }
        $base = $our ?: $ext;

        return abs($ext - $our) / $base <= self::PRICE_TOLERANCE ? 'igual' : ($ext > $our ? 'mas_caro' : 'mas_barato');
    }

    private static function line(array $o): array
    {
        return ['description' => $o['description'], 'quantity' => (float) $o['quantity'], 'unit_price' => (float) $o['unit_price']];
    }

    public static function compare(int $projectId, array $ext, ?float $extTotal, ?Quote $quote): array
    {
        $ours = [];
        foreach ($quote?->items ?? [] as $i) {
            $ours[] = ['description' => $i->description, 'quantity' => (float) $i->quantity, 'unit_price' => (float) $i->unit_price, 'product_id' => $i->product_id];
        }

        // Emparejamiento uno a uno, de la pareja más parecida a la menos parecida.
        $scored = [];
        foreach ($ext as $ei => $e) {
            foreach ($ours as $oi => $o) {
                $scored[] = [self::similarity($e['description'], $o['description']), $ei, $oi];
            }
        }
        usort($scored, fn ($a, $b) => [$b[0], $b[1], $b[2]] <=> [$a[0], $a[1], $a[2]]);
        $usedE = [];
        $usedO = [];
        $pairs = [];
        foreach ($scored as [$score, $ei, $oi]) {
            if ($score < self::MATCH_THRESHOLD || isset($usedE[$ei]) || isset($usedO[$oi])) {
                continue;
            }
            $usedE[$ei] = $usedO[$oi] = true;
            $pairs[] = [$ei, $oi];
        }
        usort($pairs, fn ($a, $b) => $a <=> $b);

        $matched = [];
        foreach ($pairs as [$ei, $oi]) {
            $e = $ext[$ei];
            $o = $ours[$oi];
            $sameQty = abs($e['quantity'] - $o['quantity']) < 0.01;
            $price = self::priceState($e['unit_price'], $o['unit_price']);
            $matched[] = [
                'external' => self::line($e), 'ours' => self::line($o), 'same_quantity' => $sameQty, 'price' => $price,
                'price_diff_pct' => round(($e['unit_price'] - $o['unit_price']) / ($o['unit_price'] ?: ($e['unit_price'] ?: 1)) * 100, 1),
                'status' => $sameQty && $price === 'igual' ? 'igual' : 'diferente',
            ];
        }
        $onlyExternal = [];
        foreach ($ext as $i => $e) {
            if (! isset($usedE[$i])) {
                $onlyExternal[] = self::line($e);
            }
        }
        $onlyOurs = [];
        foreach ($ours as $i => $o) {
            if (! isset($usedO[$i])) {
                $onlyOurs[] = self::line($o);
            }
        }

        // Cobertura del levantamiento: lo que el técnico marcó en las fotos frente a lo que trae cada cotización.
        $categoryOf = [];
        $ids = array_filter(array_column($ours, 'product_id'));
        if ($ids) {
            foreach (Product::with('category')->whereIn('id', $ids)->get() as $p) {
                $categoryOf[$p->id] = $p->category?->name;
            }
        }
        $coverage = [];
        foreach (SurveyPoints::markerCounts($projectId) as $kind => $marked) {
            if ($kind === 'otro' || ! array_key_exists($kind, SurveyPoints::KINDS)) {
                continue;
            }
            $extQty = array_sum(array_map(fn ($e) => $e['quantity'], array_filter($ext, fn ($e) => AiEngine::isKindLine($e, $kind, []))));
            $ourQty = array_sum(array_map(fn ($o) => $o['quantity'], array_filter($ours, fn ($o) => AiEngine::isKindLine($o, $kind, $categoryOf))));
            $status = fn ($q) => $q == $marked ? 'ok' : ($q < $marked ? 'falta' : 'sobra');
            $coverage[] = ['kind' => $kind, 'label' => SurveyPoints::LABELS[$kind] ?? 'Otro', 'marked' => $marked, 'external' => (float) $extQty, 'ours' => (float) $ourQty,
                'external_status' => $status($extQty), 'ours_status' => $status($ourQty)];
        }

        return [
            'matched' => $matched, 'only_external' => $onlyExternal, 'only_ours' => $onlyOurs, 'coverage' => $coverage,
            'totals' => [
                'external_subtotal' => round(array_sum(array_map(fn ($e) => $e['quantity'] * $e['unit_price'], $ext)), 2), 'external_total' => $extTotal,
                'our_subtotal' => $quote ? (float) $quote->subtotal : null, 'our_total' => $quote ? (float) $quote->total : null, 'our_code' => $quote?->code,
            ],
        ];
    }
}
