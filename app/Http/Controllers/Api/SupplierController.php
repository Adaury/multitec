<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Material;
use App\Models\Supplier;
use App\Support\ApiException;
use App\Support\V;
use Illuminate\Http\Request;

class SupplierController extends Controller
{
    private function find(int $id): Supplier
    {
        $s = Supplier::find($id);
        if (! $s) {
            throw new ApiException(404, 'Proveedor no encontrado');
        }

        return $s;
    }

    /** Create y update llevan los mismos campos; update los reemplaza todos (como la API original). */
    private function data(Request $r): array
    {
        $d = [];
        foreach (Supplier::FIELDS as $f => $max) {
            $d[$f] = V::text($r->input($f), $max, $f, $f === 'name');
        }

        return $d;
    }

    private function out(Supplier $s): array
    {
        return array_merge($s->only(array_keys(Supplier::FIELDS)), [
            'id' => $s->id, 'created_by' => $s->created_by, 'created_at' => $s->created_at, 'updated_at' => $s->updated_at,
        ]);
    }

    public function index()
    {
        return Supplier::orderBy('name')->get()->map(fn ($s) => $this->out($s))->values();
    }

    public function store(Request $r)
    {
        $s = Supplier::create($this->data($r) + ['created_by' => $r->attributes->get('user')->id, 'created_at' => now()]);

        return response()->json($this->out($s->fresh()), 201);
    }

    public function show(int $supplier_id)
    {
        return $this->out($this->find($supplier_id));
    }

    public function update(Request $r, int $supplier_id)
    {
        $s = $this->find($supplier_id);
        $s->update($this->data($r) + ['updated_at' => now()]);

        return $this->out($s->fresh());
    }

    /** Historial de compras: materiales comprados a este proveedor, con el código del proyecto. */
    public function purchases(int $supplier_id)
    {
        $this->find($supplier_id);

        return Material::with('supplier', 'project')->where('supplier_id', $supplier_id)
            ->orderByDesc('updated_at')->orderByDesc('created_at')->get()
            ->map(fn ($m) => $m->toOut() + ['project_code' => $m->project->code])->values();
    }
}
