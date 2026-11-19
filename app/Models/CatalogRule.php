<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;

class CatalogRule extends Model
{
    use BelongsToCompany;

    public $timestamps = false;
    protected $guarded = ['id', 'company_id'];
    protected $casts = ['per_source_units' => 'float', 'quantity' => 'float', 'created_at' => 'datetime'];

    public function toOut(): array
    {
        return [
            'id' => $this->id, 'source_product_id' => $this->source_product_id, 'target_tag' => $this->target_tag,
            'per_source_units' => $this->per_source_units, 'quantity' => (float) $this->quantity,
            'notes' => $this->notes, 'created_at' => $this->created_at,
        ];
    }
}
