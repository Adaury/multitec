<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

/**
 * Compara CADA campo de CADA fila importada en la base «real» contra los archivos exportados de PostgreSQL, y revisa
 * que ninguna fila quede huérfana (apuntando a algo que no existe). No escribe nada.
 */
class VerifyImport extends Command
{
    protected $signature = 'multitec:verify-import {dir : Carpeta con los .jsonl exportados}';
    protected $description = 'Compara los datos importados con los exportados de PostgreSQL, fila por fila';

    /** @param mixed $a @param mixed $b */
    private function same($a, $b): bool
    {
        if ($a === null || $b === null) {
            return $a === $b;
        }
        if (is_array($a)) { // JSON: se compara el contenido, no el texto
            $b = is_string($b) ? json_decode($b, true) : $b;

            return $a == $b;
        }
        if (is_bool($a)) {
            return (int) $a === (int) $b;
        }
        if (is_numeric($a) && is_numeric($b) && ! (is_string($a) && is_string($b) && ! preg_match('/^-?\d+(\.\d+)?$/', $a))) {
            return abs((float) $a - (float) $b) < 1e-9;
        }

        return (string) $a === (string) $b;
    }

    public function handle(): int
    {
        DB::setDefaultConnection('real');
        $dir = rtrim((string) $this->argument('dir'), '\\/');
        $summary = collect(json_decode((string) file_get_contents("$dir/_summary.json"), true))->keyBy('table');
        $totalRows = 0;
        $totalFields = 0;
        $bad = 0;

        foreach ($summary as $table => $info) {
            if (! Schema::hasTable($table) || in_array($table, ['migrations'], true)) {
                continue;
            }
            $myCols = Schema::getColumnListing($table);
            $cols = array_values(array_intersect($info['columns'], $myCols));
            $pk = in_array('id', $info['columns'], true) ? ['id'] : (['code_sequences' => ['company_id', 'prefix']][$table] ?? [$info['columns'][0]]);
            $mine = DB::table($table)->get()->map(fn ($r) => (array) $r)->keyBy(fn ($r) => implode('|', array_map(fn ($k) => $r[$k], $pk)));
            $n = 0;
            $diffs = [];
            $fh = fopen("$dir/$table.jsonl", 'r');
            while (($line = fgets($fh)) !== false) {
                if (trim($line) === '') {
                    continue;
                }
                $src = json_decode($line, true);
                $n++;
                $key = implode('|', array_map(fn ($k) => $src[$k], $pk));
                $dst = $mine[$key] ?? null;
                if ($dst === null) {
                    $diffs[] = "falta la fila $key";
                    continue;
                }
                foreach ($cols as $c) {
                    $totalFields++;
                    if (! $this->same($src[$c], $dst[$c])) {
                        $diffs[] = "fila $key columna $c: original=".json_encode($src[$c], JSON_UNESCAPED_UNICODE).' laravel='.json_encode($dst[$c], JSON_UNESCAPED_UNICODE);
                    }
                }
            }
            fclose($fh);
            $extra = $mine->count() - $n;
            if ($extra !== 0) {
                $diffs[] = "hay $extra fila(s) de más en MySQL";
            }
            $totalRows += $n;
            $bad += count($diffs);
            $this->line(sprintf(' %s %-24s %5d filas%s', $diffs ? '✗' : '✓', $table, $n, $diffs ? '  ← '.count($diffs).' diferencia(s)' : ''));
            foreach (array_slice($diffs, 0, 5) as $d) {
                $this->line("      $d");
            }
        }
        $this->newLine();
        $this->info("Comparadas $totalRows filas y $totalFields campos: ".($bad ? "$bad DIFERENCIA(S)" : 'TODO IDÉNTICO'));

        // Integridad: filas que apuntan a algo que no existe.
        $this->newLine();
        $this->line('Integridad de referencias (filas huérfanas):');
        $db = DB::connection('real')->getDatabaseName();
        $fks = DB::select('SELECT TABLE_NAME t, COLUMN_NAME c, REFERENCED_TABLE_NAME rt, REFERENCED_COLUMN_NAME rc
            FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA = ? AND REFERENCED_TABLE_NAME IS NOT NULL', [$db]);
        $orph = 0;
        foreach ($fks as $fk) {
            $n = DB::table($fk->t)->whereNotNull($fk->c)
                // La tabla padre lleva alias: en las que se refieren a sí mismas (subcategoría → categoría) no se compararía contra sí misma.
                ->whereNotExists(fn ($q) => $q->select(DB::raw(1))->from("{$fk->rt} as ref_parent")->whereColumn("ref_parent.{$fk->rc}", "{$fk->t}.{$fk->c}"))->count();
            if ($n) {
                $orph += $n;
                $this->line("   ✗ {$fk->t}.{$fk->c} → {$fk->rt}: $n huérfana(s)");
            }
        }
        $this->info('Revisadas '.count($fks).' relaciones: '.($orph ? "$orph huérfana(s)" : 'ninguna huérfana'));

        return ($bad || $orph) ? 1 : 0;
    }
}
