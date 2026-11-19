<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\CalculationParameter;
use App\Support\ApiException;
use App\Support\V;
use Illuminate\Http\Request;

class CalculationParameterController extends Controller
{
    /** Todas las claves conocidas, configuradas o no (una sin fila muestra su valor por defecto). */
    public function index()
    {
        $rows = CalculationParameter::all()->keyBy('key');

        return collect(CalculationParameter::KNOWN)->map(function ($meta, $key) use ($rows) {
            $row = $rows[$key] ?? null;

            return [
                'key' => $key, 'value' => $row ? (float) $row->value : $meta['default'],
                'description' => $row && $row->description ? $row->description : $meta['description'],
                'is_default' => $row === null, 'updated_at' => $row?->updated_at,
            ];
        })->values();
    }

    public function upsert(Request $r, string $key)
    {
        if (! array_key_exists($key, CalculationParameter::KNOWN)) {
            throw new ApiException(404, "Parámetro desconocido: $key");
        }
        $value = V::num($r->input('value'), 'value');
        if ($value === null) {
            throw new ApiException(422, 'El campo value es obligatorio');
        }
        $desc = V::text($r->input('description'), 200, 'description');
        $row = CalculationParameter::where('key', $key)->first();
        if (! $row) {
            $row = CalculationParameter::create(['key' => $key, 'value' => $value, 'description' => $desc, 'created_at' => now()]);
        } else {
            $row->update(['value' => $value, 'updated_at' => now()] + ($desc !== null ? ['description' => $desc] : []));
        }
        $row = $row->fresh();

        return [
            'key' => $row->key, 'value' => (float) $row->value,
            'description' => $row->description ?: CalculationParameter::KNOWN[$key]['description'],
            'is_default' => false, 'updated_at' => $row->updated_at,
        ];
    }
}
