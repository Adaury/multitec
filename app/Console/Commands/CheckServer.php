<?php

namespace App\Console\Commands;

use App\Models\User;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

/**
 * Revisa que el servidor cumple lo que Multitec necesita y que la instalación está lista para clientes reales.
 * Úsalo después de subir la aplicación:  php artisan multitec:check-server
 * No escribe nada. Termina con código 1 si hay algún ERROR (los AVISOS no impiden usarla, pero conviene leerlos).
 */
class CheckServer extends Command
{
    protected $signature = 'multitec:check-server';
    protected $description = 'Revisa requisitos del servidor y la configuración de producción';

    private int $errors = 0;
    private int $warnings = 0;

    private function ok(string $m): void
    {
        $this->line("  <info>✓</info> $m");
    }

    private function warn2(string $m): void
    {
        $this->warnings++;
        $this->line("  <comment>! AVISO:</comment> $m");
    }

    private function bad(string $m): void
    {
        $this->errors++;
        $this->line("  <error> ✗ ERROR </error> $m");
    }

    private function bytes(string $v): int
    {
        $v = trim($v);
        $n = (int) $v;

        return match (strtolower(substr($v, -1))) { 'g' => $n * 1024 ** 3, 'm' => $n * 1024 ** 2, 'k' => $n * 1024, default => $n };
    }

    public function handle(): int
    {
        $this->info('PHP y extensiones');
        PHP_VERSION_ID >= 80300 ? $this->ok('PHP '.PHP_VERSION) : $this->bad('Hace falta PHP 8.3 o superior (hay '.PHP_VERSION.'). Cámbialo en hPanel → PHP.');
        foreach (['pdo_mysql' => 'base de datos', 'mbstring' => 'textos con tildes', 'openssl' => 'cifrado y tokens', 'gd' => 'fotos y PDF', 'fileinfo' => 'validar archivos',
            'ctype' => 'validaciones', 'json' => 'JSON', 'tokenizer' => 'Laravel', 'xml' => 'PDF', 'dom' => 'PDF', 'curl' => 'mapa y correo',
    'zip' => 'Excel', 'simplexml' => 'Excel', 'xmlreader' => 'Excel', 'xmlwriter' => 'Excel'] as $ext => $why) {
            extension_loaded($ext) ? $this->ok("$ext ($why)") : $this->bad("Falta la extensión $ext ($why). Actívala en hPanel → PHP → Extensiones.");
        }
        extension_loaded('exif') ? $this->ok('exif (enderezar fotos de iPhone)') : $this->warn2('Sin la extensión exif las fotos de iPhone pueden salir de lado en los PDF.');
        function_exists('imagecreatefromwebp') ? $this->ok('GD con WebP') : $this->warn2('GD sin WebP: las fotos WebP no saldrán en el anexo del PDF.');

        $this->newLine();
        $this->info('Límites del servidor');
        $up = $this->bytes((string) ini_get('upload_max_filesize'));
        $post = $this->bytes((string) ini_get('post_max_size'));
        $up >= 25 * 1024 ** 2 ? $this->ok('upload_max_filesize '.ini_get('upload_max_filesize')) : $this->warn2('upload_max_filesize es '.ini_get('upload_max_filesize').': las fotos/audios de hasta 25 MB fallarán. Súbelo a 32M en hPanel → PHP → Opciones.');
        $post >= 26 * 1024 ** 2 ? $this->ok('post_max_size '.ini_get('post_max_size')) : $this->warn2('post_max_size es '.ini_get('post_max_size').' (debe ser ≥ upload_max_filesize).');
        $mem = ini_get('memory_limit');
        ($mem === '-1' || $this->bytes((string) $mem) >= 128 * 1024 ** 2) ? $this->ok("memory_limit $mem") : $this->warn2("memory_limit es $mem: los PDF con muchas fotos pueden quedarse sin memoria (recomendado 256M).");
        $te = (int) ini_get('max_execution_time');
        ($te === 0 || $te >= 60) ? $this->ok('max_execution_time '.($te ?: 'sin límite')) : $this->warn2("max_execution_time es {$te}s: súbelo a 60 o más.");

        $this->newLine();
        $this->info('Carpetas');
        foreach (['storage/app/private', 'storage/framework/cache', 'storage/framework/sessions', 'storage/framework/views', 'storage/logs', 'bootstrap/cache'] as $d) {
            $p = base_path($d);
            is_dir($p) && is_writable($p) ? $this->ok("$d escribible") : $this->bad("$d no existe o no se puede escribir (permisos 755/775).");
        }
        // En Hostinger la carpeta pública (public_html) está FUERA de la aplicación: por consola Laravel no la conoce, así que se
        // busca donde corresponde (junto a la aplicación) además de public/.
        $webs = array_filter([public_path(), dirname(base_path()).DIRECTORY_SEPARATOR.'public_html', getenv('PUBLIC_HTML') ?: null]);
        $found = null;
        foreach ($webs as $w) {
            if (is_file($w.DIRECTORY_SEPARATOR.'app.html')) {
                $found = $w;
                break;
            }
        }
        $found ? $this->ok("la aplicación (app.html) está en $found") : $this->bad('No encuentro app.html en la carpeta pública (¿subiste multitec-public_html.zip dentro de public_html?).');
        if ($found && ! is_file($found.DIRECTORY_SEPARATOR.'index.php')) {
            $this->bad("Falta index.php en $found.");
        }

        $this->newLine();
        $this->info('Configuración');
        config('app.env') === 'production' ? $this->ok('APP_ENV=production') : $this->bad('APP_ENV debe ser production (hay '.config('app.env').').');
        config('app.debug') === false ? $this->ok('APP_DEBUG=false') : $this->bad('APP_DEBUG está activo: mostraría rutas, consultas y claves a quien provoque un error.');
        str_starts_with((string) config('app.url'), 'https://') ? $this->ok('APP_URL con https') : $this->warn2('APP_URL no empieza con https:// ('.config('app.url').').');
        config('app.key') ? $this->ok('APP_KEY definida') : $this->bad('Falta APP_KEY (php artisan key:generate).');
        // config('app.jwt_secret') cae a APP_KEY si no hay JWT_SECRET propio: si son iguales, falta el propio.
        $jwt = (string) config('app.jwt_secret');
        if ($jwt === '' || $jwt === (string) config('app.key')) {
            $this->bad('Falta JWT_SECRET propio: sin él las sesiones se firmarían con APP_KEY. Genera uno aleatorio de 64 caracteres.');
        } elseif (strlen($jwt) < 32) {
            $this->bad('JWT_SECRET es demasiado corto (mínimo 32 caracteres; usa 64 aleatorios).');
        } else {
            $this->ok('JWT_SECRET propio y largo');
        }
        config('app.trusted_proxies') === '*' ? $this->warn2('TRUSTED_PROXIES=* : solo es seguro si el servidor no es alcanzable sin pasar por ese proxy (permite falsificar la IP y esquivar límites).') : $this->ok('Proxies de confianza: '.(config('app.trusted_proxies') ?: 'ninguno'));
        config('mail.default') === 'smtp' && config('mail.mailers.smtp.host') && config('mail.mailers.smtp.host') !== '127.0.0.1'
            ? $this->ok('Correo SMTP configurado') : $this->warn2('Correo sin configurar: los avisos por email y el envío de cotizaciones no saldrán (la campanita sí funciona).');
        (string) config('app.notification_email') !== '' ? $this->ok('NOTIFICATION_EMAIL definido') : $this->warn2('NOTIFICATION_EMAIL vacío: los avisos de nuevas empresas solo llegarán a la campanita.');

        $this->newLine();
        $this->info('Base de datos');
        try {
            $db = DB::connection()->getDatabaseName();
            $this->ok("Conecta a «{$db}»");
        } catch (\Throwable $e) {
            $this->bad('No conecta a la base de datos: '.$e->getMessage());

            return $this->finish();
        }
        foreach (['companies', 'users', 'clients', 'projects', 'quotes', 'invoices', 'ncf_sequences', 'audit_log'] as $t) {
            if (! Schema::hasTable($t)) {
                $this->bad("Falta la tabla $t: importa el SQL o corre php artisan migrate --force.");
            }
        }
        if ($this->errors === 0 || Schema::hasTable('companies')) {
            $this->ok(DB::table('information_schema.tables')->where('table_schema', $db)->count().' tablas');
            $n = DB::table('companies')->count();
            $n > 0 ? $this->ok("$n empresa(s), ".DB::table('users')->count().' usuario(s)') : $this->bad('La base está vacía (sin empresas).');
            User::where('is_platform_admin', true)->where('is_active', true)->exists() ? $this->ok('Hay un administrador de la plataforma activo') : $this->bad('No hay administrador de plataforma activo.');
            $demo = User::where('email', 'like', '%@example.%')->orWhere('email', 'like', '%@multitec.test')->count();
            $demo === 0 ? $this->ok('Sin usuarios de prueba') : $this->bad("Hay $demo usuario(s) de prueba (@example.* / @multitec.test): bórralos o desactívalos antes de abrir al público.");
            DB::table('ncf_sequences')->where('active', true)->where('expires_at', '>=', now()->toDateString())->exists()
                ? $this->ok('Hay secuencias NCF vigentes') : $this->warn2('Ninguna secuencia NCF vigente: no se podrá facturar hasta registrar un rango nuevo.');
        }

        return $this->finish();
    }

    private function finish(): int
    {
        $this->newLine();
        if ($this->errors) {
            $this->error("{$this->errors} error(es) y {$this->warnings} aviso(s): corrige los errores antes de usarla.");

            return 1;
        }
        $this->info("Sin errores. {$this->warnings} aviso(s).");

        return 0;
    }
}
