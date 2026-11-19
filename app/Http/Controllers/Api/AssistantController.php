<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Client;
use App\Models\Project;
use App\Models\Quote;
use App\Models\Ticket;
use App\Models\Visit;
use App\Support\Access;
use App\Support\ApiException;
use App\Support\Conversation;
use App\Support\Gemini;
use Illuminate\Http\Request;
use Illuminate\Support\Carbon;

/** Asistente del Inicio: resumen del día (sin IA, instantáneo) y turnos de conversación escritos o hablados. */
class AssistantController extends Controller
{
    private const LIMIT = 5; // es un resumen para decidir qué hacer ahora, no un listado completo
    private const TZ = 'America/Santo_Domingo';
    private const UNKNOWN = 'No te entendí bien. Puedes decirme, por ejemplo: «un levantamiento de cámaras para Juan Pérez», «continuar con Ferretería López» o «qué tengo hoy».';
    private const UNHEARD = 'No te escuché bien. ¿Me lo repites?';

    private function mine($user)
    {
        return fn ($q) => Access::projectScope($q, $user);
    }

    /** Resumen del día: visitas de hoy, levantamientos listos para cotizar, cotizaciones esperando, tickets abiertos y proyectos para continuar. */
    private function buildToday($user): array
    {
        $today = Carbon::now(self::TZ)->startOfDay();
        $tech = $user->role === 'tecnico';

        $vq = Visit::with('project.client')->whereDate('scheduled_date', $today->toDateString())->where('status', 'programada');
        if ($tech) {
            $vq->where('technician_id', $user->id);
        }
        $visits = $vq->orderByRaw('scheduled_time IS NULL')->orderBy('scheduled_time')->limit(self::LIMIT)->get()->map(fn ($v) => [
            'id' => $v->id, 'project_id' => $v->project_id, 'project_code' => $v->project->code, 'client_name' => $v->project->client->name,
            'scheduled_time' => $v->scheduled_time, 'address' => $v->project->placeAddress(), 'location_url' => $v->project->placeLocationUrl(),
            'phone' => $v->project->client->phone, 'notes' => $v->notes,
        ])->all();

        // Levantamiento con notas y sin ninguna cotización todavía: lo siguiente es cotizarlo.
        $ready = Access::projectScope(Project::with('client'), $user)->where('projects.status', 'levantamiento')
            ->whereIn('projects.id', \App\Models\Survey::whereRaw("length(trim(coalesce(notes, ''))) > 0")->select('project_id'))
            ->whereDoesntHave('quotes')->orderByDesc('projects.created_at')->limit(self::LIMIT)->get()->map(fn ($p) => [
                'project_id' => $p->id, 'project_code' => $p->code, 'client_name' => $p->client->name, 'survey_type' => $p->survey_type,
            ])->all();

        $waiting = Quote::with('project.client')->where('status', 'pendiente')
            ->whereIn('project_id', Access::projectScope(Project::query(), $user)->select('projects.id'))
            ->orderBy('created_at')->limit(self::LIMIT)->get()->map(fn ($q) => [
                'quote_id' => $q->id, 'code' => $q->code, 'project_id' => $q->project_id, 'client_name' => $q->project->client->name,
                'total' => (float) $q->total, 'days_pending' => max(0, (int) $today->diffInDays($q->created_at->copy()->setTimezone(self::TZ)->startOfDay(), false) * -1),
            ])->all();

        // El técnico ve los que tiene asignados; admin y oficina, todos los abiertos del negocio.
        $tq = Ticket::with('project.client')->whereIn('status', Ticket::OPEN);
        if ($tech) {
            $tq->where('technician_id', $user->id);
        }
        $tickets = $tq->orderBy('created_at')->limit(self::LIMIT)->get()->map(fn ($t) => [
            'id' => $t->id, 'code' => $t->code, 'project_id' => $t->project_id, 'client_name' => $t->project->client->name, 'problem' => $t->problem, 'status' => $t->status,
        ])->all();

        $recent = Access::projectScope(Project::with('client'), $user)->where('projects.status', '!=', 'cerrado')
            ->orderByRaw('coalesce(projects.updated_at, projects.created_at) desc')->limit(3)->get()->map(fn ($p) => [
                'project_id' => $p->id, 'project_code' => $p->code, 'client_name' => $p->client->name, 'survey_type' => $p->survey_type, 'status' => $p->status,
            ])->all();

        return ['today' => $today->toDateString(), 'visits' => $visits, 'ready_to_quote' => $ready, 'quotes_waiting' => $waiting,
            'tickets' => $tickets, 'continue_projects' => $recent];
    }

    public function today(Request $r)
    {
        return $this->buildToday($r->attributes->get('user'));
    }

    private function count(int $n, string $one, string $many): string
    {
        return $n.' '.($n === 1 ? $one : $many);
    }

    private function agendaSentence(array $t): string
    {
        $parts = [];
        if ($t['visits']) {
            $parts[] = $this->count(count($t['visits']), 'visita', 'visitas');
        }
        if ($t['ready_to_quote']) {
            $parts[] = $this->count(count($t['ready_to_quote']), 'levantamiento listo para cotizar', 'levantamientos listos para cotizar');
        }
        if ($t['quotes_waiting']) {
            $parts[] = $this->count(count($t['quotes_waiting']), 'cotización esperando respuesta', 'cotizaciones esperando respuesta');
        }
        if ($t['tickets']) {
            $parts[] = $this->count(count($t['tickets']), 'ticket abierto', 'tickets abiertos');
        }
        if (! $parts) {
            return 'Hoy no tienes visitas ni pendientes urgentes.';
        }
        if (count($parts) === 1) {
            return "Hoy tienes {$parts[0]}.";
        }
        $last = array_pop($parts);

        return 'Hoy tienes '.implode(', ', $parts)." y $last.";
    }

    /** Un turno de la conversación: devuelve qué responderle y a dónde llevarlo. No crea ni modifica nada. */
    private function respond($user, string $text, array $types): array
    {
        $projects = Access::projectScope(Project::with('client'), $user)->where('projects.status', '!=', 'cerrado')
            ->orderByRaw('coalesce(projects.updated_at, projects.created_at) desc')->limit(300)->get()
            ->map(fn ($p) => ['project_id' => $p->id, 'project_code' => $p->code, 'client_name' => $p->client->name])->all();

        $u = Conversation::understand($text, $types, $projects);
        $intent = $u['intent'];
        $out = ['intent' => $intent ?: 'unknown', 'reply' => self::UNKNOWN, 'navigate_to' => null, 'client_name' => $u['client_name'], 'client_id' => null,
            'phone' => $u['phone'], 'survey_type' => $u['survey_type'], 'ai_used' => $u['ai_used'], 'heard' => ''];

        if ($intent === 'new_survey') {
            $name = $u['client_name'];
            $kind = $u['survey_type'] ? " de {$u['survey_type']}" : '';
            $existing = null;
            if ($name !== '') {
                // técnico: solo clientes suyos
                $existing = Access::clientScope(Client::query(), $user)->whereRaw('lower(clients.name) = ?', [mb_strtolower($name)])->first();
            }
            if ($existing) {
                $out['client_id'] = $existing->id;
                $out['client_name'] = $existing->name;
                $out['reply'] = "Perfecto. Vamos con el levantamiento$kind para {$existing->name}, que ya es cliente.";
            } elseif ($name !== '') {
                $out['reply'] = "Perfecto. Vamos con el levantamiento$kind para $name. Te pido lo que falta.";
            } else {
                $out['reply'] = "Perfecto, empecemos un levantamiento$kind. Dime el nombre del cliente y su teléfono.";
            }
            $out['navigate_to'] = '/nuevo';
        } elseif ($intent === 'open_project') {
            $p = $u['project'];
            if (! $p) {
                $out['intent'] = 'ask_project';
                $out['reply'] = 'No encontré un proyecto abierto con ese nombre. ¿De qué cliente es?';
            } else {
                $out['client_name'] = $p['client_name'];
                $out['reply'] = "Abro el proyecto de {$p['client_name']}, {$p['project_code']}.";
                $out['navigate_to'] = "/proyectos/{$p['project_id']}";
            }
        } elseif ($intent === 'agenda') {
            $t = $this->buildToday($user);
            $s = $this->agendaSentence($t);
            if ($t['visits']) {
                $f = $t['visits'][0];
                $s .= " La primera visita es con {$f['client_name']}".($f['scheduled_time'] ? ' a las '.substr((string) $f['scheduled_time'], 0, 5) : '').'.';
            }
            $work = $t['visits'] || $t['ready_to_quote'] || $t['quotes_waiting'] || $t['tickets'];
            $out['reply'] = $s.($work ? ' ¿Con cuál empezamos?' : ' ¿Qué quieres hacer?');
        } elseif ($intent === 'quotes') {
            $out['reply'] = 'Te muestro las cotizaciones.';
            $out['navigate_to'] = '/cotizaciones';
        } elseif ($intent === 'tickets') {
            $tk = $this->buildToday($user)['tickets'];
            if (! $tk) {
                $out['reply'] = 'No tienes tickets abiertos ahora mismo.';
            } elseif (count($tk) === 1) {
                $out['reply'] = "Tienes un ticket abierto, de {$tk[0]['client_name']}: {$tk[0]['problem']}. Lo abro.";
                $out['navigate_to'] = "/proyectos/{$tk[0]['project_id']}?tab=tickets";
            } else {
                $names = implode(', ', array_map(fn ($x) => $x['client_name'], array_slice($tk, 0, 3)));
                $out['reply'] = 'Tienes '.count($tk)." tickets abiertos: $names. Tócalos en la lista de abajo para abrirlos.";
            }
        } elseif ($intent === 'none') {
            $out['reply'] = 'De acuerdo. Aquí estoy cuando me necesites.';
        }

        return $out;
    }

    private function types($raw): array
    {
        if (is_string($raw)) {
            $raw = json_decode($raw, true);
        }

        return is_array($raw) ? array_slice(array_map('strval', array_filter($raw, 'is_scalar')), 0, 30) : [];
    }

    public function talk(Request $r)
    {
        $text = $r->input('text');
        if (! is_string($text) || mb_strlen($text) > 600) {
            throw new ApiException(422, 'text es obligatorio (máximo 600 caracteres)');
        }

        return $this->respond($r->attributes->get('user'), $text, $this->types($r->input('survey_types', [])));
    }

    /** Un turno HABLADO: recibe el audio grabado en el teléfono, lo transcribe y responde igual que /talk. */
    public function listen(Request $r)
    {
        $file = $r->file('audio');
        if (! $file || ! $file->isValid()) {
            throw new ApiException(422, 'Falta el audio');
        }
        $mime = strtolower(explode(';', (string) $file->getClientMimeType())[0]);
        if (! str_starts_with($mime, 'audio/') && ! in_array($mime, ['video/mp4', 'video/webm', 'application/octet-stream'], true)) {
            throw new ApiException(400, 'Tipo de archivo no permitido: '.$file->getClientMimeType());
        }
        if ($file->getSize() > 25 * 1024 * 1024) {
            throw new ApiException(413, 'El audio pesa más de 25 MB');
        }
        try {
            $heard = Gemini::transcribe($file->getRealPath(), Conversation::PROMPT_VOICE);
        } catch (ApiException $e) {
            throw $e->status === 503 ? $e : new ApiException(400, 'No se pudo transcribir el audio. '.$e->getMessage());
        }
        if (trim($heard) === '') {
            return ['intent' => 'unheard', 'reply' => self::UNHEARD, 'heard' => ''];
        }

        return ['heard' => $heard] + $this->respond($r->attributes->get('user'), $heard, $this->types($r->input('survey_types', '[]')));
    }
}
