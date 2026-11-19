<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Client;
use App\Support\Access;
use App\Support\ApiException;
use Illuminate\Http\Request;

class ClientController extends Controller
{
    private const FIELDS = [
        'name' => 150, 'company' => 150, 'rnc' => 30, 'phone' => 30,
        'email' => 255, 'address' => 5000, 'location_url' => 2048, 'notes' => 5000,
    ];

    private function data(Request $r, bool $partial = false): array
    {
        $out = [];
        foreach (self::FIELDS as $f => $max) {
            if (! $r->has($f)) {
                continue;
            }
            $v = $r->input($f);
            $v = is_string($v) ? $v : ($v === null ? null : (string) $v);
            if ($v !== null && mb_strlen($v) > $max) {
                throw new ApiException(422, "El campo $f excede $max caracteres");
            }
            $out[$f] = $v;
        }
        if (! $partial && (! isset($out['name']) || trim($out['name']) === '')) {
            throw new ApiException(422, 'El nombre es obligatorio');
        }

        return $out;
    }

    private function find(int $id): Client
    {
        $c = Client::find($id);
        if (! $c) {
            throw new ApiException(404, 'Cliente no encontrado');
        }

        return $c;
    }

    public function index(Request $r)
    {
        // técnico: los de sus proyectos y los que él creó
        $q = Access::clientScope(Client::query(), $r->attributes->get('user'));

        return $q->orderBy('name')->get();
    }

    public function store(Request $r)
    {
        $c = Client::create($this->data($r) + ['created_by' => $r->attributes->get('user')->id, 'created_at' => now()]);

        return response()->json($c->fresh(), 201);
    }

    public function show(int $client_id)
    {
        return $this->find($client_id);
    }

    public function update(Request $r, int $client_id)
    {
        $c = $this->find($client_id);
        $c->update($this->data($r, true));

        return $c->fresh();
    }

    public function export()
    {
        $rows = Client::orderBy('name')->get();
        $h = ['Código', 'Nombre', 'Empresa', 'RNC', 'Teléfono', 'Correo', 'Dirección'];
        $out = "\xEF\xBB\xBF".implode(',', $h)."\r\n";
        foreach ($rows as $c) {
            $line = [$c->id, $c->name, $c->company, $c->rnc, $c->phone, $c->email, $c->address];
            $out .= implode(',', array_map(fn ($v) => '"'.str_replace('"', '""', (string) $v).'"', $line))."\r\n";
        }

        return response($out, 200, ['Content-Type' => 'text/csv', 'Content-Disposition' => 'attachment; filename="clientes.csv"']);
    }
}
