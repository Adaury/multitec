<?php

namespace App\Support;

use App\Models\Material;
use App\Models\PreInvoice;
use App\Models\Quote;
use App\Models\QuoteHistory;
use Illuminate\Support\Carbon;

class QuoteApproval
{
    /** Las líneas que se convertirán en materiales si la cotización se aprueba (la vista previa usa lo mismo). */
    public static function materialRows(Quote $quote): array
    {
        return $quote->items->map(fn ($i) => [
            'product_id' => $i->product_id, 'description' => $i->description, 'quantity' => (float) $i->quantity,
        ])->values()->all();
    }

    /**
     * Aprueba la cotización, genera la lista de materiales y la prefactura — las dos una sola vez por cotización,
     * aunque se re-apruebe tras reactivarla. No abre transacción: lo hace quien llama.
     */
    public static function approve(Quote $quote, ?int $userId, ?string $note = null): void
    {
        $quote->update(['status' => 'aprobada', 'decided_at' => Carbon::now(), 'updated_at' => now()]);
        QuoteHistory::add($quote->id, 'aprobada', $note);

        if (! Material::where('source_quote_id', $quote->id)->exists()) {
            foreach (self::materialRows($quote) as $row) {
                Material::create($row + [
                    'project_id' => $quote->project_id, 'source_quote_id' => $quote->id, 'status' => 'pendiente_compra',
                    'created_by' => $userId, 'created_at' => now(),
                ]);
            }
        }
        self::preInvoice($quote, $userId);
    }

    /** Copia la cotización aprobada a una prefactura (mismos totales y líneas). Idempotente por cotización. */
    public static function preInvoice(Quote $quote, ?int $userId): PreInvoice
    {
        $existing = PreInvoice::where('source_quote_id', $quote->id)->first();
        if ($existing) {
            return $existing;
        }
        $pre = PreInvoice::create([
            'code' => Codes::next('PFC'), 'project_id' => $quote->project_id, 'source_quote_id' => $quote->id,
            'notes' => $quote->notes, 'subtotal' => $quote->subtotal, 'itbis' => $quote->itbis, 'total' => $quote->total,
            'created_by' => $userId, 'created_at' => now(),
        ]);
        foreach ($quote->items as $i) {
            $pre->items()->create([
                'product_id' => $i->product_id, 'description' => $i->description, 'quantity' => $i->quantity,
                'unit_price' => $i->unit_price, 'subtotal' => $i->subtotal, 'note' => $i->note,
            ]);
        }

        return $pre;
    }
}
