<?php

namespace Database\Seeders;

use App\Models\Company;
use App\Models\User;
use Illuminate\Database\Seeder;

class DemoSeeder extends Seeder
{
    /** Datos de PRUEBA locales (no usar en producción). */
    public function run(): void
    {
        $c = Company::firstOrCreate(['slug' => 'multitec'], ['name' => 'Multitec', 'created_at' => now()]);
        User::firstOrCreate(['email' => 'admin@multitec.test'], [
            'company_id' => $c->id, 'name' => 'Admin Prueba', 'role' => 'admin', 'is_platform_admin' => true,
            'hashed_password' => password_hash('Prueba12345', PASSWORD_BCRYPT), 'created_at' => now(),
        ]);
    }
}
