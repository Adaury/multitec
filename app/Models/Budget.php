<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Budget extends Model
{
    use BelongsToCompany;

    protected $guarded = ['id', 'company_id'];
    protected $casts = ['total' => 'float', 'ai_generated' => 'boolean', 'created_at' => 'datetime', 'updated_at' => 'datetime'];

    public function items(): HasMany
    {
        return $this->hasMany(BudgetItem::class)->orderBy('id');
    }

    public function project()
    {
        return $this->belongsTo(Project::class);
    }

    /** Sin precio unitario en las líneas: regla de negocio del presupuesto. */
    public function toOut(): array
    {
        return [
            'id' => $this->id, 'code' => $this->code, 'project_id' => $this->project_id, 'notes' => $this->notes,
            'total' => (float) $this->total, 'ai_generated' => (bool) $this->ai_generated, 'created_by' => $this->created_by,
            'created_at' => $this->created_at, 'updated_at' => $this->updated_at,
            'items' => $this->items->map(fn ($i) => [
                'id' => $i->id, 'description' => $i->description, 'quantity' => (float) $i->quantity,
                'product_id' => $i->product_id, 'note' => $i->note,
            ])->values(),
        ];
    }
}
