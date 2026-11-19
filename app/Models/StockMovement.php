<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;

class StockMovement extends Model
{
    use BelongsToCompany;

    public $timestamps = false;
    protected $guarded = ['id', 'company_id'];
    protected $casts = ['quantity' => 'float', 'created_at' => 'datetime'];

    public function toOut(): array
    {
        return [
            'id' => $this->id, 'product_id' => $this->product_id, 'movement_type' => $this->movement_type,
            'quantity' => (float) $this->quantity, 'reason' => $this->reason, 'created_by' => $this->created_by,
            'created_at' => $this->created_at,
        ];
    }
}
