<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\CompanyProfile;
use App\Support\ApiException;
use App\Support\Audit;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

class CompanyController extends Controller
{
    private const LOGO_TYPES = ['image/png' => 'png', 'image/jpeg' => 'jpg', 'image/webp' => 'webp'];
    private const LOGO_MAX_BYTES = 5 * 1024 * 1024;

    private function profile(): ?CompanyProfile
    {
        return CompanyProfile::first();
    }

    private function out(): array
    {
        $p = $this->profile();
        $out = [];
        foreach (array_keys(CompanyProfile::FIELDS) as $f) {
            $out[$f] = $p?->$f ?? '';
        }
        $out['has_logo'] = $p && $p->logo_path && Storage::disk('local')->exists($p->logo_path);

        return $out;
    }

    public function show()
    {
        return $this->out();
    }

    public function update(Request $r)
    {
        $profile = $this->profile() ?? new CompanyProfile();
        $changed = [];
        foreach (CompanyProfile::FIELDS as $f => $max) {
            if (! $r->has($f)) {
                continue;
            }
            $v = $r->input($f);
            $v = is_string($v) && trim($v) !== '' ? trim($v) : null;
            if ($v !== null && mb_strlen($v) > $max) {
                throw new ApiException(422, "El campo $f excede $max caracteres");
            }
            if ($profile->$f !== $v) {
                $changed[] = $f; // solo los nombres: el RNC y las cuentas no se copian a la bitácora
            }
            $profile->$f = $v;
        }
        $profile->updated_at = now();
        $profile->save();
        if ($changed) {
            Audit::log('company_updated', $r->attributes->get('user'), entity: 'company', detail: ['campos' => $changed], request: $r);
        }

        return $this->out();
    }

    public function uploadLogo(Request $r)
    {
        $file = $r->file('file');
        if (! $file || ! $file->isValid()) {
            throw new ApiException(400, 'Falta el archivo del logo.');
        }
        $info = @getimagesize($file->getRealPath());
        $mime = $info['mime'] ?? '';
        if (! isset(self::LOGO_TYPES[$mime])) {
            throw new ApiException(400, 'El logo debe ser una imagen PNG, JPG o WebP.');
        }
        if ($file->getSize() > self::LOGO_MAX_BYTES) {
            throw new ApiException(400, 'El logo es demasiado grande (máximo 5 MB).');
        }
        $profile = $this->profile() ?? new CompanyProfile();
        $dir = 'uploads/c'.app('company_id').'/company';
        $name = 'logo-'.Str::uuid().'.'.self::LOGO_TYPES[$mime];
        $path = $file->storeAs($dir, $name, 'local');
        $this->deleteLogoFile($profile->logo_path);
        $profile->logo_path = $path;
        $profile->updated_at = now();
        $profile->save();
        Audit::log('company_logo_changed', $r->attributes->get('user'), entity: 'company', request: $r);

        return $this->out();
    }

    public function deleteLogo(Request $r)
    {
        $profile = $this->profile() ?? new CompanyProfile();
        $this->deleteLogoFile($profile->logo_path);
        $profile->logo_path = '';
        $profile->updated_at = now();
        $profile->save();

        return $this->out();
    }

    public function logo()
    {
        $p = $this->profile();
        if (! $p || ! $p->logo_path || ! Storage::disk('local')->exists($p->logo_path)) {
            throw new ApiException(404, 'Todavía no hay logo');
        }

        return response()->file(Storage::disk('local')->path($p->logo_path), ['Cache-Control' => 'no-cache']);
    }

    /** Solo borra archivos dentro de la carpeta de logos DE ESTA empresa. */
    private function deleteLogoFile(?string $path): void
    {
        if ($path && \App\Support\Uploads::owns($path)) {
            Storage::disk('local')->delete($path);
        }
    }
}
