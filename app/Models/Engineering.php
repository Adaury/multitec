<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;

class Engineering extends Model
{
    use BelongsToCompany;

    protected $table = 'engineering';
    protected $guarded = ['id', 'company_id'];
    protected $casts = ['ai_generated' => 'boolean'];
}
