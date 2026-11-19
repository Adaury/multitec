<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;

class QuoteComparison extends Model
{
    use BelongsToCompany;

    public $timestamps = false;
    protected $guarded = ['id', 'company_id'];
    protected $casts = ['items' => 'array', 'total' => 'float', 'created_at' => 'datetime'];
}
