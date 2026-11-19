<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Material;
use App\Models\Product;
use App\Models\Project;
use App\Models\Supplier;
use App\Support\ApiException;
use App\Support\V;
use Illuminate\Http\Request;

class MaterialController extends Controller
{
    public function index(int $project_id)
    {
        return Material::with('supplier')->where('project_id', $project_id)->orderByDesc('created_at')->orderByDesc('id')
            ->get()->map(fn ($m) => $m->toOut())->values();
    }

    /** Lista inteligente de compras (§10): materiales pendientes de comprar. */
    public function purchaseList(int $project_id)
    {
        return Material::with('supplier')->where('project_id', $project_id)->where('status', 'pendiente_compra')
            ->orderBy('created_at')->orderBy('id')->get()->map(fn ($m) => $m->toOut())->values();
    }

    public function store(Request $r, int $project_id)
    {
        if (! Project::whereKey($project_id)->exists()) {
            throw new ApiException(404, 'Proyecto no encontrado');
        }
        $description = V::text($r->input('description'), 500, 'description');
        $productId = V::int($r->input('product_id'), 'product_id');
        if ($productId !== null) {
            $product = Product::find($productId);
            if (! $product) {
                throw new ApiException(400, "Producto $productId no encontrado");
            }
            $description = $description ?: $product->name;
        }
        if ($description === null || trim($description) === '') {
            throw new ApiException(422, 'La descripción es obligatoria');
        }
        $m = Material::create([
            'project_id' => $project_id, 'product_id' => $productId, 'description' => $description,
            'quantity' => V::num($r->input('quantity', 1), 'quantity') ?? 1, 'notes' => V::text($r->input('notes'), 2000, 'notes'),
            'status' => 'pendiente_compra', 'created_by' => $r->attributes->get('user')->id, 'created_at' => now(),
        ]);

        return response()->json($m->fresh('supplier')->toOut(), 201);
    }

    public function updateStatus(Request $r, int $material_id)
    {
        $status = $r->input('status');
        if (! in_array($status, Material::STATUSES, true)) {
            throw new ApiException(400, 'Estado inválido: '.(is_scalar($status) ? $status : ''));
        }
        $m = Material::find($material_id);
        if (! $m) {
            throw new ApiException(404, 'Material no encontrado');
        }
        $d = ['status' => $status, 'updated_at' => now()];
        // Opcionales: solo se aplican si vienen, para no borrar un proveedor/precio ya cargado.
        if ($r->input('supplier_id') !== null) {
            $sid = V::int($r->input('supplier_id'), 'supplier_id');
            if (! Supplier::whereKey($sid)->exists()) {
                throw new ApiException(400, "Proveedor $sid no encontrado");
            }
            $d['supplier_id'] = $sid;
        }
        if ($r->input('purchase_price') !== null) {
            $d['purchase_price'] = V::num($r->input('purchase_price'), 'purchase_price');
        }
        $m->update($d);

        return $m->fresh('supplier')->toOut();
    }
}
