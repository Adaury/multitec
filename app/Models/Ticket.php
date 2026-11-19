<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Ticket extends Model
{
    use BelongsToCompany;

    public const STATUSES = ['abierto', 'en_proceso', 'resuelto', 'cerrado'];
    public const OPEN = ['abierto', 'en_proceso'];

    protected $guarded = ['id', 'company_id'];
    protected $casts = ['created_at' => 'datetime', 'updated_at' => 'datetime', 'resolved_at' => 'datetime'];

    public function assets(): HasMany
    {
        return $this->hasMany(TicketAsset::class)->orderBy('id');
    }

    public function project(): BelongsTo
    {
        return $this->belongsTo(Project::class);
    }

    public function technician(): BelongsTo
    {
        return $this->belongsTo(User::class, 'technician_id');
    }

    public function toOut(): array
    {
        return [
            'id' => $this->id, 'code' => $this->code, 'project_id' => $this->project_id, 'technician_id' => $this->technician_id,
            'problem' => $this->problem, 'solution' => $this->solution, 'status' => $this->status, 'created_by' => $this->created_by,
            'created_at' => $this->created_at, 'updated_at' => $this->updated_at, 'resolved_at' => $this->resolved_at,
            'assets' => $this->assets->map(fn ($a) => [
                'id' => $a->id, 'file_path' => $a->file_path, 'description' => $a->description, 'created_at' => $a->created_at,
            ])->values(),
        ];
    }
}
