<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class SurveyAsset extends Model
{
    use BelongsToCompany;

    public $timestamps = false;
    protected $guarded = ['id', 'company_id'];
    protected $casts = ['created_at' => 'datetime'];

    public function markers(): HasMany
    {
        return $this->hasMany(SurveyMarker::class, 'asset_id')->orderBy('number');
    }

    public function toOut(): array
    {
        return [
            'id' => $this->id, 'kind' => $this->kind, 'file_path' => $this->file_path,
            'description' => $this->description, 'created_at' => $this->created_at,
            'markers' => $this->markers->map(fn ($m) => $m->toOut())->values(),
        ];
    }
}
