<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class PreInvoice extends Model
{
    use BelongsToCompany;

    protected $guarded = ['id', 'company_id'];
    protected $casts = ['subtotal' => 'float', 'itbis' => 'float', 'total' => 'float', 'created_at' => 'datetime', 'updated_at' => 'datetime'];

    public function items(): HasMany
    {
        return $this->hasMany(PreInvoiceItem::class)->orderBy('id');
    }

    public function toOut(): array
    {
        return [
            'id' => $this->id, 'code' => $this->code, 'project_id' => $this->project_id,
            'source_quote_id' => $this->source_quote_id, 'status' => $this->status, 'notes' => $this->notes,
            'subtotal' => (float) $this->subtotal, 'itbis' => (float) $this->itbis, 'total' => (float) $this->total,
            'created_by' => $this->created_by, 'created_at' => $this->created_at, 'updated_at' => $this->updated_at,
            'items' => $this->items->map(fn ($i) => [
                'id' => $i->id, 'product_id' => $i->product_id, 'description' => $i->description,
                'quantity' => (float) $i->quantity, 'unit_price' => (float) $i->unit_price,
                'subtotal' => (float) $i->subtotal, 'note' => $i->note,
            ])->values(),
        ];
    }
}
