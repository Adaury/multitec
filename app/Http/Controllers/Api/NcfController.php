<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\NcfSequence;
use App\Support\ApiException;
use App\Support\Audit;
use App\Support\V;
use Illuminate\Http\Request;

class NcfController extends Controller
{
    public function index()
    {
        return NcfSequence::orderBy('ncf_type')->orderBy('expires_at')->orderBy('id')->get()->map(fn ($s) => $s->toOut())->values();
    }

    public function store(Request $r)
    {
        $user = $r->attributes->get('user');
        $type = (string) $r->input('ncf_type', '');
        if (! in_array($type, ['B01', 'B02', 'B14', 'B15'], true)) {
            throw new ApiException(422, 'ncf_type debe ser B01, B02, B14 o B15');
        }
        $desc = V::text($r->input('description'), 100, 'description', true);
        $start = V::int($r->input('range_start'), 'range_start', 0);
        $end = V::int($r->input('range_end'), 'range_end', 0);
        if ($start === null || $end === null) {
            throw new ApiException(422, 'range_start y range_end son obligatorios');
        }
        if ($end < $start) {
            throw new ApiException(422, 'range_end debe ser mayor o igual a range_start');
        }
        $exp = $r->input('expires_at');
        if (! is_string($exp) || ! preg_match('/^\d{4}-\d{2}-\d{2}$/', $exp) || ! strtotime($exp)) {
            throw new ApiException(422, 'expires_at inválida (usa AAAA-MM-DD)');
        }
        $seq = NcfSequence::create([
            'ncf_type' => $type, 'description' => $desc, 'range_start' => $start, 'range_end' => $end, 'next_number' => $start,
            'expires_at' => $exp, 'created_by' => $user->id, 'created_at' => now(),
        ]);
        Audit::log('ncf_sequence_created', $user, entity: 'ncf_sequence', entityId: $seq->id,
            detail: ['tipo' => $type, 'desde' => $start, 'hasta' => $end], request: $r);

        return response()->json($seq->fresh()->toOut(), 201);
    }

    public function update(Request $r, int $sequence_id)
    {
        $seq = NcfSequence::find($sequence_id);
        if (! $seq) {
            throw new ApiException(404, 'Secuencia NCF no encontrada');
        }
        if (! $r->has('active') || ! is_bool(filter_var($r->input('active'), FILTER_VALIDATE_BOOLEAN, FILTER_NULL_ON_FAILURE))) {
            throw new ApiException(422, 'El campo active es obligatorio');
        }
        $active = filter_var($r->input('active'), FILTER_VALIDATE_BOOLEAN);
        if ($seq->active !== $active) {
            Audit::log('ncf_sequence_toggled', $r->attributes->get('user'), entity: 'ncf_sequence', entityId: $seq->id,
                detail: ['tipo' => $seq->ncf_type, 'activa' => $active], request: $r);
        }
        $seq->update(['active' => $active]);

        return $seq->fresh()->toOut();
    }
}
