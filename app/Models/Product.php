<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Product extends Model
{
    use BelongsToCompany;

    public const FALLBACK_PREFIX = 'OTR';

    protected $guarded = ['id', 'company_id', 'code'];
    protected $casts = [
        'price' => 'float', 'cost' => 'float', 'stock_quantity' => 'float', 'price_estimated' => 'boolean',
        'install_minutes' => 'float', 'resolution_mp' => 'float', 'storage_capacity_gb' => 'float',
        'tags' => 'array', 'synonyms' => 'array', 'created_at' => 'datetime', 'updated_at' => 'datetime',
    ];

    public function category(): BelongsTo
    {
        return $this->belongsTo(Category::class);
    }

    /** Prefijo de código: el primero con code_prefix caminando por los ancestros de la categoría. */
    public static function resolvePrefix(?Category $category): string
    {
        for ($node = $category, $i = 0; $node && $i < 50; $node = $node->parent, $i++) {
            if ($node->code_prefix) {
                return $node->code_prefix;
            }
        }

        return self::FALLBACK_PREFIX;
    }

    /** Ruta legible de la clasificación, ej. "CCTV › Cámaras IP". */
    public function categoryPath(): ?string
    {
        if (! $this->category) {
            return null;
        }
        $parts = [];
        for ($node = $this->category, $i = 0; $node && $i < 50; $node = $node->parent, $i++) {
            $parts[] = $node->name;
        }

        return implode(' › ', array_reverse($parts));
    }

    public function toOut(): array
    {
        return [
            'id' => $this->id, 'code' => $this->code, 'category_id' => $this->category_id,
            'category_name' => $this->category?->name, 'category_path' => $this->categoryPath(),
            'name' => $this->name, 'unit' => $this->unit, 'price' => (float) $this->price,
            'price_estimated' => (bool) $this->price_estimated, 'cost' => $this->cost, 'stock_quantity' => (float) $this->stock_quantity,
            'notes' => $this->notes, 'brand' => $this->brand, 'model' => $this->model,
            'commercial_description' => $this->commercial_description, 'technical_description' => $this->technical_description,
            'install_minutes' => $this->install_minutes, 'labor_role' => $this->labor_role, 'priority' => $this->priority,
            'resolution_mp' => $this->resolution_mp, 'storage_capacity_gb' => $this->storage_capacity_gb,
            'channel_capacity' => $this->channel_capacity, 'pack_size' => $this->pack_size,
            'tags' => $this->tags ?: [], 'synonyms' => $this->synonyms ?: [],
            'created_by' => $this->created_by, 'created_at' => $this->created_at, 'updated_at' => $this->updated_at,
        ];
    }
}
