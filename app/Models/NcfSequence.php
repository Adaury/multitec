<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;

class NcfSequence extends Model
{
    use BelongsToCompany;

    public $timestamps = false;
    protected $guarded = ['id', 'company_id'];
    protected $casts = ['active' => 'boolean', 'expires_at' => 'date:Y-m-d', 'created_at' => 'datetime'];

    public function toOut(): array
    {
        return [
            'id' => $this->id, 'ncf_type' => $this->ncf_type, 'description' => $this->description,
            'range_start' => $this->range_start, 'range_end' => $this->range_end, 'next_number' => $this->next_number,
            'expires_at' => $this->expires_at?->format('Y-m-d'), 'active' => (bool) $this->active,
            'created_by' => $this->created_by, 'created_at' => $this->created_at,
        ];
    }
}
