<?php

/*
 * Verificador de requisitos de Multitec. NO necesita nada instalado: súbelo solo, ábrelo una vez y BÓRRALO.
 *   - Por navegador: https://tudominio.com/requisitos.php?clave=LA_CLAVE_QUE_ESCRIBAS_ABAJO
 *   - Por SSH:       php requisitos.php
 * Antes de subirlo, cambia la clave. Muestra la versión de PHP y de qué está equipado el servidor; no toca la base de datos.
 */

const CLAVE = 'CAMBIA-ESTA-CLAVE';

if (PHP_SAPI !== 'cli') {
    if (CLAVE === 'CAMBIA-ESTA-CLAVE' || ! hash_equals(CLAVE, (string) ($_GET['clave'] ?? ''))) {
        http_response_code(403);
        exit('Acceso denegado. Edita la CLAVE dentro de este archivo y ábrelo con ?clave=...');
    }
    header('Content-Type: text/plain; charset=utf-8');
    header('X-Robots-Tag: noindex');
}

$errores = 0;
$avisos = 0;
function ok($m) { echo "  [OK]    $m\n"; }
function aviso($m) { global $avisos; $avisos++; echo "  [AVISO] $m\n"; }
function mal($m) { global $errores; $errores++; echo "  [ERROR] $m\n"; }
function bytes($v) { $v = trim((string) $v); $n = (int) $v; switch (strtolower(substr($v, -1))) { case 'g': return $n * 1024 ** 3; case 'm': return $n * 1024 ** 2; case 'k': return $n * 1024; } return $n; }

echo "REQUISITOS DE MULTITEC\n======================\n\n";
echo "PHP\n";
PHP_VERSION_ID >= 80300 ? ok('PHP '.PHP_VERSION) : mal('Hace falta PHP 8.3 o superior (hay '.PHP_VERSION.'). Cámbialo en hPanel → Avanzado → Configuración de PHP.');
echo '  SAPI: '.PHP_SAPI."\n\n";

echo "Extensiones\n";
$exts = ['pdo_mysql' => 'base de datos', 'mbstring' => 'textos con tildes', 'openssl' => 'cifrado y tokens', 'gd' => 'fotos y PDF',
    'fileinfo' => 'validar archivos', 'ctype' => 'validaciones', 'json' => 'JSON', 'tokenizer' => 'Laravel', 'xml' => 'PDF', 'dom' => 'PDF', 'curl' => 'mapa y correo',
    'zip' => 'Excel', 'simplexml' => 'Excel', 'xmlreader' => 'Excel', 'xmlwriter' => 'Excel'];
foreach ($exts as $e => $why) {
    extension_loaded($e) ? ok("$e ($why)") : mal("Falta $e ($why). Actívala en hPanel → PHP → Extensiones.");
}
extension_loaded('exif') ? ok('exif (enderezar fotos de iPhone)') : aviso('Sin exif, las fotos de iPhone pueden salir de lado en los PDF.');
extension_loaded('gd') && function_exists('imagecreatefromwebp') ? ok('GD con WebP') : aviso('GD sin WebP.');
extension_loaded('zip') ? ok('zip') : aviso('Sin zip (solo hace falta para descomprimir desde PHP).');

echo "\nLímites\n";
bytes(ini_get('upload_max_filesize')) >= 25 * 1024 ** 2 ? ok('upload_max_filesize '.ini_get('upload_max_filesize')) : aviso('upload_max_filesize es '.ini_get('upload_max_filesize').': fotos y audios de hasta 25 MB fallarán. Ponlo en 32M (hPanel → PHP → Opciones).');
bytes(ini_get('post_max_size')) >= 26 * 1024 ** 2 ? ok('post_max_size '.ini_get('post_max_size')) : aviso('post_max_size es '.ini_get('post_max_size').' (debe ser mayor que upload_max_filesize).');
$m = ini_get('memory_limit');
($m === '-1' || bytes($m) >= 128 * 1024 ** 2) ? ok("memory_limit $m") : aviso("memory_limit es $m: los PDF con muchas fotos pueden quedarse sin memoria (recomendado 256M).");
$t = (int) ini_get('max_execution_time');
($t === 0 || $t >= 60) ? ok('max_execution_time '.($t ?: 'sin límite')) : aviso("max_execution_time es {$t}s (recomendado 60 o más).");

echo "\nSeguridad del servidor\n";
$https = (! empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') || ($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https';
PHP_SAPI === 'cli' ? ok('(en consola no se revisa HTTPS)') : ($https ? ok('Esta página llegó por HTTPS') : aviso('Entraste por http: activa el SSL gratis en hPanel → Seguridad → SSL y fuerza HTTPS.'));
ini_get('display_errors') && strtolower(ini_get('display_errors')) !== 'off' && PHP_SAPI !== 'cli' ? aviso('display_errors está activo en PHP (la aplicación lo apaga con APP_DEBUG=false, pero conviene apagarlo también aquí).') : ok('display_errors apagado');

echo "\n";
echo $errores ? "RESULTADO: $errores error(es), $avisos aviso(s). Corrige los errores antes de instalar.\n" : "RESULTADO: sin errores, $avisos aviso(s). Puedes instalar.\n";
echo "\nIMPORTANTE: borra este archivo del servidor cuando termines.\n";
