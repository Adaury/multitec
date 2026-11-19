<?php

namespace App\Support;

use App\Models\Category;
use App\Models\Product;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

/**
 * Lo que recibe una empresa nueva: el árbol de clasificaciones y, si se pide, el catálogo base de artículos SIN
 * precio (marcados «precio estimado»). Trabaja dentro de la empresa activa (app('company_id')): nunca copia nada de otra.
 */
class CatalogSeeder
{
    private static function fold(string $s): string
    {
        return mb_strtolower(Str::ascii($s));
    }

    private static function data(string $file): array
    {
        return json_decode((string) file_get_contents(database_path('data/'.$file)), true) ?: [];
    }

    /** Top-up idempotente del árbol de clasificaciones: crea las que no existan por slug y no toca las demás. */
    public static function categories(): void
    {
        $existing = Category::pluck('id', 'slug')->all();
        $insert = function (array $node, ?int $parentId) use (&$insert, &$existing) {
            if (isset($existing[$node['slug']])) {
                $id = $existing[$node['slug']];
            } else {
                $id = Category::create([
                    'name' => $node['name'], 'slug' => $node['slug'], 'code_prefix' => $node['code_prefix'] ?? null,
                    'parent_id' => $parentId, 'created_at' => now(),
                ])->id;
                $existing[$node['slug']] = $id;
            }
            foreach ($node['children'] ?? [] as $child) {
                $insert($child, $id);
            }
        };
        foreach (self::data('taxonomy.json') as $root) {
            $insert($root, null);
        }
    }

    private static function uniqueSlug(string $name): string
    {
        $base = Str::slug($name) ?: 'categoria';
        $slug = $base;
        for ($n = 2; Category::where('slug', $slug)->exists(); $n++) {
            $slug = $base.'-'.$n;
        }

        return $slug;
    }

    /** Primeros niveles nuevos (Alarmas, Cerco Eléctrico, Domótica…) con su prefijo de código. */
    public static function ensureRoots(): void
    {
        $roots = [];
        foreach (Category::whereNull('parent_id')->get() as $c) {
            $roots[self::fold($c->name)] = $c;
        }
        foreach (self::data('base_catalog.json')['roots'] ?? [] as $name => $prefix) {
            $found = $roots[self::fold($name)] ?? null;
            if (! $found) {
                Category::create(['name' => $name, 'slug' => self::uniqueSlug($name), 'code_prefix' => $prefix, 'created_at' => now()]);
            } elseif (! $found->code_prefix) {
                $found->update(['code_prefix' => $prefix]);
            }
        }
    }

    /** Busca (o crea) la categoría de una ruta como «CCTV > Cámaras Domo». @param array<string,Category> $byPath */
    private static function resolvePath(string $raw, array &$byPath): Category
    {
        $parts = array_values(array_filter(array_map('trim', preg_split('/\s*[>\/]\s*/', $raw))));
        $parent = null;
        foreach ($parts as $depth => $_) {
            $key = self::fold(implode(' > ', array_slice($parts, 0, $depth + 1)));
            $node = $byPath[$key] ?? null;
            if (! $node && $depth === 0) {
                $node = collect($byPath)->first(fn ($c) => $c->parent_id === null && self::fold($c->name) === $key);
            }
            if (! $node) {
                $node = Category::create([
                    'name' => mb_substr($parts[$depth], 0, 120), 'slug' => self::uniqueSlug($parts[$depth]),
                    'parent_id' => $parent?->id, 'created_at' => now(),
                ]);
                $byPath[$key] = $node;
            }
            $parent = $node;
        }

        return $parent;
    }

    /** Crea los artículos base que todavía no existan (sin precio). Lo que ya está con ese nombre no se toca. Devuelve cuántos creó. */
    public static function baseCatalog(?int $userId): int
    {
        $byPath = [];
        $all = Category::all();
        $byId = $all->keyBy('id');
        foreach ($all as $c) {
            $names = [];
            for ($n = $c, $i = 0; $n && $i < 20; $n = $byId[$n->parent_id] ?? null, $i++) {
                array_unshift($names, $n->name);
            }
            $byPath[self::fold(implode(' > ', $names))] = $c;
        }
        $existing = Product::pluck('id', 'name')->mapWithKeys(fn ($id, $name) => [self::fold($name) => $id])->all();
        $created = 0;

        DB::transaction(function () use (&$byPath, &$existing, &$created, $userId) {
            foreach (self::data('base_catalog.json')['rows'] ?? [] as $row) {
                [$name, $cat, $unit, , , $brand, $model, $desc, $tags, $syn] = array_pad($row, 11, '');
                $name = trim($name);
                if ($name === '' || isset($existing[self::fold($name)]) || trim($cat) === '') {
                    continue;
                }
                $category = self::resolvePath($cat, $byPath);
                $split = fn ($v) => array_values(array_filter(array_map('trim', explode(';', (string) $v))));
                $p = new Product([
                    'name' => $name, 'unit' => trim($unit) ?: 'unidad', 'price' => 0, 'price_estimated' => true,
                    'brand' => trim($brand) ?: null, 'model' => trim($model) ?: null,
                    'commercial_description' => trim($desc) ?: null, 'tags' => $split($tags), 'synonyms' => $split($syn),
                ]);
                $p->code = Codes::next(Product::resolvePrefix($category->loadMissing('parent')));
                $p->category_id = $category->id;
                $p->created_by = $userId;
                $p->created_at = now();
                $p->save();
                $existing[self::fold($name)] = $p->id;
                $created++;
            }
        });

        return $created;
    }
}
