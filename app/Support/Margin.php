<?php

namespace App\Support;

use App\Models\Invoice;
use App\Models\InvoiceItem;
use App\Models\Product;
use App\Models\Quote;
use App\Models\QuoteItem;
use Illuminate\Support\Carbon;

/**
 * Venta, costo y margen en vivo contra el costo ACTUAL del catálogo (sin foto histórica por línea).
 * Una línea sin producto, o con costo sin cargar, suma a la venta pero no al costo: `lines_costed < lines_total`
 * avisa que el margen es parcial. Un costo real de 0 (artículo de regalo) sí cuenta como costeado.
 */
class Margin
{
    public static function empty(): array
    {
        return ['revenue' => 0.0, 'cost' => 0.0, 'margin' => 0.0, 'margin_pct' => null, 'lines_total' => 0, 'lines_costed' => 0, 'basis' => 'ninguno'];
    }

    public static function compute(iterable $items, string $basis): array
    {
        $items = collect($items);
        $ids = $items->pluck('product_id')->filter()->unique()->all();
        $costs = $ids ? Product::whereIn('id', $ids)->get(['id', 'cost'])->mapWithKeys(fn ($p) => [$p->id => $p->cost])->all() : [];

        $revenue = 0;
        $cost = 0;
        $costed = 0;
        foreach ($items as $i) {
            $revenue += Money::cents($i->subtotal);
            $unit = $i->product_id !== null ? ($costs[$i->product_id] ?? null) : null;
            if ($unit !== null) {
                $cost += Money::line($i->quantity, $unit);
                $costed++;
            }
        }
        $margin = $revenue - $cost;

        return [
            'revenue' => Money::fromCents($revenue), 'cost' => Money::fromCents($cost), 'margin' => Money::fromCents($margin),
            'margin_pct' => $revenue ? round($margin / $revenue, 4) : null,
            'lines_total' => $items->count(), 'lines_costed' => $costed, 'basis' => $basis,
        ];
    }

    /** Lo realmente facturado; si todavía no hay facturas, lo proyectado de las cotizaciones aprobadas; si no, ceros. */
    public static function project(int $projectId): array
    {
        $inv = InvoiceItem::whereIn('invoice_id', Invoice::where('project_id', $projectId)->whereNull('voided_at')->select('id'))->get();
        if ($inv->isNotEmpty()) {
            return self::compute($inv, 'facturado');
        }
        $q = QuoteItem::whereIn('quote_id', Quote::where('project_id', $projectId)->where('status', 'aprobada')->select('id'))->get();

        return $q->isNotEmpty() ? self::compute($q, 'cotizado') : self::empty();
    }

    /** Margen agregado de la empresa sobre las facturas de los últimos N meses. */
    public static function company(int $months = 6): array
    {
        $start = Carbon::now('America/Santo_Domingo')->startOfMonth()->subMonths($months - 1)->utc();
        $items = InvoiceItem::whereIn('invoice_id', Invoice::where('created_at', '>=', $start)->whereNull('voided_at')->select('id'))->get();

        return self::compute($items, 'facturado');
    }
}
