<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class PlatformPlan extends Model
{
    public $timestamps = false;
    protected $guarded = ['id'];
    protected $casts = [
        'monthly_price' => 'float', 'setup_price' => 'float', 'features' => 'array', 'highlighted' => 'boolean',
        'active' => 'boolean', 'created_at' => 'datetime',
    ];

    public function toOut(): array
    {
        return [
            'name' => $this->name, 'description' => $this->description, 'monthly_price' => (float) $this->monthly_price,
            'setup_price' => (float) $this->setup_price, 'max_users' => $this->max_users, 'features' => $this->features ?: [],
            'highlighted' => (bool) $this->highlighted, 'active' => (bool) $this->active, 'sort' => (int) $this->sort, 'id' => $this->id,
        ];
    }
}
