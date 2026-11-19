<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Project;
use App\Models\Quote;
use App\Models\QuoteComparison;
use App\Support\ApiException;
use App\Support\Audit;
use App\Support\QuoteCompare;
use App\Support\Uploads;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

/** Subir una cotización ajena (competidor o proveedor) y compararla con el levantamiento y con la cotización propia. Solo admin y oficina: son precios. */
class ComparisonController extends Controller
{
    private const TYPES = ['application/pdf' => 'pdf', 'image/jpeg' => 'jpg', 'image/png' => 'png', 'image/webp' => 'webp'];
    private const MAX_BYTES = 25 * 1024 * 1024;

    private function project(int $id): Project
    {
        return Project::find($id) ?? throw new ApiException(404, 'Proyecto no encontrado');
    }

    private function row(int $projectId, int $id): QuoteComparison
    {
        return QuoteComparison::where('id', $id)->where('project_id', $projectId)->first() ?? throw new ApiException(404, 'Comparación no encontrada');
    }

    /** La cotización indicada o, si no hay, la más reciente del proyecto que no esté rechazada. */
    private function ourQuote(int $projectId, ?int $quoteId): ?Quote
    {
        $q = Quote::with('items')->where('project_id', $projectId);
        if ($quoteId !== null) {
            return $q->where('id', $quoteId)->first();
        }

        return $q->where('status', '!=', 'no_aprobada')->orderByDesc('created_at')->orderByDesc('id')->first();
    }

    private function out(QuoteComparison $r): array
    {
        $items = $r->items ?? [];
        $result = QuoteCompare::compare($r->project_id, $items, $r->total, $this->ourQuote($r->project_id, $r->quote_id));

        return [
            'id' => $r->id, 'project_id' => $r->project_id, 'label' => $r->label, 'filename' => $r->filename, 'file_path' => $r->file_path,
            'quote_id' => $r->quote_id, 'created_at' => $r->created_at, 'items' => $items, 'total' => $r->total,
        ] + $result;
    }

    public function index(int $project_id)
    {
        $this->project($project_id);

        return QuoteComparison::where('project_id', $project_id)->orderByDesc('id')->get()->map(fn ($r) => [
            'id' => $r->id, 'label' => $r->label, 'filename' => $r->filename, 'quote_id' => $r->quote_id, 'created_at' => $r->created_at, 'lines' => count($r->items ?? []),
        ])->values();
    }

    public function store(Request $r, int $project_id)
    {
        $user = $r->attributes->get('user');
        $this->project($project_id);
        $label = trim((string) $r->input('label', ''));
        if ($label === '' || mb_strlen($label) > 120) {
            throw new ApiException(422, 'La etiqueta es obligatoria (máximo 120 caracteres)');
        }
        $quoteId = $r->filled('quote_id') ? (int) $r->input('quote_id') : null;
        if ($quoteId !== null && ! $this->ourQuote($project_id, $quoteId)) {
            throw new ApiException(404, 'Cotización propia no encontrada en este proyecto');
        }
        $text = $r->input('text');
        if ($text !== null && (! is_string($text) || mb_strlen($text) > 20000)) {
            throw new ApiException(422, 'El texto es demasiado largo (máximo 20000 caracteres)');
        }
        $file = $r->file('file');
        if (! $file && trim((string) $text) === '') {
            throw new ApiException(400, 'Sube un PDF o una foto, o pega el texto de la cotización');
        }

        $contents = null;
        $type = '';
        if ($file) {
            $type = strtolower(trim(explode(';', (string) $file->getClientMimeType())[0]));
            if (! isset(self::TYPES[$type]) || ! $file->isValid()) {
                throw new ApiException(400, 'Sube un PDF o una foto (JPG, PNG o WebP)');
            }
            if ($file->getSize() > self::MAX_BYTES) {
                throw new ApiException(413, 'El archivo supera el límite de 25 MB');
            }
            $contents = (string) file_get_contents($file->getRealPath());
            // No se confía en el tipo que declara el cliente: se mira el contenido.
            $real = str_starts_with($contents, '%PDF') ? 'application/pdf' : (@getimagesizefromstring($contents)['mime'] ?? '');
            if ($real !== $type) {
                throw new ApiException(400, 'El contenido del archivo no corresponde al tipo declarado');
            }
            $source = QuoteCompare::extractText($contents);
        } else {
            $source = trim((string) $text);
        }

        $extracted = QuoteCompare::readItems($source);
        if (! $extracted['items']) {
            throw new ApiException(400, 'No encontré líneas de productos en ese documento. Prueba con otro archivo o pega el texto.');
        }

        // El archivo se guarda solo cuando todo lo anterior salió bien: una lectura fallida no deja archivos huérfanos.
        $path = $filename = null;
        if ($file) {
            $path = $file->storeAs('uploads/c'.app('company_id').'/comparisons/'.$project_id, Str::uuid()->toString().'.'.self::TYPES[$type], 'local');
            $filename = mb_substr((string) $file->getClientOriginalName(), 0, 255) ?: null;
        }
        $row = QuoteComparison::create([
            'project_id' => $project_id, 'quote_id' => $quoteId, 'label' => $label, 'filename' => $filename, 'file_path' => $path,
            'source_text' => $source, 'items' => $extracted['items'], 'total' => $extracted['total'], 'created_by' => $user->id, 'created_at' => now(),
        ]);
        Audit::log('comparison_created', $user, entity: 'project', entityId: $project_id, detail: ['etiqueta' => $label], request: $r);

        return response()->json($this->out($row), 201);
    }

    public function show(int $project_id, int $comparison_id)
    {
        return $this->out($this->row($project_id, $comparison_id));
    }

    /** Oficina corrige lo que la IA leyó (o cambia contra qué cotización se compara). */
    public function update(Request $r, int $project_id, int $comparison_id)
    {
        $row = $this->row($project_id, $comparison_id);
        if ($r->has('label')) {
            $label = trim((string) $r->input('label'));
            if ($label === '' || mb_strlen($label) > 120) {
                throw new ApiException(422, 'La etiqueta no puede estar vacía (máximo 120 caracteres)');
            }
            $row->label = $label;
        }
        if ($r->has('quote_id')) {
            $qid = $r->input('quote_id');
            if ($qid !== null && ! $this->ourQuote($project_id, (int) $qid)) {
                throw new ApiException(404, 'Cotización propia no encontrada en este proyecto');
            }
            $row->quote_id = $qid !== null ? (int) $qid : null;
        }
        if ($r->has('items') && $r->input('items') !== null) {
            $items = $r->input('items');
            if (! is_array($items) || count($items) > 200) {
                throw new ApiException(422, 'items debe ser una lista de máximo 200 líneas');
            }
            foreach ($items as $i => $it) {
                $q = is_array($it) ? ($it['quantity'] ?? null) : null;
                $p = is_array($it) ? ($it['unit_price'] ?? null) : null;
                $d = is_array($it) ? trim((string) ($it['description'] ?? '')) : '';
                if ($d === '' || mb_strlen($d) > 300 || ! is_numeric($q) || $q <= 0 || ! is_numeric($p) || $p < 0) {
                    throw new ApiException(422, 'Línea '.($i + 1).': descripción (1-300), cantidad mayor que 0 y precio no negativo');
                }
            }
            $row->items = QuoteCompare::cleanItems($items);
        }
        if ($r->has('total')) {
            $t = $r->input('total');
            if ($t !== null && (! is_numeric($t) || $t < 0)) {
                throw new ApiException(422, 'total inválido');
            }
            $row->total = $t !== null ? (float) $t : null;
        }
        $row->save();

        return $this->out($row);
    }

    public function destroy(int $project_id, int $comparison_id)
    {
        $row = $this->row($project_id, $comparison_id);
        $path = $row->file_path;
        $row->delete();
        if ($path && Uploads::owns($path)) {
            Storage::disk('local')->delete($path);
        }

        return response()->noContent();
    }
}
