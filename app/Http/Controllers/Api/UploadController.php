<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Support\ApiException;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;

class UploadController extends Controller
{
    /**
     * Fotos y audios del trabajo: solo con sesión, y cada empresa solo ve su carpeta (uploads/c{id}/...).
     * Un archivo sin prefijo (anterior a multi-empresa) es de la empresa 1.
     */
    public function show(Request $r, string $path)
    {
        $root = realpath(Storage::disk('local')->path('uploads'));
        $target = $root ? realpath($root.DIRECTORY_SEPARATOR.$path) : false;
        if (! $target || ! is_file($target) || ! str_starts_with($target, $root.DIRECTORY_SEPARATOR)) {
            throw new ApiException(404, 'Archivo no encontrado');
        }
        $relative = str_replace('\\', '/', substr($target, strlen($root) + 1));
        $first = explode('/', $relative, 2)[0];
        $company = app('company_id');
        $allowed = preg_match('/^c(\d+)$/', $first, $m) ? (int) $m[1] === $company : $company === 1;
        if (! $allowed) {
            throw new ApiException(404, 'Archivo no encontrado'); // 404: no revela que existe
        }

        return response()->file($target, [
            'X-Content-Type-Options' => 'nosniff',
            'Content-Security-Policy' => "default-src 'none'; img-src 'self'; media-src 'self'; sandbox",
            'Cache-Control' => 'private, max-age=3600',
        ]);
    }
}
