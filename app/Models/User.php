<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class User extends Model
{
    public $timestamps = false;
    protected $guarded = [];
    protected $hidden = ['hashed_password'];
    protected $casts = [
        'is_active' => 'boolean', 'must_change_password' => 'boolean', 'is_platform_admin' => 'boolean',
        'last_login_at' => 'datetime', 'created_at' => 'datetime',
    ];

    public function company(): BelongsTo
    {
        return $this->belongsTo(Company::class);
    }

    /** Igual que CurrentUser de la API original. */
    public function toCurrent(): array
    {
        return [
            'id' => $this->id, 'name' => $this->name, 'email' => $this->email, 'role' => $this->role,
            'assistant_alias' => $this->assistant_alias, 'must_change_password' => $this->must_change_password,
            'company_id' => $this->company_id, 'company_name' => $this->company->name,
            'is_platform_admin' => $this->is_platform_admin,
            'support_mode' => (bool) ($this->attributes['support_mode'] ?? false),
            'support_write' => (bool) ($this->attributes['support_write'] ?? false),
            'support_expires_at' => $this->attributes['support_expires_at'] ?? null,
        ];
    }
}
