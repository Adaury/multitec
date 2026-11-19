<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;

class LogEntryAsset extends Model
{
    use BelongsToCompany;

    public $timestamps = false;
    protected $guarded = ['id', 'company_id'];
    protected $casts = ['created_at' => 'datetime'];
}
