<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class LogEntry extends Model
{
    use BelongsToCompany;

    protected $guarded = ['id', 'company_id'];
    protected $casts = ['entry_date' => 'date:Y-m-d', 'created_at' => 'datetime', 'updated_at' => 'datetime'];

    public function assets(): HasMany
    {
        return $this->hasMany(LogEntryAsset::class)->orderBy('id');
    }

    public function toOut(): array
    {
        return [
            'id' => $this->id, 'project_id' => $this->project_id, 'comment' => $this->comment,
            'entry_date' => $this->entry_date?->format('Y-m-d'), 'responsible_id' => $this->responsible_id,
            'created_at' => $this->created_at,
            'assets' => $this->assets->map(fn ($a) => [
                'id' => $a->id, 'file_path' => $a->file_path, 'description' => $a->description, 'created_at' => $a->created_at,
            ])->values(),
        ];
    }
}
