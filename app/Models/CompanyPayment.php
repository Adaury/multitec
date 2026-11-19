<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class CompanyPayment extends Model
{
    public $timestamps = false;
    protected $guarded = ['id'];
    protected $casts = ['amount' => 'float', 'paid_at' => 'date:Y-m-d', 'paid_until_after' => 'datetime', 'created_at' => 'datetime'];

    public function toOut(): array
    {
        return [
            'id' => $this->id, 'kind' => $this->kind, 'amount' => (float) $this->amount, 'months' => (int) $this->months,
            'method' => $this->method, 'reference' => $this->reference, 'notes' => $this->notes,
            'paid_at' => $this->paid_at?->format('Y-m-d'), 'paid_until_after' => $this->paid_until_after, 'created_at' => $this->created_at,
        ];
    }
}
