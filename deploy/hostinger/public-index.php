<?php

/*
 * Punto de entrada para Hostinger: este archivo va en public_html (la carpeta web). La aplicación completa (código, .env,
 * claves, vendor, storage) vive FUERA de public_html, en la carpeta «{{APP_DIR}}» al lado, para que nadie pueda pedir
 * esos archivos por internet. El script de construcción reemplaza {{APP_DIR}} por el nombre elegido.
 */

use Illuminate\Foundation\Application;
use Illuminate\Http\Request;

define('LARAVEL_START', microtime(true));

$base = dirname(__DIR__).'/{{APP_DIR}}';

// Modo mantenimiento (php artisan down)
if (file_exists($maintenance = $base.'/storage/framework/maintenance.php')) {
    require $maintenance;
}

require $base.'/vendor/autoload.php';

/** @var Application $app */
$app = require_once $base.'/bootstrap/app.php';
// La carpeta pública no está dentro de la aplicación: se le dice dónde está.
$app->usePublicPath(__DIR__);

$app->handleRequest(Request::capture());
