<?php

namespace App\Support;

use App\Models\Product;
use Illuminate\Http\Request;

/** Líneas de presupuesto / cotización / factura: validación y relleno desde el catálogo. */
class DocItems
{
    /**
     * Valida y normaliza las líneas que vienen en la petición.
     * unit_price null = «no lo mandó» (precio del catálogo si hay producto, o 0 si es texto libre); un 0 explícito se respeta.
     *
     * @return array<int, array{product_id:?int,description:string,quantity:float,unit_price:float,note:?string}>
     */
    public static function fromRequest(Request $r): array
    {
        $items = $r->input('items', []);
        if (! is_array($items)) {
            throw new ApiException(422, 'items debe ser una lista');
        }
        $out = [];
        foreach ($items as $i => $it) {
            if (! is_array($it)) {
                throw new ApiException(422, 'Cada línea debe ser un objeto');
            }
            $n = $i + 1;
            $productId = V::int($it['product_id'] ?? null, "product_id (línea $n)");
            $description = V::text($it['description'] ?? null, 500, "description (línea $n)") ?? '';
            $qty = V::num($it['quantity'] ?? 1, "quantity (línea $n)", null, 0) ?? 1.0;
            $price = V::num($it['unit_price'] ?? null, "unit_price (línea $n)", 0.0);
            $note = V::text($it['note'] ?? null, 500, "note (línea $n)");

            if ($productId !== null) {
                $product = Product::find($productId);
                if (! $product) {
                    throw new ApiException(400, "Producto $productId no encontrado");
                }
                $description = $description !== '' ? $description : $product->name;
                $price ??= (float) $product->price;
            } else {
                $price ??= 0.0;
            }
            if (trim($description) === '') {
                throw new ApiException(422, "La descripción es obligatoria (línea $n)");
            }
            $out[] = ['product_id' => $productId, 'description' => $description, 'quantity' => $qty, 'unit_price' => $price, 'note' => $note];
        }

        return $out;
    }
}
