<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use App\Support\SurveyPoints;
use Illuminate\Database\Eloquent\Model;

class SurveyMarker extends Model
{
    use BelongsToCompany;

    public $timestamps = false;
    protected $guarded = ['id', 'company_id'];
    protected $casts = ['x' => 'float', 'y' => 'float', 'created_at' => 'datetime'];

    public function toOut(): array
    {
        return [
            'id' => $this->id, 'number' => $this->number, 'label' => $this->label,
            'point_kind' => SurveyPoints::markerKind($this->kind, $this->label), 'x' => $this->x, 'y' => $this->y,
        ];
    }
}
