<?php

use Illuminate\Support\Facades\Route;

// Archivos del trabajo (fotos/audios): solo con sesión y solo los de la propia empresa.
Route::get('/uploads/{path}', [\App\Http\Controllers\Api\UploadController::class, 'show'])
    ->where('path', '.*')->middleware('jwt');

// El frontend compilado (React) vive en public/ ; app.html es su index. Cualquier ruta que no sea /api ni un
// archivo real devuelve la app, para que las rutas del navegador (/clientes, /login...) funcionen al recargar.
Route::fallback(function (\Illuminate\Http\Request $request) {
    // Una ruta /api que no existe (aún) debe dar 404 en JSON, nunca la página de la app.
    if ($request->is('api/*') || $request->is('api')) {
        return response()->json(['detail' => 'Not Found'], 404);
    }
    $file = public_path('app.html');
    abort_unless(is_file($file), 404);

    // Sin caché: cada despliegue nuevo debe cargarse de inmediato (los archivos de /assets llevan hash y sí se guardan).
    return response()->file($file, ['Content-Type' => 'text/html; charset=utf-8', 'Cache-Control' => 'no-cache']);
});
