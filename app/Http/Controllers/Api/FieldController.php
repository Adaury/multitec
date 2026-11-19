<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Engineering;
use App\Models\Extension;
use App\Models\LogEntry;
use App\Models\LogEntryAsset;
use App\Models\Project;
use App\Models\ProjectStage;
use App\Models\Quote;
use App\Support\ApiException;
use App\Support\Codes;
use App\Support\Ncf;
use App\Support\V;
use Illuminate\Http\Request;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

/** Ingeniería, ejecución por etapas, bitácora y ampliaciones de un proyecto. */
class FieldController extends Controller
{
    private const ENG_FIELDS = ['recommended_equipment', 'distribution', 'conduits', 'wiring', 'technical_design', 'observations'];
    private const PHOTO_EXT = ['image/jpeg' => 'jpg', 'image/png' => 'png', 'image/heic' => 'heic', 'image/webp' => 'webp'];

    private function validDate($v, string $field): ?string
    {
        if ($v === null || $v === '') {
            return null;
        }
        if (! is_string($v) || ! preg_match('/^\d{4}-\d{2}-\d{2}$/', $v) || ! strtotime($v)) {
            throw new ApiException(422, "$field inválida (usa AAAA-MM-DD)");
        }

        return $v;
    }

    // ---- ingeniería ------------------------------------------------------------------------

    private function engOut(Engineering $e): array
    {
        $out = ['id' => $e->id, 'project_id' => $e->project_id];
        foreach (self::ENG_FIELDS as $f) {
            $out[$f] = $e->$f;
        }

        return $out + ['ai_generated' => (bool) $e->ai_generated, 'created_by' => $e->created_by, 'created_at' => $e->created_at, 'updated_at' => $e->updated_at];
    }

    public function engineering(int $project_id)
    {
        $e = Engineering::where('project_id', $project_id)->first();
        if (! $e) {
            throw new ApiException(404, 'Ingeniería no encontrada');
        }

        return $this->engOut($e);
    }

    public function updateEngineering(Request $r, int $project_id)
    {
        $e = Engineering::where('project_id', $project_id)->first();
        if (! $e) {
            // Proyecto sin ingeniería todavía: guardar la crea, en vez de perder lo escrito a mano.
            if (! Project::whereKey($project_id)->exists()) {
                throw new ApiException(404, 'Proyecto no encontrado');
            }
            $e = Engineering::create(['project_id' => $project_id, 'created_by' => $r->attributes->get('user')->id, 'created_at' => now()]);
        }
        $data = [];
        foreach (self::ENG_FIELDS as $f) {
            if ($r->has($f)) {
                $data[$f] = V::text($r->input($f), 10000, $f);
            }
        }
        $e->update($data + ['updated_at' => now()]);

        return $this->engOut($e->fresh());
    }

    // ---- ejecución por etapas -----------------------------------------------------------------

    private function stages(int $projectId)
    {
        $s = ProjectStage::where('project_id', $projectId)->orderBy('order')->get();
        if ($s->isEmpty()) {
            throw new ApiException(404, 'El proyecto no tiene etapas de ejecución');
        }

        return $s;
    }

    private function execOut($stages): array
    {
        $done = $stages->where('completed', true)->count();

        return [
            'stages' => $stages->map(fn ($s) => [
                'id' => $s->id, 'name' => $s->name, 'order' => $s->order, 'completed' => (bool) $s->completed, 'completed_at' => $s->completed_at,
            ])->values(),
            'progress_percent' => $stages->count() ? round($done / $stages->count() * 100, 2) : 0.0,
        ];
    }

    public function execution(int $project_id)
    {
        return $this->execOut($this->stages($project_id));
    }

    /** Completa la siguiente etapa pendiente (orden fijo y secuencial). */
    public function advance(int $project_id)
    {
        $stages = $this->stages($project_id);
        $next = $stages->firstWhere('completed', false);
        if (! $next) {
            throw new ApiException(400, 'Todas las etapas ya están completas');
        }
        $next->update(['completed' => true, 'completed_at' => Carbon::now()]);

        return $this->execOut($this->stages($project_id));
    }

    /** Deshace la última etapa completada. */
    public function undo(int $project_id)
    {
        $stages = $this->stages($project_id);
        $last = $stages->where('completed', true)->sortByDesc('order')->first();
        if (! $last) {
            throw new ApiException(400, 'No hay etapas completadas para deshacer');
        }
        $last->update(['completed' => false, 'completed_at' => null]);

        return $this->execOut($this->stages($project_id));
    }

    // ---- bitácora ------------------------------------------------------------------------------

    public function logbook(int $project_id)
    {
        return LogEntry::with('assets')->where('project_id', $project_id)->orderByDesc('entry_date')->orderByDesc('created_at')->orderByDesc('id')
            ->get()->map(fn ($e) => $e->toOut())->values();
    }

    public function createLogEntry(Request $r, int $project_id)
    {
        if (! Project::whereKey($project_id)->exists()) {
            throw new ApiException(404, 'Proyecto no encontrado');
        }
        $e = LogEntry::create([
            'project_id' => $project_id, 'comment' => V::text($r->input('comment'), 5000, 'comment', true),
            'entry_date' => $this->validDate($r->input('entry_date'), 'La fecha') ?? Ncf::today(),
            'responsible_id' => $r->attributes->get('user')->id, 'created_at' => now(),
        ]);

        return response()->json($e->fresh('assets')->toOut(), 201);
    }

    public function uploadLogPhoto(Request $r, int $entry_id)
    {
        $entry = LogEntry::find($entry_id);
        if (! $entry) {
            throw new ApiException(404, 'Entrada de bitácora no encontrada');
        }
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
        $path = $file->getRealPath();
        $ok = $type === 'image/heic'
            ? substr((string) file_get_contents($path, false, null, 4, 4), 0, 4) === 'ftyp'
            : (($info = @getimagesize($path)) && ($info['mime'] ?? '') === $type);
        if (! $ok) {
            throw new ApiException(400, 'El contenido del archivo no corresponde al tipo declarado');
        }
        $stored = $file->storeAs('uploads/c'.app('company_id').'/logbook/'.$entry->id, Str::uuid().'.'.self::PHOTO_EXT[$type], 'local');
        $desc = $r->input('description');
        $a = LogEntryAsset::create([
            'log_entry_id' => $entry->id, 'file_path' => $stored, 'description' => $desc !== null ? mb_substr((string) $desc, 0, 255) : null,
            'created_at' => now(),
        ]);

        return response()->json(['id' => $a->id, 'file_path' => $a->file_path, 'description' => $a->description, 'created_at' => $a->created_at], 201);
    }

    // ---- ampliaciones ------------------------------------------------------------------------------

    public function extensions(int $project_id)
    {
        return Extension::where('project_id', $project_id)->orderByDesc('created_at')->orderByDesc('id')->get()->map(fn ($e) => $e->toOut())->values();
    }

    public function createExtension(Request $r, int $project_id)
    {
        if (! Project::whereKey($project_id)->exists()) {
            throw new ApiException(404, 'Proyecto no encontrado');
        }
        $quoteId = V::int($r->input('quote_id'), 'quote_id');
        if ($quoteId !== null) {
            $q = Quote::find($quoteId);
            if (! $q || $q->project_id !== $project_id) {
                throw new ApiException(400, 'La cotización debe pertenecer al mismo proyecto');
            }
        }
        $title = V::text($r->input('title'), 255, 'title', true);
        $desc = V::text($r->input('description'), 5000, 'description');
        $date = $this->validDate($r->input('date'), 'La fecha') ?? Ncf::today();
        $ext = DB::transaction(fn () => Extension::create([
            'code' => Codes::next('AMP'), 'project_id' => $project_id, 'quote_id' => $quoteId, 'title' => $title,
            'description' => $desc, 'date' => $date, 'created_by' => $r->attributes->get('user')->id, 'created_at' => now(),
        ]));

        return response()->json($ext->fresh()->toOut(), 201);
    }

    public function extensionStatus(Request $r, int $extension_id)
    {
        $status = $r->input('status');
        if (! in_array($status, Extension::STATUSES, true)) {
            throw new ApiException(400, 'Estado inválido: '.(is_scalar($status) ? $status : ''));
        }
        $e = Extension::find($extension_id);
        if (! $e) {
            throw new ApiException(404, 'Ampliación no encontrada');
        }
        $e->update(['status' => $status, 'updated_at' => now()]);

        return $e->fresh()->toOut();
    }
}
