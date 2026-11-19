<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

/**
 * Borra una empresa COMPLETA y todo lo suyo (usuarios, clientes, proyectos, facturas…) de la base indicada. Pensado para
 * quitar empresas de prueba de la copia que se va a subir al servidor. Nunca borra la empresa 1 (la original).
 * Sin --yes solo MUESTRA lo que se borraría.
 */
class DeleteCompany extends Command
{
    protected $signature = 'multitec:delete-company {id : id de la empresa} {--connection=real : conexión de base de datos} {--yes : confirmar el borrado}';
    protected $description = 'Borra una empresa de prueba y todos sus datos (sin --yes solo muestra qué borraría)';

    public function handle(): int
    {
        $id = (int) $this->argument('id');
        $conn = (string) $this->option('connection');
        DB::setDefaultConnection($conn);
        $db = DB::connection()->getDatabaseName();
        if ($id === 1) {
            $this->error('La empresa 1 es la original (Multitec): me niego a borrarla.');

            return 1;
        }
        $company = DB::table('companies')->where('id', $id)->first();
        if (! $company) {
            $this->error("No existe la empresa $id en $db.");

            return 1;
        }
        $this->info("Empresa $id «{$company->name}» en la base $db");

        $tables = DB::table('information_schema.columns')->where('table_schema', $db)->where('column_name', 'company_id')
            ->where('table_name', '!=', 'companies')->selectRaw('table_name AS t')->pluck('t')->all();
        sort($tables);
        $userIds = DB::table('users')->where('company_id', $id)->pluck('id')->all();
        $plan = [];
        foreach ($tables as $t) {
            $n = DB::table($t)->where('company_id', $id)->count();
            if ($n) {
                $plan[$t] = $n;
            }
        }
        $tokens = $userIds ? DB::table('refresh_tokens')->whereIn('user_id', $userIds)->count() : 0;
        foreach ($plan as $t => $n) {
            $this->line(sprintf('   %-22s %5d fila(s)', $t, $n));
        }
        $this->line(sprintf('   %-22s %5d fila(s)', 'refresh_tokens', $tokens));
        if (! $this->option('yes')) {
            $this->warn('No se borró nada. Para borrar de verdad agrega --yes');

            return 0;
        }

        DB::transaction(function () use ($tables, $id, $userIds) {
            DB::statement('SET FOREIGN_KEY_CHECKS=0');
            if ($userIds) {
                DB::table('refresh_tokens')->whereIn('user_id', $userIds)->delete();
            }
            foreach ($tables as $t) {
                DB::table($t)->where('company_id', $id)->delete();
            }
            DB::table('companies')->where('id', $id)->delete();
            DB::statement('SET FOREIGN_KEY_CHECKS=1');
        });
        $this->info("Empresa $id borrada.");

        return 0;
    }
}
