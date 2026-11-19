<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Survey extends Model
{
    use BelongsToCompany;

    protected $guarded = ['id', 'company_id'];
    protected $casts = ['created_at' => 'datetime', 'updated_at' => 'datetime'];

    public function assets(): HasMany
    {
        return $this->hasMany(SurveyAsset::class)->orderBy('id');
    }

    public function toOut(): array
    {
        return [
            'id' => $this->id, 'project_id' => $this->project_id, 'notes' => $this->notes,
            'measurements' => $this->measurements, 'observations' => $this->observations,
            'ai_summary' => $this->ai_summary, 'created_by' => $this->created_by,
            'created_at' => $this->created_at, 'updated_at' => $this->updated_at,
            'assets' => $this->assets->map(fn ($a) => $a->toOut())->values(),
        ];
    }
}
