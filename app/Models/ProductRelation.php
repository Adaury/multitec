<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;

class ProductRelation extends Model
{
    use BelongsToCompany;

    public const TYPES = ['compatible_con', 'alternativa_de', 'requiere'];

    public $timestamps = false;
    protected $guarded = ['id', 'company_id'];
    protected $casts = ['created_at' => 'datetime'];

    public function toOut(): array
    {
        return [
            'id' => $this->id, 'product_id' => $this->product_id, 'related_product_id' => $this->related_product_id,
            'relation_type' => $this->relation_type, 'notes' => $this->notes, 'created_at' => $this->created_at,
        ];
    }
}
