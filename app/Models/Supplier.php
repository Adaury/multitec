<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;

class Supplier extends Model
{
    use BelongsToCompany;

    public const FIELDS = ['name' => 150, 'rnc' => 30, 'phone' => 30, 'email' => 255, 'address' => 5000, 'notes' => 5000];

    protected $guarded = ['id', 'company_id'];
    protected $casts = ['created_at' => 'datetime', 'updated_at' => 'datetime'];
}
