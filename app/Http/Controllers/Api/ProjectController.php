<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Client;
use App\Models\Engineering;
use App\Models\Project;
use App\Models\ProjectStage;
use App\Models\Survey;
use App\Models\User;
use App\Support\Access;
use App\Support\ApiException;
use App\Support\Codes;
use Illuminate\Http\Request;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;

class ProjectController extends Controller
{
    /** Lo único que el técnico puede cambiar de un proyecto. */
    private const TECH_EDITABLE = ['address', 'location_url', 'survey_type'];
    private const TEXT_LIMITS = ['status' => 30, 'description' => 5000, 'address' => 5000, 'location_url' => 2048, 'survey_type' => 60];

    private function limited(Request $r, array $fields): array
    {
        $out = [];
        foreach ($fields as $f) {
            if ($r->has($f)) {
                $v = $r->input($f);
                if ($v !== null && mb_strlen((string) $v) > self::TEXT_LIMITS[$f]) {
                    throw new ApiException(422, "El campo $f excede ".self::TEXT_LIMITS[$f].' caracteres');
                }
                $out[$f] = $v;
            }
        }

        return $out;
    }

    private function userExists(?int $id): void
    {
        if ($id !== null && ! User::where('company_id', app('company_id'))->whereKey($id)->exists()) {
            throw new ApiException(404, 'Responsable no encontrado');
        }
    }

    public function index(Request $r)
    {
        $q = Access::projectScope(Project::query(), $r->attributes->get('user'));

        return $q->orderByDesc('created_at')->orderByDesc('id')->get()->map(fn ($p) => $p->toOut())->values();
    }

    public function store(Request $r)
    {
        $user = $r->attributes->get('user');
        $clientId = (int) $r->input('client_id', 0);
        if (! Client::whereKey($clientId)->exists() || ! Access::canSeeClient($user, $clientId)) {
            throw new ApiException(404, 'Cliente no encontrado');
        }
        $responsible = $r->input('responsible_id');
        $this->userExists($responsible !== null ? (int) $responsible : null);
        $date = $r->input('date');
        if ($date !== null && ! preg_match('/^\d{4}-\d{2}-\d{2}$/', (string) $date)) {
            throw new ApiException(422, 'Fecha inválida (usa AAAA-MM-DD)');
        }

        $project = DB::transaction(function () use ($r, $user, $clientId, $responsible, $date) {
            $project = Project::create([
                'code' => Codes::next('PRY'), 'client_id' => $clientId, 'responsible_id' => $responsible,
                'date' => $date ?? Carbon::now('America/Santo_Domingo')->toDateString(),
                'status' => 'levantamiento', 'created_by' => $user->id, 'created_at' => now(),
            ] + $this->limited($r, ['description', 'address', 'location_url', 'survey_type']));
            // Cada proyecto nace con su levantamiento e ingeniería vacíos (núcleo del ERP) y sus 5 etapas.
            Survey::create(['project_id' => $project->id, 'created_by' => $user->id, 'created_at' => now()]);
            Engineering::create(['project_id' => $project->id, 'created_by' => $user->id, 'created_at' => now()]);
            foreach (ProjectStage::NAMES as $order => $name) {
                ProjectStage::create(['project_id' => $project->id, 'name' => $name, 'order' => $order]);
            }

            return $project;
        });

        return response()->json($project->fresh()->toOut(), 201);
    }

    public function show(Request $r, int $project_id)
    {
        $project = Project::with('client')->find($project_id);
        if (! $project) {
            throw new ApiException(404, 'Proyecto no encontrado');
        }
        $out = $project->toOut();
        $out['client'] = $project->client;
        // El token del portal abre cotizaciones y facturas del cliente: el técnico no ve dinero ni ese enlace.
        $out['public_token'] = $r->attributes->get('user')->role === 'tecnico' ? null : $project->public_token;
        $out['portal_first_viewed_at'] = $project->portal_first_viewed_at;
        $out['portal_last_viewed_at'] = $project->portal_last_viewed_at;

        return $out;
    }

    public function update(Request $r, int $project_id)
    {
        $user = $r->attributes->get('user');
        $project = Project::find($project_id);
        if (! $project) {
            throw new ApiException(404, 'Proyecto no encontrado');
        }
        $fields = ['status', 'description', 'address', 'location_url', 'survey_type'];
        $data = $this->limited($r, $fields);
        if ($r->has('responsible_id')) {
            $data['responsible_id'] = $r->input('responsible_id');
        }
        if ($user->role === 'tecnico' && array_diff(array_keys($data), self::TECH_EDITABLE)) {
            throw new ApiException(403, 'No tienes permiso para realizar esta acción');
        }
        if (isset($data['responsible_id'])) {
            $this->userExists((int) $data['responsible_id']);
        }
        $project->update($data + ['updated_at' => now()]);

        return $project->fresh()->toOut();
    }

    public function margin(int $project_id)
    {
        if (! Project::whereKey($project_id)->exists()) {
            throw new ApiException(404, 'Proyecto no encontrado');
        }

        return \App\Support\Margin::project($project_id);
    }

    public function export()
    {
        $rows = Project::with('client')->orderByDesc('created_at')->get();
        $out = "\xEF\xBB\xBF".implode(',', ['Código', 'Cliente', 'Estado', 'Fecha', 'Descripción'])."\r\n";
        foreach ($rows as $p) {
            $line = [$p->code, $p->client->name, $p->status, $p->date?->format('Y-m-d'), $p->description];
            $out .= implode(',', array_map(fn ($v) => '"'.str_replace('"', '""', (string) $v).'"', $line))."\r\n";
        }

        return response($out, 200, ['Content-Type' => 'text/csv', 'Content-Disposition' => 'attachment; filename="proyectos.csv"']);
    }
}
