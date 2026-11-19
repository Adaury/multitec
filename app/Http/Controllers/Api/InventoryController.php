<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Product;
use App\Models\StockMovement;
use App\Support\ApiException;
use App\Support\V;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class InventoryController extends Controller
{
    private function product(int $id): Product
    {
        $p = Product::find($id);
        if (! $p) {
            throw new ApiException(404, 'Producto no encontrado');
        }

        return $p;
    }

    public function index(int $product_id)
    {
        $this->product($product_id);

        return StockMovement::where('product_id', $product_id)->orderByDesc('created_at')->orderByDesc('id')
            ->get()->map(fn ($m) => $m->toOut())->values();
    }

    public function store(Request $r, int $product_id)
    {
        $type = $r->input('movement_type');
        if (! in_array($type, ['entrada', 'salida'], true)) {
            throw new ApiException(422, "movement_type debe ser 'entrada' o 'salida'");
        }
        $qty = V::num($r->input('quantity'), 'quantity', null, 0);
        if ($qty === null) {
            throw new ApiException(422, 'La cantidad es obligatoria');
        }
        $reason = V::text($r->input('reason'), 2000, 'reason');

        $movement = DB::transaction(function () use ($product_id, $type, $qty, $reason, $r) {
            // lockForUpdate: dos salidas simultáneas no leen el mismo stock «viejo» y pasan ambas la revisión.
            $p = Product::lockForUpdate()->find($product_id);
            if (! $p) {
                throw new ApiException(404, 'Producto no encontrado');
            }
            $stock = (float) $p->stock_quantity;
            if ($type === 'salida' && $qty > $stock) {
                throw new ApiException(400, 'No hay suficiente stock: disponible '.V::g($stock).', se pidió sacar '.V::g($qty).'.');
            }
            $p->update(['stock_quantity' => $type === 'entrada' ? $stock + $qty : $stock - $qty]);

            return StockMovement::create([
                'product_id' => $product_id, 'movement_type' => $type, 'quantity' => $qty, 'reason' => $reason,
                'created_by' => $r->attributes->get('user')->id, 'created_at' => now(),
            ]);
        });

        return response()->json($movement->fresh()->toOut(), 201);
    }
}
