<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Client;
use App\Models\ClientAsset;
use App\Models\Project;
use App\Support\ApiException;
use App\Support\Audit;
use App\Support\V;
use Illuminate\Http\Request;

/** Equipos instalados en casa o local de un cliente (serial, MAC, ubicación, garantía). */
class ClientAssetController extends Controller
{
    private const TEXT = ['brand' => 60, 'model' => 60, 'serial' => 80, 'ip_address' => 45, 'location' => 160, 'notes' => 2000];

    private function find(int $id): ClientAsset
    {
        $a = ClientAsset::find($id);
        if (! $a) {
            throw new ApiException(404, 'Equipo no encontrado');
        }

        return $a;
    }

    /** AA:BB:CC:DD:EE:FF a partir de AA-BB-…, aabb.ccdd.eeff o AABBCCDDEEFF. Vacío = sin MAC. */
    private function mac($v): ?string
    {
        if ($v === null || trim((string) $v) === '') {
            return null;
        }
        $d = strtoupper(preg_replace('/[^0-9A-Fa-f]/', '', (string) $v));
        if (! preg_match('/^[0-9A-F]{12}$/', $d)) {
            throw new ApiException(422, 'La MAC debe tener 12 dígitos hexadecimales (ej. AA:BB:CC:DD:EE:FF)');
        }

        return implode(':', str_split($d, 2));
    }

    private function date($v, string $f): ?string
    {
        if ($v === null || $v === '') {
            return null;
        }
        if (! is_string($v) || ! preg_match('/^\d{4}-\d{2}-\d{2}$/', $v) || ! strtotime($v)) {
            throw new ApiException(422, "$f inválida (usa AAAA-MM-DD)");
        }

        return $v;
    }

    private function checkProject(int $clientId, ?int $projectId): void
    {
        if ($projectId === null) {
            return;
        }
        $p = Project::find($projectId);
        if (! $p || $p->client_id !== $clientId) {
            throw new ApiException(400, 'Ese proyecto no es de este cliente');
        }
    }

    /** Valida los campos presentes (en alta: todos los de la ficha; en edición: solo los que lleguen). */
    private function data(Request $r, bool $create): array
    {
        $d = [];
        if ($create || $r->has('kind')) {
            $kind = $r->input('kind', 'otro');
            if ($kind !== null && ! in_array($kind, ClientAsset::KINDS, true)) {
                throw new ApiException(422, 'Tipo de equipo inválido: '.(is_scalar($kind) ? $kind : ''));
            }
            if ($kind !== null) { // un tipo nulo en edición no cambia nada
                $d['kind'] = $kind;
            }
        }
        if ($create || $r->has('name')) {
            $name = V::text($r->input('name'), 120, 'name', $create);
            if ($name !== null && trim($name) !== '') { // el nombre nunca se borra
                $d['name'] = trim($name);
            }
        }
        foreach (self::TEXT as $f => $max) {
            if ($r->has($f)) {
                $v = V::text($r->input($f), $max, $f);
                $d[$f] = $v !== null && trim($v) !== '' ? trim($v) : null;
            }
        }
        if ($r->has('mac')) {
            $d['mac'] = $this->mac($r->input('mac'));
        }
        if ($r->has('installed_on')) {
            $d['installed_on'] = $this->date($r->input('installed_on'), 'La fecha de instalación');
        }
        if ($r->has('warranty_until')) {
            $d['warranty_until'] = $this->date($r->input('warranty_until'), 'La fecha de garantía');
        }
        if ($r->has('project_id')) {
            $d['project_id'] = V::int($r->input('project_id'), 'project_id');
        }

        return $d;
    }

    public function index(int $client_id)
    {
        if (! Client::whereKey($client_id)->exists()) {
            throw new ApiException(404, 'Cliente no encontrado');
        }

        // Como PostgreSQL (el sistema original): los equipos sin ubicación van al final.
        return ClientAsset::where('client_id', $client_id)->orderByRaw('location IS NULL')->orderBy('location')->orderBy('name')->orderBy('id')->get()
            ->map(fn ($a) => $a->toOut())->values();
    }

    public function store(Request $r, int $client_id)
    {
        if (! Client::whereKey($client_id)->exists()) {
            throw new ApiException(404, 'Cliente no encontrado');
        }
        $d = $this->data($r, true);
        $this->checkProject($client_id, $d['project_id'] ?? null);
        $a = ClientAsset::create($d + ['client_id' => $client_id, 'created_by' => $r->attributes->get('user')->id, 'created_at' => now()]);

        return response()->json($a->fresh()->toOut(), 201);
    }

    public function update(Request $r, int $client_asset_id)
    {
        $a = $this->find($client_asset_id);
        $d = $this->data($r, false);
        if (array_key_exists('project_id', $d)) {
            $this->checkProject($a->client_id, $d['project_id']);
        }
        $a->update($d + ['updated_at' => now()]);

        return $a->fresh()->toOut();
    }

    public function destroy(Request $r, int $client_asset_id)
    {
        $a = $this->find($client_asset_id);
        Audit::log('client_asset_deleted', $r->attributes->get('user'), entity: 'client_asset', entityId: $a->id,
            detail: ['equipo' => $a->name, 'serial' => $a->serial, 'cliente_id' => $a->client_id], request: $r);
        $a->delete();

        return response()->noContent();
    }
}
