<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\CalculationParameter;
use App\Models\CatalogRule;
use App\Models\Category;
use App\Models\Product;
use App\Models\ProductRelation;
use App\Models\TechnicalRule;
use App\Support\ApiException;
use App\Support\Audit;
use App\Support\Codes;
use App\Support\V;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class CatalogController extends Controller
{
    // ---- productos ---------------------------------------------------------

    private const TEXT = ['notes' => 2000, 'brand' => 80, 'model' => 80, 'commercial_description' => 2000, 'technical_description' => 2000, 'labor_role' => 80, 'unit' => 30, 'name' => 255];

    private function category(int $id): Category
    {
        $c = Category::find($id);
        if (! $c) {
            throw new ApiException(400, "Categoría desconocida: $id");
        }

        return $c;
    }

    private function product(int $id): Product
    {
        $p = Product::with('category.parent')->find($id);
        if (! $p) {
            throw new ApiException(404, 'Producto no encontrado');
        }

        return $p;
    }

    /** Valida y normaliza los campos que vengan en la petición (solo los presentes). */
    private function productData(Request $r, bool $create): array
    {
        $d = [];
        foreach (self::TEXT as $f => $max) {
            if ($r->has($f)) {
                $d[$f] = V::text($r->input($f), $max, $f, $f === 'name' && ($create || $r->input($f) !== null));
            }
        }
        foreach (['price' => [0.0, null], 'cost' => [null, null], 'install_minutes' => [null, null], 'resolution_mp' => [null, null]] as $f => $_) {
            if ($r->has($f)) {
                $d[$f] = V::num($r->input($f), $f);
            }
        }
        if ($r->has('storage_capacity_gb')) {
            $d['storage_capacity_gb'] = V::num($r->input('storage_capacity_gb'), 'storage_capacity_gb', null, 0);
        }
        foreach (['priority', 'channel_capacity'] as $f) {
            if ($r->has($f)) {
                $d[$f] = V::int($r->input($f), $f);
            }
        }
        if ($r->has('pack_size')) {
            $d['pack_size'] = V::int($r->input('pack_size'), 'pack_size', 0);
        }
        if ($r->has('price_estimated') && $r->input('price_estimated') !== null) {
            $d['price_estimated'] = filter_var($r->input('price_estimated'), FILTER_VALIDATE_BOOLEAN);
        }
        foreach (['tags', 'synonyms'] as $f) {
            if ($r->has($f) && ($r->input($f) !== null || $create)) {
                $d[$f] = V::strings($r->input($f), $f);
            }
        }

        return $d;
    }

    public function index()
    {
        return Product::with('category.parent')->orderBy('code')->get()->map(fn ($p) => $p->toOut())->values();
    }

    public function store(Request $r)
    {
        $user = $r->attributes->get('user');
        $category = $this->category((int) $r->input('category_id', 0));
        $d = $this->productData($r, true);
        $d += ['price' => 0.0, 'unit' => 'unidad', 'tags' => [], 'synonyms' => []];
        $d['price'] = $d['price'] ?? 0.0;
        $product = DB::transaction(function () use ($category, $d, $user) {
            $p = new Product($d);
            $p->code = Codes::next(Product::resolvePrefix($category));
            $p->category_id = $category->id;
            $p->created_by = $user->id;
            $p->created_at = now();
            $p->save();

            return $p;
        });

        return response()->json($this->product($product->id)->toOut(), 201);
    }

    public function update(Request $r, int $product_id)
    {
        $user = $r->attributes->get('user');
        $p = $this->product($product_id);
        $d = $this->productData($r, false);
        if ($r->has('category_id') && $r->input('category_id') !== null) {
            $d['category_id'] = $this->category((int) $r->input('category_id'))->id;
        }
        if (array_key_exists('name', $d) && $d['name'] === null) {
            unset($d['name']);
        }
        if (array_key_exists('price', $d) && $d['price'] !== null && (float) $d['price'] !== (float) $p->price) {
            Audit::log('product_price_changed', $user, entity: 'product', entityId: $p->id,
                detail: ['producto' => $p->name, 'de' => (float) $p->price, 'a' => (float) $d['price']], request: $r);
            if (! array_key_exists('price_estimated', $d)) {
                $d['price_estimated'] = false; // un precio puesto a mano deja de ser «estimado»
            }
        }
        if (array_key_exists('price', $d) && $d['price'] === null) {
            unset($d['price']);
        }
        $p->update($d + ['updated_at' => now()]);

        return $this->product($product_id)->toOut();
    }

    public function bulkPrices(Request $r)
    {
        $items = $r->input('items');
        if (! is_array($items) || count($items) < 1 || count($items) > 2000) {
            throw new ApiException(422, 'Envía entre 1 y 2000 productos');
        }
        $ids = [];
        foreach ($items as $it) {
            $id = V::int($it['id'] ?? null, 'id');
            $price = V::num($it['price'] ?? null, 'price', 0.0);
            if ($id === null || $price === null) {
                throw new ApiException(422, 'Cada producto necesita id y price');
            }
            $ids[] = $id;
        }
        $products = Product::with('category.parent')->whereIn('id', $ids)->get()->keyBy('id');
        $missing = array_values(array_diff(array_unique($ids), $products->keys()->all()));
        if ($missing) {
            sort($missing);
            throw new ApiException(404, 'Productos no encontrados: ['.implode(', ', $missing).']');
        }
        $changes = [];
        DB::transaction(function () use ($items, $products, &$changes) {
            foreach ($items as $it) {
                $p = $products[(int) $it['id']];
                $new = (float) $it['price'];
                if ((float) $p->price !== $new) {
                    $changes[] = ['id' => $p->id, 'de' => (float) $p->price, 'a' => $new];
                }
                $p->update(['price' => $new, 'price_estimated' => false, 'updated_at' => now()]);
            }
        });
        if ($changes) {
            Audit::log('catalog_prices_changed', $r->attributes->get('user'), entity: 'product',
                detail: ['productos' => count($changes), 'cambios' => array_slice($changes, 0, 25)], request: $r);
        }

        return collect(array_unique($ids))->map(fn ($id) => $products[$id]->fresh('category.parent')->toOut())->values();
    }

    /** Importar/exportar planillas y listas base: todavía no migrado a esta versión. */
    public function notMigrated()
    {
        throw new ApiException(501, 'Esta función (importar/exportar catálogo por Excel o CSV) aún no está disponible en esta versión.');
    }

    // ---- reglas de accesorios (CatalogRule) -------------------------------

    private function requireProduct(int $id): Product
    {
        $p = Product::find($id);
        if (! $p) {
            throw new ApiException(404, 'Producto no encontrado');
        }

        return $p;
    }

    public function listRules(int $product_id)
    {
        return CatalogRule::where('source_product_id', $product_id)->orderBy('id')->get()->map(fn ($x) => $x->toOut())->values();
    }

    public function createRule(Request $r, int $product_id)
    {
        $this->requireProduct($product_id);
        $rule = CatalogRule::create([
            'source_product_id' => $product_id,
            'target_tag' => V::text($r->input('target_tag'), 60, 'target_tag', true),
            'per_source_units' => V::num($r->input('per_source_units'), 'per_source_units', null, 0),
            'quantity' => V::num($r->input('quantity', 1), 'quantity') ?? 1,
            'notes' => V::text($r->input('notes'), 200, 'notes'), 'created_at' => now(),
        ]);

        return response()->json($rule->fresh()->toOut(), 201);
    }

    public function updateRule(Request $r, int $rule_id)
    {
        $rule = CatalogRule::find($rule_id);
        if (! $rule) {
            throw new ApiException(404, 'Regla no encontrada');
        }
        $d = [];
        if ($r->has('target_tag')) {
            if ($r->input('target_tag') === null) {
                throw new ApiException(400, 'target_tag no puede ser nulo');
            }
            $d['target_tag'] = V::text($r->input('target_tag'), 60, 'target_tag', true);
        }
        if ($r->has('per_source_units')) {
            $d['per_source_units'] = V::num($r->input('per_source_units'), 'per_source_units', null, 0);
        }
        if ($r->has('quantity') && $r->input('quantity') !== null) {
            $d['quantity'] = V::num($r->input('quantity'), 'quantity');
        }
        if ($r->has('notes')) {
            $d['notes'] = V::text($r->input('notes'), 200, 'notes');
        }
        $rule->update($d);

        return $rule->fresh()->toOut();
    }

    public function deleteRule(int $rule_id)
    {
        $rule = CatalogRule::find($rule_id);
        if (! $rule) {
            throw new ApiException(404, 'Regla no encontrada');
        }
        $rule->delete();

        return response()->noContent();
    }

    // ---- reglas técnicas ---------------------------------------------------

    public function listTechnicalRules(int $product_id)
    {
        return TechnicalRule::where('source_product_id', $product_id)->orderBy('id')->get()->map(fn ($x) => $x->toOut())->values();
    }

    public function createTechnicalRule(Request $r, int $product_id)
    {
        $this->requireProduct($product_id);
        $type = $r->input('action_type', TechnicalRule::ADD_ACCESSORY);
        $notes = V::text($r->input('notes'), 200, 'notes');
        if ($type === TechnicalRule::ADD_ACCESSORY) {
            $params = [
                'target_tag' => V::text($r->input('target_tag'), 60, 'target_tag', true),
                'per_source_units' => V::num($r->input('per_source_units'), 'per_source_units', null, 0),
                'quantity' => V::num($r->input('quantity', 1), 'quantity') ?? 1.0,
            ];
        } elseif ($type === TechnicalRule::SET_PARAMETER) {
            $key = V::text($r->input('parameter_key'), 60, 'parameter_key', true);
            if (! array_key_exists($key, CalculationParameter::KNOWN)) {
                throw new ApiException(400, "Parámetro desconocido: $key");
            }
            $value = V::num($r->input('value'), 'value');
            if ($value === null) {
                throw new ApiException(422, 'El campo value es obligatorio');
            }
            $params = ['parameter_key' => $key, 'value' => $value];
        } elseif ($type === TechnicalRule::FLAG_NOTE) {
            $params = ['engineering_note' => V::text($r->input('engineering_note'), 500, 'engineering_note', true)];
        } else {
            throw new ApiException(422, "action_type no soportado: $type");
        }
        $rule = TechnicalRule::create([
            'source_product_id' => $product_id, 'action_type' => $type, 'action_params' => $params,
            'notes' => $notes, 'created_at' => now(),
        ]);

        return response()->json($rule->fresh()->toOut(), 201);
    }

    public function updateTechnicalRule(Request $r, int $rule_id)
    {
        $rule = TechnicalRule::find($rule_id);
        if (! $rule) {
            throw new ApiException(404, 'Regla no encontrada');
        }
        $params = [];
        if ($r->has('target_tag') && $r->input('target_tag') !== null) {
            $params['target_tag'] = V::text($r->input('target_tag'), 60, 'target_tag', true);
        }
        if ($r->has('per_source_units')) {
            $params['per_source_units'] = V::num($r->input('per_source_units'), 'per_source_units', null, 0);
        }
        if ($r->has('quantity') && $r->input('quantity') !== null) {
            $params['quantity'] = V::num($r->input('quantity'), 'quantity');
        }
        if ($r->has('parameter_key') && $r->input('parameter_key') !== null) {
            if (! array_key_exists($r->input('parameter_key'), CalculationParameter::KNOWN)) {
                throw new ApiException(400, 'Parámetro desconocido: '.$r->input('parameter_key'));
            }
            $params['parameter_key'] = $r->input('parameter_key');
        }
        if ($r->has('value') && $r->input('value') !== null) {
            $params['value'] = V::num($r->input('value'), 'value');
        }
        if ($r->has('engineering_note') && $r->input('engineering_note') !== null) {
            $params['engineering_note'] = V::text($r->input('engineering_note'), 500, 'engineering_note', true);
        }
        $data = [];
        if ($r->has('notes')) {
            $data['notes'] = V::text($r->input('notes'), 200, 'notes');
        }
        if ($params) {
            $data['action_params'] = array_merge($rule->action_params ?? [], $params);
        }
        $rule->update($data);

        return $rule->fresh()->toOut();
    }

    public function deleteTechnicalRule(int $rule_id)
    {
        $rule = TechnicalRule::find($rule_id);
        if (! $rule) {
            throw new ApiException(404, 'Regla no encontrada');
        }
        $rule->delete();

        return response()->noContent();
    }

    // ---- relaciones entre productos ---------------------------------------

    public function listRelations(int $product_id)
    {
        $rows = ProductRelation::where(fn ($q) => $q->where('product_id', $product_id)->orWhere('related_product_id', $product_id))
            ->orderBy('id')->get();
        $otherIds = $rows->map(fn ($x) => $x->product_id === $product_id ? $x->related_product_id : $x->product_id)->unique();
        $names = Product::whereIn('id', $otherIds)->pluck('name', 'id');

        return $rows->map(function ($x) use ($product_id, $names) {
            $outgoing = $x->product_id === $product_id;
            $related = $outgoing ? $x->related_product_id : $x->product_id;

            return [
                'id' => $x->id, 'relation_type' => $x->relation_type, 'direction' => $outgoing ? 'outgoing' : 'incoming',
                'related_product_id' => $related, 'related_product_name' => $names[$related] ?? null,
                'notes' => $x->notes, 'created_at' => $x->created_at,
            ];
        })->values();
    }

    public function createRelation(Request $r, int $product_id)
    {
        $this->requireProduct($product_id);
        $related = V::int($r->input('related_product_id'), 'related_product_id');
        $type = $r->input('relation_type');
        if (! in_array($type, ProductRelation::TYPES, true)) {
            throw new ApiException(422, 'relation_type inválido');
        }
        if ($related === $product_id) {
            throw new ApiException(400, 'Un producto no puede relacionarse consigo mismo');
        }
        if (! $related || ! Product::whereKey($related)->exists()) {
            throw new ApiException(400, "Producto $related no encontrado");
        }
        $rel = ProductRelation::create([
            'product_id' => $product_id, 'related_product_id' => $related, 'relation_type' => $type,
            'notes' => V::text($r->input('notes'), 200, 'notes'), 'created_at' => now(),
        ]);

        return response()->json($rel->fresh()->toOut(), 201);
    }

    public function updateRelation(Request $r, int $relation_id)
    {
        $rel = ProductRelation::find($relation_id);
        if (! $rel) {
            throw new ApiException(404, 'Relación no encontrada');
        }
        $d = [];
        if ($r->has('relation_type')) {
            if ($r->input('relation_type') === null) {
                throw new ApiException(400, 'relation_type no puede ser nulo');
            }
            if (! in_array($r->input('relation_type'), ProductRelation::TYPES, true)) {
                throw new ApiException(422, 'relation_type inválido');
            }
            $d['relation_type'] = $r->input('relation_type');
        }
        if ($r->has('notes')) {
            $d['notes'] = V::text($r->input('notes'), 200, 'notes');
        }
        $rel->update($d);

        return $rel->fresh()->toOut();
    }

    public function deleteRelation(int $relation_id)
    {
        $rel = ProductRelation::find($relation_id);
        if (! $rel) {
            throw new ApiException(404, 'Relación no encontrada');
        }
        $rel->delete();

        return response()->noContent();
    }
}
