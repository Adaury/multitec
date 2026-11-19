<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Visit;
use App\Support\ApiException;
use App\Support\Csv;
use Illuminate\Http\Request;
use Illuminate\Support\Carbon;

/**
 * Hoja de tiempo: las horas que cada técnico estuvo en el sitio, sacadas de la entrada y salida que marca en cada visita (no se
 * teclean). Una visita sin salida aparece con minutos vacíos: sigue en curso o se olvidó marcar.
 */
class TimesheetController extends Controller
{
    private const TZ = 'America/Santo_Domingo';

    private function date(?string $v, string $field): ?Carbon
    {
        if ($v === null || $v === '') {
            return null;
        }
        if (! preg_match('/^\d{4}-\d{2}-\d{2}$/', $v) || ! checkdate((int) substr($v, 5, 2), (int) substr($v, 8, 2), (int) substr($v, 0, 4))) {
            throw new ApiException(422, "$field inválida (usa AAAA-MM-DD)");
        }

        return Carbon::createFromFormat('Y-m-d', $v, self::TZ)->startOfDay();
    }

    /** Por defecto, la semana en curso (lunes a hoy). @return array{0:Carbon,1:Carbon} */
    private function range(Request $r): array
    {
        $today = Carbon::now(self::TZ)->startOfDay();
        $first = $this->date($r->query('start'), 'start') ?? $today->copy()->startOfWeek(Carbon::MONDAY);
        $last = $this->date($r->query('end'), 'end') ?? $today;
        if ($last->lt($first)) {
            throw new ApiException(400, 'La fecha final no puede ser anterior a la inicial');
        }
        if ($first->diffInDays($last) > 366) {
            throw new ApiException(400, 'El rango no puede pasar de un año');
        }

        return [$first, $last];
    }

    private function rows(Carbon $first, Carbon $last, ?int $userId): array
    {
        $q = Visit::with('project.client', 'technician')
            ->whereBetween('scheduled_date', [$first->toDateString(), $last->toDateString()])
            ->whereNotNull('checkin_at')->where('status', '!=', 'cancelada');
        if ($userId !== null) {
            $q->where('technician_id', $userId);
        }
        $out = [];
        foreach ($q->orderBy('scheduled_date')->orderBy('checkin_at')->orderBy('id')->get() as $v) {
            $mins = $v->checkout_at ? max(0, (int) round(($v->checkout_at->getTimestamp() - $v->checkin_at->getTimestamp()) / 60)) : null;
            $out[] = [
                'visit_id' => $v->id, 'date' => $v->scheduled_date->format('Y-m-d'), 'technician_id' => $v->technician_id,
                'technician' => $v->technician?->name ?? 'Sin asignar', 'project_code' => $v->project->code,
                'client_name' => $v->project->client->name, 'checkin_at' => $v->checkin_at, 'checkout_at' => $v->checkout_at, 'minutes' => $mins,
            ];
        }

        return $out;
    }

    /** Total por técnico (solo las visitas con entrada y salida cuentan para las horas). */
    private function totals(array $rows): array
    {
        $t = [];
        foreach ($rows as $r) {
            $k = $r['technician_id'].'|'.$r['technician'];
            $t[$k] ??= ['technician_id' => $r['technician_id'], 'technician' => $r['technician'], 'visits' => 0, 'minutes' => 0, 'open' => 0];
            $t[$k]['visits']++;
            $r['minutes'] === null ? $t[$k]['open']++ : $t[$k]['minutes'] += $r['minutes'];
        }
        $t = array_values($t);
        usort($t, fn ($a, $b) => strcmp($a['technician'], $b['technician']));

        return $t;
    }

    private function userId(Request $r): ?int
    {
        $u = $r->query('user_id');
        if ($u === null || $u === '') {
            return null;
        }
        if (! ctype_digit((string) $u)) {
            throw new ApiException(422, 'user_id inválido');
        }

        return (int) $u;
    }

    public function show(Request $r)
    {
        [$first, $last] = $this->range($r);
        $rows = $this->rows($first, $last, $this->userId($r));

        return [
            'start' => $first->toDateString(), 'end' => $last->toDateString(), 'totals' => $this->totals($rows),
            'rows' => array_map(fn ($x) => $x + [], array_map(function ($x) {
                $x['checkin_at'] = $x['checkin_at']->toIso8601String();
                $x['checkout_at'] = $x['checkout_at']?->toIso8601String();

                return $x;
            }, $rows)),
        ];
    }

    public function export(Request $r)
    {
        [$first, $last] = $this->range($r);
        $csv = [];
        foreach ($this->rows($first, $last, $this->userId($r)) as $x) {
            $csv[] = [
                $x['date'], $x['technician'], $x['project_code'], $x['client_name'],
                $x['checkin_at']->copy()->setTimezone(self::TZ)->format('H:i'),
                $x['checkout_at'] ? $x['checkout_at']->copy()->setTimezone(self::TZ)->format('H:i') : '',
                $x['minutes'] !== null ? round($x['minutes'] / 60, 2) : '',
            ];
        }

        return Csv::response(Csv::build(['Fecha', 'Técnico', 'Proyecto', 'Cliente', 'Entrada', 'Salida', 'Horas'], $csv),
            'hoja-de-tiempo-'.$first->toDateString().'-'.$last->toDateString().'.csv');
    }
}
