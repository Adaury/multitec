<?php

namespace App\Console\Commands;

use App\Models\Company;
use App\Models\CompanyProfile;
use App\Models\User;
use App\Support\CatalogSeeder;
use App\Support\SiteDefaults;
use Illuminate\Console\Command;
use Illuminate\Support\Str;

/**
 * Instalación limpia: crea la empresa dueña del sistema y su primer administrador (también administrador de la
 * plataforma) con una clave temporal que debe cambiar al entrar. Carga los planes y el catálogo base.
 *
 *   php artisan multitec:crear-administrador admin@tudominio.com --empresa="Mi empresa" --nombre="Tu nombre"
 *
 * La última línea de la salida es  CLAVE_TEMPORAL=...  (se muestra una sola vez; no se guarda en claro).
 */
class CreateAdmin extends Command
{
    protected $signature = 'multitec:crear-administrador {email : correo con el que entrará} {--empresa=Mi empresa : nombre de la empresa} {--nombre=Administrador : nombre de la persona}';
    protected $description = 'Crea la empresa y el primer administrador de una instalación limpia (clave temporal de un solo uso)';

    public function handle(): int
    {
        $email = mb_strtolower(trim((string) $this->argument('email')));
        if (! filter_var($email, FILTER_VALIDATE_EMAIL)) {
            $this->error('Correo inválido.');

            return 1;
        }
        if (User::where('email', $email)->exists()) {
            $this->error('Ya existe un usuario con ese correo.');

            return 1;
        }
        $empresa = trim((string) $this->option('empresa')) ?: 'Mi empresa';
        $nombre = trim((string) $this->option('nombre')) ?: 'Administrador';
        $clave = rtrim(strtr(base64_encode(random_bytes(9)), '+/', 'Aa'), '=');

        SiteDefaults::ensure(); // planes y textos de la página pública
        $company = Company::create([
            'name' => $empresa, 'slug' => Str::slug($empresa) ?: 'empresa', 'source' => 'instalacion',
            'contact_name' => $nombre, 'contact_email' => $email, 'created_at' => now(),
        ]);
        CompanyProfile::withoutGlobalScopes()->forceCreate(['company_id' => $company->id, 'name' => $empresa, 'email' => $email]);
        $admin = User::create([
            'company_id' => $company->id, 'name' => $nombre, 'email' => $email, 'hashed_password' => password_hash($clave, PASSWORD_BCRYPT),
            'role' => 'admin', 'is_platform_admin' => true, 'must_change_password' => true, 'created_at' => now(),
        ]);

        app()->instance('company_id', $company->id);
        try {
            CatalogSeeder::categories();
            CatalogSeeder::ensureRoots();
            CatalogSeeder::baseCatalog($admin->id);
        } catch (\Throwable $e) {
            $this->warn('No se pudo cargar el catálogo base (se puede cargar después desde Catálogo): '.$e->getMessage());
        } finally {
            app()->forgetInstance('company_id');
        }

        $this->info("Empresa «{$empresa}» y administrador {$email} creados. Debe cambiar la clave al entrar.");
        $this->line('CLAVE_TEMPORAL='.$clave);

        return 0;
    }
}
