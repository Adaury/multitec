<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Project;
use App\Models\User;
use App\Models\Visit;
use App\Support\Access;
use App\Support\ApiException;
use Illuminate\Http\Request;
use Illuminate\Support\Carbon;

class VisitController extends Controller
{
    private function find(int $id): Visit
    {
        $v = Visit::with('project.client', 'technician')->find($id);
        if (! $v) {
            throw new ApiException(404, 'Visita no encontrada');
        }

        return $v;
    }

    private function checkTechnician(?int $id): void
    {
        if ($id === null) {
            return;
        }
        $t = User::where('company_id', app('company_id'))->find($id);
        if (! $t) {
            throw new ApiException(404, 'Técnico no encontrado');
        }
        if (! $t->is_active) {
            throw new ApiException(400, 'Ese usuario está desactivado: elige otro técnico');
        }
    }

    private function validDate(?string $v, string $field): string
    {
        if (! $v || ! preg_match('/^\d{4}-\d{2}-\d{2}$/', $v) || ! strtotime($v)) {
            throw new ApiException(422, "$field inválida (usa AAAA-MM-DD)");
        }

        return $v;
    }

    private function validTime(?string $v): ?string
    {
        if ($v === null || $v === '') {
            return null;
        }
        if (! preg_match('/^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$/', $v)) {
            throw new ApiException(422, 'Hora inválida (usa HH:MM)');
        }

        return strlen($v) === 5 ? $v.':00' : $v;
    }

    private function duration($v): ?int
    {
        if ($v === null || $v === '') {
            return null;
        }
        if (! is_numeric($v) || $v < 5 || $v > 1440) {
            throw new ApiException(422, 'La duración debe estar entre 5 y 1440 minutos');
        }

        return (int) $v;
    }

    private function notes($v): ?string
    {
        if ($v !== null && mb_strlen((string) $v) > 2000) {
            throw new ApiException(422, 'Las notas exceden 2000 caracteres');
        }

        return $v;
    }

    public function index(Request $r)
    {
        $user = $r->attributes->get('user');
        $q = Visit::with('project.client', 'technician');
        if (Access::restricted($user)) { // técnico: sus visitas y las de sus proyectos
            $q->where(fn ($w) => $w->where('technician_id', $user->id)
                ->orWhereIn('project_id', Access::projectScope(Project::query(), $user)->select('projects.id')));
        }
        if ($r->filled('start')) {
            $q->where('scheduled_date', '>=', $this->validDate($r->query('start'), 'start'));
        }
        if ($r->filled('end')) {
            $q->where('scheduled_date', '<=', $this->validDate($r->query('end'), 'end'));
        }

        // Como PostgreSQL (el sistema original): las visitas sin hora van al final de su día.
        return $q->orderBy('scheduled_date')->orderByRaw('scheduled_time IS NULL')->orderBy('scheduled_time')->get()->map(fn ($v) => $v->toOut())->values();
    }

    public function store(Request $r)
    {
        $user = $r->attributes->get('user');
        $pid = (int) $r->input('project_id', 0);
        if (! Project::whereKey($pid)->exists() || ! Access::canSeeProject($user, $pid)) {
            throw new ApiException(404, 'Proyecto no encontrado');
        }
        $tech = $r->input('technician_id');
        $this->checkTechnician($tech !== null ? (int) $tech : null);
        $visit = Visit::create([
            'project_id' => $pid, 'technician_id' => $tech,
            'scheduled_date' => $this->validDate($r->input('scheduled_date'), 'Fecha'),
            'scheduled_time' => $this->validTime($r->input('scheduled_time')),
            'duration_min' => $this->duration($r->input('duration_min')),
            'notes' => $this->notes($r->input('notes')), 'status' => 'programada',
            'created_by' => $user->id, 'created_at' => now(),
        ]);

        return response()->json($this->find($visit->id)->toOut(), 201);
    }

    public function update(Request $r, int $visit_id)
    {
        $visit = $this->find($visit_id);
        $data = [];
        if ($r->has('status')) {
            if (! in_array($r->input('status'), Visit::STATUSES, true)) {
                throw new ApiException(400, 'Estado inválido: '.$r->input('status'));
            }
            $data['status'] = $r->input('status');
        }
        if ($r->has('technician_id')) {
            $t = $r->input('technician_id');
            $this->checkTechnician($t !== null ? (int) $t : null);
            $data['technician_id'] = $t;
        }
        if ($r->has('scheduled_date')) {
            $data['scheduled_date'] = $this->validDate($r->input('scheduled_date'), 'Fecha');
        }
        if ($r->has('scheduled_time')) {
            $data['scheduled_time'] = $this->validTime($r->input('scheduled_time'));
        }
        if ($r->has('duration_min')) {
            $data['duration_min'] = $this->duration($r->input('duration_min'));
        }
        if ($r->has('notes')) {
            $data['notes'] = $this->notes($r->input('notes'));
        }
        $visit->update($data + ['updated_at' => now()]);

        return $this->find($visit_id)->toOut();
    }

    /** Solo la persona asignada marca (o cualquiera si aún no hay nadie). Oficina y admin pueden marcar por otro. */
    private function punchVisit(Request $r, int $id): Visit
    {
        $visit = $this->find($id);
        $user = $r->attributes->get('user');
        if ($user->role === 'tecnico' && $visit->technician_id !== null && $visit->technician_id !== $user->id) {
            throw new ApiException(403, 'Esta visita está asignada a otro técnico');
        }

        return $visit;
    }

    private function coords(Request $r): array
    {
        $lat = $r->input('lat');
        $lng = $r->input('lng');
        if (($lat !== null && (! is_numeric($lat) || $lat < -90 || $lat > 90)) || ($lng !== null && (! is_numeric($lng) || $lng < -180 || $lng > 180))) {
            throw new ApiException(422, 'Coordenadas inválidas');
        }

        return [$lat !== null ? (float) $lat : null, $lng !== null ? (float) $lng : null];
    }

    public function checkin(Request $r, int $visit_id)
    {
        $visit = $this->punchVisit($r, $visit_id);
        if ($visit->status !== 'programada') {
            throw new ApiException(400, 'Esta visita ya no está pendiente de entrada');
        }
        [$lat, $lng] = $this->coords($r);
        $visit->update([
            'checkin_at' => Carbon::now(), 'checkin_lat' => $lat, 'checkin_lng' => $lng, 'status' => 'en_sitio',
            'technician_id' => $visit->technician_id ?? $r->attributes->get('user')->id, 'updated_at' => now(),
        ]);

        return $this->find($visit_id)->toOut();
    }

    public function checkout(Request $r, int $visit_id)
    {
        $visit = $this->punchVisit($r, $visit_id);
        if ($visit->status !== 'en_sitio') {
            throw new ApiException(400, 'Primero marca la entrada');
        }
        [$lat, $lng] = $this->coords($r);
        $visit->update([
            'checkout_at' => Carbon::now(), 'checkout_lat' => $lat, 'checkout_lng' => $lng,
            'status' => 'completada', 'updated_at' => now(),
        ]);

        return $this->find($visit_id)->toOut();
    }
}
