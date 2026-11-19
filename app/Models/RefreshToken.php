<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class RefreshToken extends Model
{
    public $timestamps = false;
    protected $guarded = [];
    protected $casts = ['revoked' => 'boolean', 'expires_at' => 'datetime', 'created_at' => 'datetime', 'last_used_at' => 'datetime'];
}
