<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Quote extends Model
{
    use BelongsToCompany;

    protected $guarded = ['id', 'company_id'];
    protected $casts = [
        'subtotal' => 'float', 'itbis' => 'float', 'total' => 'float', 'stale_notified' => 'boolean',
        'created_at' => 'datetime', 'updated_at' => 'datetime', 'decided_at' => 'datetime',
    ];

    public function items(): HasMany
    {
        return $this->hasMany(QuoteItem::class)->orderBy('id');
    }

    public function history(): HasMany
    {
        return $this->hasMany(QuoteHistory::class)->orderBy('created_at')->orderBy('id');
    }

    public function project(): BelongsTo
    {
        return $this->belongsTo(Project::class);
    }

    public function toOut(): array
    {
        return [
            'id' => $this->id, 'code' => $this->code, 'project_id' => $this->project_id,
            'source_budget_id' => $this->source_budget_id, 'status' => $this->status, 'notes' => $this->notes,
            'subtotal' => (float) $this->subtotal, 'itbis' => (float) $this->itbis, 'total' => (float) $this->total,
            'created_by' => $this->created_by, 'created_at' => $this->created_at, 'updated_at' => $this->updated_at,
            'decided_at' => $this->decided_at,
            'items' => $this->items->map(fn ($i) => [
                'id' => $i->id, 'product_id' => $i->product_id, 'description' => $i->description,
                'quantity' => (float) $i->quantity, 'unit_price' => (float) $i->unit_price,
                'subtotal' => (float) $i->subtotal, 'note' => $i->note,
            ])->values(),
        ];
    }
}
