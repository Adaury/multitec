<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

/**
 * Importa los datos REALES de Multitec exportados de PostgreSQL (archivos JSON-lines de pg_export.py) a la base
 * `real` de MySQL, conservando los id (todo lo que se enlaza por id sigue enlazado). Nunca toca la base de pruebas.
 *
 *   php artisan multitec:import-real C:\ruta\laravel-import --check   (solo informa: no escribe nada)
 *   php artisan multitec:import-real C:\ruta\laravel-import
 */
class ImportReal extends Command
{
    protected $signature = 'multitec:import-real {dir : Carpeta con los .jsonl exportados} {--check : Solo revisar columnas y conteos, sin escribir}';
    protected $description = 'Importa los datos reales exportados de PostgreSQL a la base «real» de MySQL';

    /** Orden de carga (los id se conservan y las llaves foráneas se validan al final). */
    private const ORDER = [
        'companies', 'platform_plans', 'testimonials', 'site_partners', 'users', 'company_profile', 'company_payments',
        'refresh_tokens', 'audit_log', 'notifications', 'clients', 'categories', 'suppliers', 'products', 'projects', 'engineering',
        'project_stages', 'surveys', 'survey_assets', 'survey_markers', 'visits', 'budgets', 'budget_items', 'quotes', 'quote_items',
        'quote_history', 'pre_invoices', 'pre_invoice_items', 'invoices', 'invoice_items', 'invoice_history', 'materials',
        'stock_movements', 'catalog_rules', 'technical_rules', 'product_relations', 'calculation_parameters', 'ncf_sequences',
        'purchase_invoices', 'tickets', 'ticket_history', 'ticket_assets', 'log_entries', 'log_entry_assets', 'extensions',
        'client_assets', 'code_sequences',
    ];

    public function handle(): int
    {
        DB::setDefaultConnection('real');
        $db = DB::connection('real')->getDatabaseName();
        $dev = (string) config('database.connections.mysql.database');
        if ($db === $dev) {
            $this->error("La base «real» ($db) es la misma de pruebas: me niego a mezclar datos reales con datos de prueba.");

            return 1;
        }
        $dir = rtrim((string) $this->argument('dir'), '\\/');
        if (! is_file("$dir/_summary.json")) {
            $this->error("No encuentro $dir/_summary.json (corre primero pg_export.py)");

            return 1;
        }
        $check = (bool) $this->option('check');
        if (! $check && DB::table('companies')->exists()) {
            $this->error("La base $db ya tiene datos. Para repetir la importación vacíala primero (migrate:fresh --database=real).");

            return 1;
        }

        $summary = collect(json_decode((string) file_get_contents("$dir/_summary.json"), true))->keyBy('table');
        $this->info(($check ? 'REVISIÓN (no se escribe nada)' : 'IMPORTANDO')." → base $db");
        $notInSchema = [];
        $problems = 0;

        if (! $check) {
            DB::statement('SET FOREIGN_KEY_CHECKS=0');
        }
        foreach (self::ORDER as $table) {
            if (! $summary->has($table)) {
                $this->line("  - $table: no existe en la base original (se omite)");
                continue;
            }
            $pgCols = $summary[$table]['columns'];
            $myCols = Schema::getColumnListing($table);
            $dropped = array_values(array_diff($pgCols, $myCols));
            $missing = array_values(array_diff($myCols, $pgCols));
            // Columnas obligatorias de MySQL que el original no trae y no tienen valor por defecto: la importación fallaría.
            $required = DB::table('information_schema.columns')->where('table_schema', $db)->where('table_name', $table)
                ->where('is_nullable', 'NO')->whereNull('column_default')->where('extra', 'not like', '%auto_increment%')
                ->selectRaw('column_name AS cn')->pluck('cn')->all();
            $fatal = array_values(array_intersect($missing, $required));
            $note = '';
            if ($dropped) {
                $note .= ' | solo en el original (se descartan): '.implode(',', $dropped);
            }
            if ($missing) {
                $note .= ' | solo en Laravel (quedan por defecto): '.implode(',', $missing);
            }
            if ($fatal) {
                $note .= ' | ⚠ OBLIGATORIAS SIN VALOR: '.implode(',', $fatal);
                $problems++;
            }

            $n = 0;
            if (! $check) {
                $batch = [];
                $fh = fopen("$dir/$table.jsonl", 'r');
                while (($line = fgets($fh)) !== false) {
                    if (trim($line) === '') {
                        continue;
                    }
                    $row = json_decode($line, true);
                    $out = [];
                    foreach ($row as $k => $v) {
                        if (! in_array($k, $myCols, true)) {
                            continue;
                        }
                        $out[$k] = is_array($v) ? json_encode($v, JSON_UNESCAPED_UNICODE) : $v;
                    }
                    $batch[] = $out;
                    $n++;
                    if (count($batch) >= 200) {
                        DB::table($table)->insert($batch);
                        $batch = [];
                    }
                }
                fclose($fh);
                if ($batch) {
                    DB::table($table)->insert($batch);
                }
            } else {
                $n = $summary[$table]['rows'];
            }
            $this->line(sprintf('  %s %-24s %5d filas%s', $problems && $fatal ? '✗' : '✓', $table, $n, $note));
        }
        if (! $check) {
            DB::statement('SET FOREIGN_KEY_CHECKS=1');
        }

        foreach (['alembic_version', 'ai_feedback_events', 'product_match_corrections', 'project_embeddings', 'quote_comparisons', 'voice_survey_examples'] as $t) {
            if ($summary->has($t)) {
                $notInSchema[] = $t.' ('.$summary[$t]['rows'].')';
            }
        }
        $this->newLine();
        $this->line('Sin tabla equivalente todavía (quedan archivadas en la carpeta de exportación; son de la IA): '.implode(', ', $notInSchema));

        return $problems ? 1 : 0;
    }
}
