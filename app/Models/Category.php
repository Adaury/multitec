<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Category extends Model
{
    use BelongsToCompany;

    public $timestamps = false;
    protected $guarded = ['id', 'company_id'];
    protected $casts = ['created_at' => 'datetime'];

    public function parent(): BelongsTo
    {
        return $this->belongsTo(Category::class, 'parent_id');
    }

    public function toOut(): array
    {
        return [
            'id' => $this->id, 'name' => $this->name, 'slug' => $this->slug, 'code_prefix' => $this->code_prefix,
            'parent_id' => $this->parent_id, 'created_at' => $this->created_at,
        ];
    }
}
