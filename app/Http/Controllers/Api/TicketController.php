<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Project;
use App\Models\Ticket;
use App\Models\TicketAsset;
use App\Models\TicketHistory;
use App\Models\User;
use App\Support\Access;
use App\Support\ApiException;
use App\Support\Codes;
use App\Support\Notify;
use App\Support\V;
use Illuminate\Http\Request;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

class TicketController extends Controller
{
    private const PHOTO_EXT = ['image/jpeg' => 'jpg', 'image/png' => 'png', 'image/heic' => 'heic', 'image/webp' => 'webp'];

    private function find(int $id): Ticket
    {
        $t = Ticket::with('assets')->find($id);
        if (! $t) {
            throw new ApiException(404, 'Ticket no encontrado');
        }

        return $t;
    }

    private function checkTechnician(?int $id): void
    {
        if ($id !== null && ! User::where('company_id', app('company_id'))->whereKey($id)->exists()) {
            throw new ApiException(404, 'Técnico no encontrado');
        }
    }

    /** Todos los tickets de la empresa (por defecto solo abiertos o en proceso), con proyecto, cliente y técnico. */
    public function index(Request $r)
    {
        $user = $r->attributes->get('user');
        $q = Ticket::with('assets', 'project.client', 'technician');
        if (filter_var($r->query('open_only', true), FILTER_VALIDATE_BOOLEAN)) {
            $q->whereIn('status', Ticket::OPEN);
        }
        if (Access::restricted($user)) { // técnico: los suyos y los de sus proyectos
            $q->where(fn ($w) => $w->where('technician_id', $user->id)
                ->orWhereIn('project_id', Access::projectScope(Project::query(), $user)->select('projects.id')));
        }

        return $q->orderByDesc('created_at')->orderByDesc('id')->limit(500)->get()->map(fn ($t) => $t->toOut() + [
            'project_code' => $t->project->code, 'client_name' => $t->project->client->name,
            'technician_name' => $t->technician?->name,
        ])->values();
    }

    public function indexByProject(int $project_id)
    {
        return Ticket::with('assets')->where('project_id', $project_id)->orderByDesc('created_at')->orderByDesc('id')
            ->get()->map(fn ($t) => $t->toOut())->values();
    }

    public function store(Request $r, int $project_id)
    {
        if (! Project::whereKey($project_id)->exists()) {
            throw new ApiException(404, 'Proyecto no encontrado');
        }
        $problem = V::text($r->input('problem'), 5000, 'problem', true);
        $tech = V::int($r->input('technician_id'), 'technician_id');
        $this->checkTechnician($tech);
        $ticket = DB::transaction(function () use ($project_id, $problem, $tech, $r) {
            $t = Ticket::create([
                'code' => Codes::next('TKT'), 'project_id' => $project_id, 'problem' => $problem, 'technician_id' => $tech,
                'status' => 'abierto', 'created_by' => $r->attributes->get('user')->id, 'created_at' => now(),
            ]);
            TicketHistory::add($t->id, 'abierto');

            return $t;
        });
        Notify::ticketAssigned($ticket);

        return response()->json($this->find($ticket->id)->toOut(), 201);
    }

    public function update(Request $r, int $ticket_id)
    {
        $t = $this->find($ticket_id);
        $previousTech = $t->technician_id;
        $data = [];
        if ($r->has('technician_id')) {
            $tech = V::int($r->input('technician_id'), 'technician_id');
            $this->checkTechnician($tech);
            $data['technician_id'] = $tech;
        }
        if ($r->has('solution')) {
            $data['solution'] = V::text($r->input('solution'), 5000, 'solution');
        }
        DB::transaction(function () use ($r, $t, $data) {
            if ($r->has('status') && $r->input('status') !== null) {
                $status = $r->input('status');
                if (! in_array($status, Ticket::STATUSES, true)) {
                    throw new ApiException(400, 'Estado inválido: '.(is_scalar($status) ? $status : ''));
                }
                if ($status !== $t->status) {
                    TicketHistory::add($t->id, $status);
                    $data['resolved_at'] = in_array($status, ['resuelto', 'cerrado'], true) ? Carbon::now() : null;
                }
                $data['status'] = $status;
            }
            $t->update($data + ['updated_at' => now()]);
        });
        $t = $this->find($ticket_id);
        if ($t->technician_id !== null && $t->technician_id !== $previousTech) {
            Notify::ticketAssigned($t);
        }

        return $t->toOut();
    }

    public function history(int $ticket_id)
    {
        $this->find($ticket_id);

        return TicketHistory::where('ticket_id', $ticket_id)->orderBy('created_at')->orderBy('id')->get()->map(fn ($h) => $h->toOut())->values();
    }

    public function uploadPhoto(Request $r, int $ticket_id)
    {
        $t = $this->find($ticket_id);
        $file = $r->file('file');
        if (! $file || ! $file->isValid()) {
            throw new ApiException(400, 'Falta el archivo');
        }
        $type = strtolower(trim(explode(';', (string) $file->getClientMimeType())[0]));
        if (! isset(self::PHOTO_EXT[$type])) {
            throw new ApiException(400, 'Tipo de archivo no permitido: '.$file->getClientMimeType());
        }
        if ($file->getSize() > 25 * 1024 * 1024) {
            throw new ApiException(413, 'El archivo supera el límite de 25 MB');
        }
        // El contenido real debe coincidir con el tipo declarado.
        $path = $file->getRealPath();
        $ok = $type === 'image/heic'
            ? substr((string) file_get_contents($path, false, null, 4, 4), 0, 4) === 'ftyp'
            : (($info = @getimagesize($path)) && ($info['mime'] ?? '') === $type);
        if (! $ok) {
            throw new ApiException(400, 'El contenido del archivo no corresponde al tipo declarado');
        }
        $stored = $file->storeAs('uploads/c'.app('company_id').'/tickets/'.$t->id, Str::uuid().'.'.self::PHOTO_EXT[$type], 'local');
        $desc = $r->input('description');
        $asset = TicketAsset::create([
            'ticket_id' => $t->id, 'file_path' => $stored, 'description' => $desc !== null ? mb_substr((string) $desc, 0, 255) : null,
            'created_at' => now(),
        ]);

        return response()->json([
            'id' => $asset->id, 'file_path' => $asset->file_path, 'description' => $asset->description, 'created_at' => $asset->created_at,
        ], 201);
    }

    public function deletePhoto(int $ticket_id, int $asset_id)
    {
        $t = $this->find($ticket_id);
        $asset = $t->assets->firstWhere('id', $asset_id);
        if (! $asset) {
            throw new ApiException(404, 'Archivo no encontrado');
        }
        $path = $asset->file_path;
        $asset->delete();
        if (\App\Support\Uploads::owns($path)) {
            Storage::disk('local')->delete($path);
        }

        return response()->noContent();
    }
}
