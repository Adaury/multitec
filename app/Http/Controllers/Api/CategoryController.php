<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Category;
use App\Models\Product;
use App\Support\ApiException;
use App\Support\V;
use Illuminate\Http\Request;
use Illuminate\Support\Str;

class CategoryController extends Controller
{
    private function find(int $id): Category
    {
        $c = Category::find($id);
        if (! $c) {
            throw new ApiException(404, 'Categoría no encontrada');
        }

        return $c;
    }

    private function uniqueSlug(string $base, ?int $excludeId = null): string
    {
        $slug = $base;
        $n = 2;
        while (Category::where('slug', $slug)->when($excludeId, fn ($q) => $q->where('id', '!=', $excludeId))->exists()) {
            $slug = $base.'-'.$n++;
        }

        return $slug;
    }

    private function slugify(string $name): string
    {
        return Str::slug($name) ?: 'categoria';
    }

    public function index()
    {
        return Category::orderBy('name')->get()->map(fn ($c) => $c->toOut())->values();
    }

    public function store(Request $r)
    {
        $name = V::text($r->input('name'), 120, 'name', true);
        $parent = $r->input('parent_id');
        if ($parent !== null) {
            $this->find((int) $parent);
        }
        $c = Category::create([
            'name' => $name, 'slug' => $this->uniqueSlug($this->slugify($name)),
            'code_prefix' => V::text($r->input('code_prefix'), 10, 'code_prefix') ?: null,
            'parent_id' => $parent, 'created_at' => now(),
        ]);

        return response()->json($c->fresh()->toOut(), 201);
    }

    public function update(Request $r, int $category_id)
    {
        $c = $this->find($category_id);
        $data = [];
        if ($r->filled('parent_id')) {
            $pid = (int) $r->input('parent_id');
            if ($pid === $category_id) {
                throw new ApiException(400, 'Una categoría no puede ser su propio padre');
            }
            for ($node = $this->find($pid), $i = 0; $node && $i < 100; $node = $node->parent, $i++) {
                if ($node->id === $category_id) {
                    throw new ApiException(400, 'No se puede crear un ciclo en el árbol de categorías');
                }
            }
            $data['parent_id'] = $pid;
        } elseif ($r->has('parent_id')) {
            $data['parent_id'] = null; // pasar a categoría raíz
        }
        if ($r->has('name')) {
            if ($r->input('name') === null) {
                throw new ApiException(400, 'El nombre no puede ser nulo');
            }
            $data['name'] = V::text($r->input('name'), 120, 'name', true);
            if ($data['name'] !== $c->name) {
                $data['slug'] = $this->uniqueSlug($this->slugify($data['name']), $c->id);
            }
        }
        if ($r->has('code_prefix')) {
            $data['code_prefix'] = V::text($r->input('code_prefix'), 10, 'code_prefix');
        }
        $c->update($data);

        return $c->fresh()->toOut();
    }

    public function destroy(int $category_id)
    {
        $c = $this->find($category_id);
        if (Category::where('parent_id', $category_id)->exists()) {
            throw new ApiException(400, 'No se puede eliminar: tiene subcategorías');
        }
        if (Product::where('category_id', $category_id)->exists()) {
            throw new ApiException(400, 'No se puede eliminar: hay productos con esta categoría');
        }
        $c->delete();

        return response()->noContent();
    }
}
