<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;

class Extension extends Model
{
    use BelongsToCompany;

    public const STATUSES = ['pendiente', 'aprobada', 'rechazada'];

    protected $guarded = ['id', 'company_id'];
    protected $casts = ['date' => 'date:Y-m-d', 'created_at' => 'datetime', 'updated_at' => 'datetime'];

    public function toOut(): array
    {
        return [
            'id' => $this->id, 'code' => $this->code, 'project_id' => $this->project_id, 'quote_id' => $this->quote_id,
            'title' => $this->title, 'description' => $this->description, 'status' => $this->status,
            'date' => $this->date?->format('Y-m-d'), 'created_by' => $this->created_by,
            'created_at' => $this->created_at, 'updated_at' => $this->updated_at,
        ];
    }
}
