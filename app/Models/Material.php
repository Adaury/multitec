<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Material extends Model
{
    use BelongsToCompany;

    public const STATUSES = ['disponible', 'pendiente_compra', 'comprado', 'instalado'];

    protected $guarded = ['id', 'company_id'];
    protected $casts = [
        'quantity' => 'float', 'purchase_price' => 'float', 'created_at' => 'datetime', 'updated_at' => 'datetime',
    ];

    public function supplier(): BelongsTo
    {
        return $this->belongsTo(Supplier::class);
    }

    public function project(): BelongsTo
    {
        return $this->belongsTo(Project::class);
    }

    public function toOut(): array
    {
        return [
            'id' => $this->id, 'project_id' => $this->project_id, 'product_id' => $this->product_id,
            'source_quote_id' => $this->source_quote_id, 'description' => $this->description,
            'quantity' => (float) $this->quantity, 'status' => $this->status, 'notes' => $this->notes,
            'supplier_id' => $this->supplier_id, 'purchase_price' => $this->purchase_price,
            'supplier_name' => $this->supplier?->name, 'created_by' => $this->created_by,
            'created_at' => $this->created_at, 'updated_at' => $this->updated_at,
        ];
    }
}
