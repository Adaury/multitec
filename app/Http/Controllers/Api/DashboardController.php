<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Client;
use App\Models\CompanyProfile;
use App\Models\Invoice;
use App\Models\Project;
use App\Models\Quote;
use App\Models\Ticket;
use App\Models\User;
use App\Support\Access;
use App\Support\Csv;
use App\Support\Money;
use App\Support\Notify;
use Illuminate\Http\Request;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;

class DashboardController extends Controller
{
    /** Cotizaciones «pendiente» con más de N días: el aviso es oportunista (sin cron), una sola vez por cotización. */
    private const STALE_DAYS = 3;

    private function staleQuotes(): array
    {
        $now = Carbon::now();
        $quotes = Quote::with('project.client')->where('status', 'pendiente')->where('created_at', '<=', $now->copy()->subDays(self::STALE_DAYS))
            ->orderBy('created_at')->get();
        $rows = [];
        $fresh = [];
        foreach ($quotes as $q) {
            $days = (int) $q->created_at->diffInDays($now);
            $rows[] = [
                'id' => $q->id, 'code' => $q->code, 'project_id' => $q->project_id, 'project_code' => $q->project->code,
                'client_name' => $q->project->client->name, 'total' => (float) $q->total, 'days_pending' => $days,
            ];
            if (! $q->stale_notified) {
                $fresh[] = [$q, $days];
            }
        }
        foreach ($fresh as [$q, $days]) {
            $q->update(['stale_notified' => true]);
        }
        foreach ($fresh as [$q, $days]) {
            Notify::quoteStale($q, $days);
        }

        return $rows;
    }

    private function lastMonths(int $n): array
    {
        $d = Carbon::now('America/Santo_Domingo')->startOfMonth();
        $out = [];
        for ($i = 0; $i < $n; $i++) {
            $out[] = $d->format('Y-m');
            $d = $d->copy()->subMonth();
        }

        return array_reverse($out);
    }

    public function summary()
    {
        $months = $this->lastMonths(6);
        $totals = array_fill_keys($months, 0);
        $start = Carbon::createFromFormat('Y-m-d', $months[0].'-01', 'America/Santo_Domingo')->startOfDay();
        foreach (Invoice::where('created_at', '>=', $start->copy()->utc())->whereNull('voided_at')->get(['created_at', 'total']) as $inv) {
            $key = Carbon::parse($inv->created_at)->setTimezone('America/Santo_Domingo')->format('Y-m');
            if (isset($totals[$key])) {
                $totals[$key] += Money::cents($inv->total);
            }
        }

        $byTech = Ticket::whereIn('status', Ticket::OPEN)->select('technician_id', DB::raw('count(*) as c'))->groupBy('technician_id')->get();
        $names = User::whereIn('id', $byTech->pluck('technician_id')->filter())->pluck('name', 'id');

        return [
            'projects_by_status' => Project::select('status', DB::raw('count(*) as c'))->groupBy('status')->get()
                ->map(fn ($r) => ['status' => $r->status, 'count' => (int) $r->c])->values(),
            'monthly_invoicing' => array_map(fn ($m) => ['month' => $m, 'total' => Money::fromCents($totals[$m])], $months),
            'quotes_pending' => Quote::where('status', 'pendiente')->count(),
            'open_tickets_by_technician' => $byTech->map(fn ($r) => [
                'technician' => $r->technician_id !== null ? ($names[$r->technician_id] ?? 'Sin asignar') : 'Sin asignar', 'count' => (int) $r->c,
            ])->values(),
            'open_tickets_total' => (int) $byTech->sum('c'),
            'stale_quotes' => $this->staleQuotes(),
        ];
    }

    public function companyMargin()
    {
        return \App\Support\Margin::company();
    }

    public function export()
    {
        $s = $this->summary();
        $rows = [['Cotizaciones pendientes', '', $s['quotes_pending']], ['Tickets abiertos', '', $s['open_tickets_total']]];
        foreach ($s['projects_by_status'] as $r) {
            $rows[] = ['Proyectos por estado', $r['status'], $r['count']];
        }
        foreach ($s['monthly_invoicing'] as $r) {
            $rows[] = ['Facturación mensual', $r['month'], $r['total']];
        }
        foreach ($s['open_tickets_by_technician'] as $r) {
            $rows[] = ['Tickets por técnico', $r['technician'], $r['count']];
        }

        return Csv::response(Csv::build(['Sección', 'Etiqueta', 'Valor'], $rows), 'dashboard.csv');
    }

    // ---- seguimientos de cobro -------------------------------------------------------------

    private function wa(?string $phone, string $message): ?string
    {
        $d = preg_replace('/\D/', '', (string) $phone);
        if (strlen($d) === 10) {
            $d = '1'.$d;
        } elseif (! (strlen($d) === 11 && str_starts_with($d, '1'))) {
            return null; // otro formato no se adivina: sin enlace
        }

        // Igual que quote() de Python: la «/» (fechas 04/11/2026) se deja sin codificar.
        return 'https://wa.me/'.$d.'?text='.str_replace('%2F', '/', rawurlencode($message));
    }

    private function money(float $v): string
    {
        return 'RD$ '.number_format($v, 2);
    }

    public function followups()
    {
        $company = (string) (CompanyProfile::first()?->name ?? '');
        $tz = 'America/Santo_Domingo';
        $today = Carbon::now($tz)->startOfDay();
        $dueDays = (int) config('app.invoice_due_days', 7);
        $staleDays = (int) config('app.quote_stale_days', 7);

        $recv = [];
        foreach (Invoice::with('project.client')->whereNull('voided_at')->whereNull('paid_at')->where('total', '>', 0)->get() as $inv) {
            $c = $inv->project->client;
            $issued = Carbon::parse($inv->created_at)->setTimezone($tz)->startOfDay();
            $due = $issued->copy()->addDays($dueDays);
            $late = (int) $due->diffInDays($today, false);
            $total = (float) $inv->total;
            $ref = $inv->code.($inv->ncf ? " (NCF {$inv->ncf})" : '');
            $body = $late > 0
                ? "le escribimos de $company sobre la factura $ref por ".$this->money($total).", que venció el {$due->format('d/m/Y')} ($late día".($late !== 1 ? 's' : '').' de atraso). ¿Nos puede confirmar la fecha en que podrá realizar el pago?'
                : "le escribimos de $company para recordarle la factura $ref por ".$this->money($total).", con vencimiento el {$due->format('d/m/Y')}. Quedamos atentos a su pago.";
            $msg = "Buen día, {$c->name}. $body Gracias por su confianza.";
            $recv[] = [
                'invoice_id' => $inv->id, 'project_id' => $inv->project_id, 'code' => $inv->code, 'ncf' => $inv->ncf,
                'client_name' => $c->name, 'client_phone' => $c->phone, 'total' => $total, 'issued_on' => $issued->format('Y-m-d'),
                'due_on' => $due->format('Y-m-d'), 'days_overdue' => $late, 'overdue' => $late > 0, 'message' => $msg,
                'whatsapp_url' => $this->wa($c->phone, $msg),
            ];
        }
        usort($recv, fn ($a, $b) => [$b['days_overdue'], $a['code']] <=> [$a['days_overdue'], $b['code']]);

        $waiting = [];
        foreach (Quote::with('project.client')->where('status', 'pendiente')->get() as $q) {
            $sent = Carbon::parse($q->created_at)->setTimezone($tz)->startOfDay();
            $days = (int) $sent->diffInDays($today);
            if ($days < 3) { // una cotización recién enviada no se persigue
                continue;
            }
            $c = $q->project->client;
            $total = (float) $q->total;
            $msg = "Buen día, {$c->name}. Le escribimos de $company para dar seguimiento a la cotización {$q->code} por ".$this->money($total)
                ." que le enviamos el {$sent->format('d/m/Y')}. ¿Pudo revisarla? Con gusto resolvemos cualquier duda o la ajustamos a lo que necesite.";
            $waiting[] = [
                'quote_id' => $q->id, 'project_id' => $q->project_id, 'code' => $q->code, 'client_name' => $c->name,
                'client_phone' => $c->phone, 'total' => $total, 'sent_on' => $sent->format('Y-m-d'), 'days_waiting' => $days,
                'stale' => $days >= $staleDays, 'message' => $msg, 'whatsapp_url' => $this->wa($c->phone, $msg),
            ];
        }
        usort($waiting, fn ($a, $b) => [$b['days_waiting'], $a['code']] <=> [$a['days_waiting'], $b['code']]);

        $overdue = array_filter($recv, fn ($r) => $r['overdue']);

        return [
            'receivables_total' => Money::fromCents(array_sum(array_map(fn ($r) => Money::cents($r['total']), $recv))),
            'overdue_total' => Money::fromCents(array_sum(array_map(fn ($r) => Money::cents($r['total']), $overdue))),
            'overdue_count' => count($overdue), 'receivables' => $recv, 'quotes' => $waiting,
        ];
    }

    // ---- búsqueda global -----------------------------------------------------------------

    public function search(Request $r)
    {
        $q = trim((string) $r->query('q', ''));
        if (mb_strlen($q) < 2) {
            return ['clients' => [], 'projects' => [], 'tickets' => []];
        }
        $user = $r->attributes->get('user');
        $like = '%'.str_replace(['\\', '%', '_'], ['\\\\', '\\%', '\\_'], $q).'%';

        $clients = Access::clientScope(Client::query(), $user)
            ->where(fn ($w) => $w->where('name', 'like', $like)->orWhere('company', 'like', $like)->orWhere('rnc', 'like', $like))
            ->orderBy('name')->limit(8)->get();
        $projects = Access::projectScope(Project::with('client'), $user)
            ->where(fn ($w) => $w->where('projects.code', 'like', $like)->orWhere('projects.description', 'like', $like)
                ->orWhereHas('client', fn ($c) => $c->where('name', 'like', $like)))
            ->orderByDesc('projects.created_at')->limit(8)->get();
        $tickets = Ticket::with('project')->where(fn ($w) => $w->where('code', 'like', $like)->orWhere('problem', 'like', $like));
        if (Access::restricted($user)) {
            $tickets->where(fn ($w) => $w->where('technician_id', $user->id)
                ->orWhereIn('project_id', Access::projectScope(Project::query(), $user)->select('projects.id')));
        }
        $tickets = $tickets->orderByDesc('created_at')->limit(8)->get();

        return [
            'clients' => $clients->map(fn ($c) => ['id' => $c->id, 'name' => $c->name, 'company' => $c->company])->values(),
            'projects' => $projects->map(fn ($p) => ['id' => $p->id, 'code' => $p->code, 'client_name' => $p->client->name, 'status' => $p->status])->values(),
            'tickets' => $tickets->map(fn ($t) => [
                'id' => $t->id, 'code' => $t->code, 'problem' => $t->problem, 'project_id' => $t->project_id, 'project_code' => $t->project->code,
            ])->values(),
        ];
    }
}
