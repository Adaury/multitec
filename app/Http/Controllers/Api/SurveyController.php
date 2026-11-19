<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Survey;
use App\Models\SurveyAsset;
use App\Models\SurveyMarker;
use App\Support\ApiException;
use App\Support\SurveyPoints;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

class SurveyController extends Controller
{
    private const EXT = [
        'image/jpeg' => 'jpg', 'image/png' => 'png', 'image/heic' => 'heic', 'image/webp' => 'webp',
        'audio/mpeg' => 'mp3', 'audio/mp4' => 'm4a', 'audio/m4a' => 'm4a', 'audio/x-m4a' => 'm4a',
        'audio/wav' => 'wav', 'audio/webm' => 'webm',
    ];
    private const ALLOWED = [
        'photo' => ['image/jpeg', 'image/png', 'image/heic', 'image/webp'],
        'audio' => ['audio/mpeg', 'audio/mp4', 'audio/m4a', 'audio/wav', 'audio/webm', 'audio/x-m4a'],
    ];
    private const MAX_BYTES = 25 * 1024 * 1024;

    private function survey(int $projectId): Survey
    {
        $s = Survey::with('assets.markers')->where('project_id', $projectId)->first();
        if (! $s) {
            throw new ApiException(404, 'Levantamiento no encontrado');
        }

        return $s;
    }

    public function show(int $project_id)
    {
        return $this->survey($project_id)->toOut();
    }

    public function update(Request $r, int $project_id)
    {
        $s = $this->survey($project_id);
        $data = [];
        foreach (['notes', 'measurements', 'observations'] as $f) {
            if ($r->has($f)) {
                $v = $r->input($f);
                if ($v !== null && mb_strlen((string) $v) > 10000) {
                    throw new ApiException(422, "El campo $f excede 10000 caracteres");
                }
                $data[$f] = $v;
            }
        }
        $s->update($data + ['updated_at' => now()]);

        return $this->survey($project_id)->toOut();
    }

    /** Comprueba que el contenido real coincide con el tipo declarado (no se confía en el cliente). */
    private function matchesDeclared(string $path, string $declared): bool
    {
        if (str_starts_with($declared, 'image/') && $declared !== 'image/heic') {
            $info = @getimagesize($path);

            return $info && ($info['mime'] ?? '') === $declared;
        }
        if ($declared === 'image/heic') {
            return substr((string) file_get_contents($path, false, null, 4, 4), 0, 4) === 'ftyp';
        }

        return true; // audio: se acepta el tipo declarado (la extensión guardada sale del tipo, nunca del nombre)
    }

    public function uploadAsset(Request $r, int $project_id)
    {
        $kind = (string) $r->input('kind', '');
        if (! isset(self::ALLOWED[$kind])) {
            throw new ApiException(400, "kind debe ser 'photo' o 'audio'");
        }
        $file = $r->file('file');
        if (! $file || ! $file->isValid()) {
            throw new ApiException(400, 'Falta el archivo');
        }
        // Chrome etiqueta el audio "audio/webm;codecs=opus": se compara solo el tipo base.
        $type = strtolower(trim(explode(';', (string) $file->getClientMimeType())[0]));
        if (! in_array($type, self::ALLOWED[$kind], true)) {
            throw new ApiException(400, "Tipo de archivo no permitido para $kind: ".$file->getClientMimeType());
        }
        if ($file->getSize() > self::MAX_BYTES) {
            throw new ApiException(413, 'El archivo supera el límite de 25 MB');
        }
        if (! $this->matchesDeclared($file->getRealPath(), $type)) {
            throw new ApiException(400, 'El contenido del archivo no corresponde al tipo declarado');
        }
        $survey = $this->survey($project_id);
        $dir = 'uploads/c'.app('company_id').'/surveys/'.$survey->id;
        $path = $file->storeAs($dir, Str::uuid()->toString().'.'.self::EXT[$type], 'local');
        $desc = $r->input('description');
        $asset = SurveyAsset::create([
            'survey_id' => $survey->id, 'kind' => $kind, 'file_path' => $path,
            'description' => $desc !== null ? mb_substr((string) $desc, 0, 255) : null, 'created_at' => now(),
        ]);

        return response()->json($asset->fresh('markers')->toOut(), 201);
    }

    public function updateMarkers(Request $r, int $project_id, int $asset_id)
    {
        $survey = $this->survey($project_id);
        $asset = $survey->assets->firstWhere('id', $asset_id);
        if (! $asset || $asset->kind !== 'photo') {
            throw new ApiException(404, 'Foto no encontrada');
        }
        $markers = $r->input('markers', []);
        if (! is_array($markers) || count($markers) > 60) {
            throw new ApiException(422, 'Máximo 60 marcadores por foto');
        }
        foreach ($markers as $m) {
            $x = $m['x'] ?? null;
            $y = $m['y'] ?? null;
            if (! is_numeric($x) || ! is_numeric($y) || $x < 0 || $x > 1 || $y < 0 || $y > 1) {
                throw new ApiException(422, 'Cada marcador necesita x e y entre 0 y 1');
            }
            if (isset($m['label']) && mb_strlen((string) $m['label']) > 80) {
                throw new ApiException(422, 'La etiqueta excede 80 caracteres');
            }
        }

        DB::transaction(function () use ($asset, $markers, $survey) {
            SurveyMarker::where('asset_id', $asset->id)->delete();
            foreach ($markers as $m) {
                $kind = isset($m['kind']) && in_array($m['kind'], SurveyPoints::keys(), true) ? $m['kind'] : null;
                $label = trim((string) ($m['label'] ?? ''));
                SurveyMarker::create([
                    'asset_id' => $asset->id, 'number' => 0, 'label' => $label === '' ? null : $label,
                    'kind' => $kind, 'x' => (float) $m['x'], 'y' => (float) $m['y'], 'created_at' => now(),
                ]);
            }
            // Renumera todo el levantamiento de corrido (1, 2, 3...) según el orden de las fotos.
            $n = 1;
            foreach (SurveyAsset::where('survey_id', $survey->id)->orderBy('id')->get() as $photo) {
                foreach (SurveyMarker::where('asset_id', $photo->id)->orderBy('id')->get() as $mk) {
                    $mk->update(['number' => $n++]);
                }
            }
        });

        return SurveyAsset::with('markers')->find($asset->id)->toOut();
    }

    public function deleteAsset(int $project_id, int $asset_id)
    {
        $survey = $this->survey($project_id);
        $asset = $survey->assets->firstWhere('id', $asset_id);
        if (! $asset) {
            throw new ApiException(404, 'Archivo no encontrado');
        }
        $path = $asset->file_path;
        $asset->delete();
        if ($path && \App\Support\Uploads::owns($path)) {
            Storage::disk('local')->delete($path);
        }

        return response()->noContent();
    }
}
