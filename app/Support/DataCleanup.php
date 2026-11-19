<?php

namespace App\Support;

use App\Models\Client;
use App\Models\Invoice;
use App\Models\Notification;
use App\Models\Product;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;

/**
 * Borrar datos de prueba: clientes (con todo lo que cuelga de ellos) y productos del catálogo.
 *
 * Cómo decide qué borrar: recorre las llaves foráneas de la base. Una fila que no puede existir sin su padre (columna NOT NULL,
 * p. ej. la cotización de un proyecto) se borra con él; una referencia opcional (columna que admite NULL) se conserva y solo se
 * suelta (queda en NULL). Así nunca queda una fila apuntando a algo que ya no existe y no se pierde lo que tiene valor propio.
 *
 * Seguridad: solo administradores, hay que escribir BORRAR; antes de borrar se guarda un archivo SQL con las filas que se van a
 * borrar (si no se puede escribir, NO se borra); queda anotado en Auditoría; y todo dentro de la empresa de la sesión.
 */
class DataCleanup
{
    public const CONFIRM_WORD = 'BORRAR';
    public const MAX_PER_REQUEST = 500;
    private const TEST_NAME = '/\b(test|tests|testing|prueba|pruebas|verify|smoke|demo|ejemplo|ignorar|e2e|dummy|fake|borrar)\b/iu';
    private const LABELS = [
        'clients' => 'Clientes', 'projects' => 'Proyectos', 'quotes' => 'Cotizaciones', 'quote_items' => 'Partidas de cotización',
        'budgets' => 'Presupuestos', 'invoices' => 'Facturas', 'pre_invoices' => 'Prefacturas', 'tickets' => 'Tickets', 'visits' => 'Visitas',
        'surveys' => 'Levantamientos', 'survey_assets' => 'Fotos y audios del levantamiento', 'ticket_assets' => 'Fotos de tickets',
        'log_entries' => 'Entradas de bitácora', 'client_assets' => 'Equipos instalados', 'products' => 'Productos',
        'stock_movements' => 'Movimientos de inventario', 'materials' => 'Materiales de proyecto',
    ];
    /** Lo que se muestra en el resumen (lo demás —historiales, etc.— se borra igual, pero no se lista). */
    private const SUMMARY = ['clients', 'projects', 'quotes', 'budgets', 'invoices', 'tickets', 'visits', 'surveys', 'survey_assets',
        'ticket_assets', 'log_entries', 'client_assets', 'materials', 'products', 'stock_movements'];

    public static function looksLikeTest(?string ...$texts): bool
    {
        foreach ($texts as $t) {
            if ($t && preg_match(self::TEST_NAME, $t)) {
                return true;
            }
        }

        return false;
    }

    // ---- grafo de llaves foráneas ------------------------------------------------------------------

    /** @return array{refs: array<string, array<int, array{0:string,1:string,2:bool}>>, pk: array<string,string>} */
    private static function schema(): array
    {
        static $cache = [];
        $db = DB::connection()->getDatabaseName();
        if (isset($cache[$db])) {
            return $cache[$db];
        }
        $refs = [];
        $rows = DB::select(
            'SELECT k.TABLE_NAME AS child, k.COLUMN_NAME AS col, k.REFERENCED_TABLE_NAME AS parent, (c.IS_NULLABLE = "YES") AS nullable
             FROM information_schema.KEY_COLUMN_USAGE k
             JOIN information_schema.COLUMNS c ON c.TABLE_SCHEMA = k.TABLE_SCHEMA AND c.TABLE_NAME = k.TABLE_NAME AND c.COLUMN_NAME = k.COLUMN_NAME
             WHERE k.TABLE_SCHEMA = ? AND k.REFERENCED_TABLE_NAME IS NOT NULL',
            [$db],
        );
        foreach ($rows as $r) {
            $refs[$r->parent][] = [$r->child, $r->col, (bool) $r->nullable];
        }
        $pkCols = [];
        foreach (DB::select('SELECT TABLE_NAME AS t, COLUMN_NAME AS c FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA = ? AND CONSTRAINT_NAME = "PRIMARY"', [$db]) as $r) {
            $pkCols[$r->t][] = $r->c;
        }
        $pk = [];
        foreach ($pkCols as $t => $cols) {
            if (count($cols) === 1) {
                $pk[$t] = $cols[0]; // las tablas con llave compuesta se borran directo por la columna que apunta al padre
            }
        }

        return $cache[$db] = ['refs' => $refs, 'pk' => $pk];
    }

    /**
     * Calcula, sin tocar nada, lo que se borraría.
     *
     * @return array{plan: array, clients: \Illuminate\Support\Collection, products: \Illuminate\Support\Collection}
     * @throws \InvalidArgumentException
     */
    public static function buildPlan(array $clientIds, array $productIds): array
    {
        if (count($clientIds) + count($productIds) > self::MAX_PER_REQUEST) {
            throw new \InvalidArgumentException('Elige como máximo '.self::MAX_PER_REQUEST.' registros por vez');
        }
        // Con el filtro de empresa de la sesión: un id de otra empresa simplemente no aparece.
        $clients = $clientIds ? Client::whereIn('id', $clientIds)->get() : collect();
        $products = $productIds ? Product::whereIn('id', $productIds)->get() : collect();
        $plan = ['ids' => [], 'order' => [], 'detach' => []];
        foreach ([['clients', $clients], ['products', $products]] as [$table, $rows]) {
            if ($rows->isEmpty()) {
                continue;
            }
            $ids = $rows->pluck('id')->all();
            $plan['ids'][$table] = array_values(array_unique(array_merge($plan['ids'][$table] ?? [], $ids)));
            self::walk($table, $ids, $plan);
            $plan['order'][] = [$table, 'id', $ids];
        }

        return ['plan' => $plan, 'clients' => $clients, 'products' => $products];
    }

    private static function walk(string $table, array $ids, array &$plan): void
    {
        $s = self::schema();
        foreach ($s['refs'][$table] ?? [] as [$child, $col, $nullable]) {
            if ($nullable) {
                $plan['detach'][] = [$child, $col, $ids];
                continue;
            }
            $pk = $s['pk'][$child] ?? null;
            if ($pk) {
                $found = DB::table($child)->whereIn($col, $ids)->pluck($pk)->all();
                $new = array_values(array_diff($found, $plan['ids'][$child] ?? []));
                if ($new) {
                    $plan['ids'][$child] = array_merge($plan['ids'][$child] ?? [], $new);
                    self::walk($child, $new, $plan);
                    $plan['order'][] = [$child, $pk, $new]; // los hijos antes que el padre
                }
            } else {
                $plan['order'][] = [$child, $col, $ids];
            }
        }
    }

    private static function fileTables(array $plan): array
    {
        $out = [];
        foreach ($plan['order'] as [$t, $c, $v]) {
            if (! empty($plan['ids'][$t]) && \Illuminate\Support\Facades\Schema::hasColumn($t, 'file_path')) {
                $out[$t] = true;
            }
        }

        return array_keys($out);
    }

    private static function filePaths(array $plan): array
    {
        $s = self::schema();
        $paths = [];
        foreach (self::fileTables($plan) as $t) {
            if ($pk = $s['pk'][$t] ?? null) {
                foreach (array_chunk($plan['ids'][$t], 500) as $chunk) {
                    $paths = array_merge($paths, DB::table($t)->whereIn($pk, $chunk)->whereNotNull('file_path')->pluck('file_path')->all());
                }
            }
        }

        return array_values(array_unique($paths));
    }

    public static function describe(array $built): array
    {
        ['plan' => $plan, 'clients' => $clients, 'products' => $products] = $built;
        $counts = [];
        foreach ($plan['ids'] as $t => $ids) {
            if ($ids) {
                $counts[$t] = count($ids);
            }
        }
        $fiscal = [];
        if (! empty($plan['ids']['invoices'])) {
            foreach (Invoice::whereIn('id', $plan['ids']['invoices'])->whereNotNull('ncf')->orderBy('code')->get(['code', 'ncf', 'voided_at']) as $i) {
                $fiscal[] = ['code' => $i->code, 'ncf' => $i->ncf, 'voided' => $i->voided_at !== null];
            }
        }
        $summary = [];
        foreach (self::SUMMARY as $k) {
            if (! empty($counts[$k])) {
                $summary[] = ['key' => $k, 'label' => self::LABELS[$k] ?? $k, 'count' => $counts[$k]];
            }
        }

        return [
            'clients' => $clients->pluck('name')->all(), 'products' => $products->pluck('name')->all(),
            'counts' => $summary, 'fiscal_invoices' => $fiscal, 'files' => count(self::filePaths($plan)),
        ];
    }

    // ---- copia previa -----------------------------------------------------------------------------

    private static function sqlValue($v): string
    {
        return $v === null ? 'NULL' : (is_int($v) || is_float($v) ? (string) $v : DB::getPdo()->quote((string) $v));
    }

    /**
     * Guarda un archivo SQL con las filas que se van a borrar (y el valor previo de las referencias que se sueltan), para poder
     * restaurarlas desde phpMyAdmin. Sin pg_dump/mysqldump: funciona igual en un hosting compartido. Si no se puede escribir, lanza.
     */
    public static function backup(array $plan): string
    {
        $dir = 'backups';
        $name = 'antes-de-borrar-pruebas_'.date('Y-m-d_His').'.sql';
        $s = self::schema();
        $out = ['-- Copia de las filas borradas por «Borrar datos de prueba» ('.date('c').")\n-- Para deshacer: importar este archivo en phpMyAdmin.\nSET FOREIGN_KEY_CHECKS=0;\n"];
        // Del padre a los hijos, para que al restaurar existan las filas referidas.
        foreach (array_reverse($plan['order']) as [$table, $col, $values]) {
            foreach (array_chunk(array_values($values), 500) as $chunk) {
                foreach (DB::table($table)->whereIn($col, $chunk)->get() as $row) {
                    $row = (array) $row;
                    $out[] = 'INSERT INTO `'.$table.'` (`'.implode('`,`', array_keys($row)).'`) VALUES ('.implode(',', array_map([self::class, 'sqlValue'], $row)).");\n";
                }
            }
        }
        foreach ($plan['detach'] as [$table, $col, $ids]) {
            $pk = $s['pk'][$table] ?? null;
            if (! $pk) {
                continue;
            }
            foreach (array_chunk($ids, 500) as $chunk) {
                foreach (DB::table($table)->whereIn($col, $chunk)->get([$pk, $col]) as $r) {
                    $out[] = "UPDATE `$table` SET `$col` = ".self::sqlValue($r->$col)." WHERE `$pk` = ".self::sqlValue($r->$pk).";\n";
                }
            }
        }
        $out[] = "SET FOREIGN_KEY_CHECKS=1;\n";
        $content = implode('', $out);
        if (! Storage::disk('local')->put("$dir/$name", $content) || Storage::disk('local')->size("$dir/$name") === 0) {
            throw new \RuntimeException('No se pudo guardar la copia de seguridad; no se borró nada');
        }

        return $name;
    }

    // ---- borrado ------------------------------------------------------------------------------------

    /** Borra según el plan (dentro de la transacción de quien llama). Devuelve las rutas de archivos a eliminar después. */
    public static function execute(array $plan): array
    {
        $files = self::filePaths($plan);
        foreach ($plan['detach'] as [$table, $col, $ids]) {
            foreach (array_chunk($ids, 500) as $chunk) {
                DB::table($table)->whereIn($col, $chunk)->update([$col => null]);
            }
        }
        foreach ($plan['order'] as [$table, $col, $values]) {
            foreach (array_chunk(array_values($values), 500) as $chunk) {
                DB::table($table)->whereIn($col, $chunk)->delete();
            }
        }
        // Los avisos de la campanita que apuntaban a esos proyectos ya no llevarían a ningún lado.
        foreach (array_chunk($plan['ids']['projects'] ?? [], 100) as $chunk) {
            Notification::where(function ($q) use ($chunk) {
                foreach ($chunk as $pid) {
                    $p = "/proyectos/$pid";
                    $q->orWhere('link', $p)->orWhere('link', 'like', "$p?%")->orWhere('link', 'like', "$p/%");
                }
            })->delete();
        }

        return $files;
    }

    public static function removeFiles(array $paths): int
    {
        $n = 0;
        foreach ($paths as $p) {
            try {
                if (Uploads::owns($p) && Storage::disk('local')->exists($p)) {
                    Storage::disk('local')->delete($p);
                    $n++;
                }
            } catch (\Throwable) {
                // un archivo que no se pudo quitar no debe deshacer el borrado ya hecho
            }
        }

        return $n;
    }

    public static function candidates(): array
    {
        $by = fn ($rows) => collect($rows)->pluck('c', 'client_id')->all();
        $count = fn (string $table, ?callable $extra = null) => $by(
            DB::table('projects')->join($table, "$table.project_id", '=', 'projects.id')
                ->when($extra, fn ($q) => $extra($q))->where('projects.company_id', app('company_id'))
                ->groupBy('projects.client_id')->selectRaw('projects.client_id, count(*) as c')->get(),
        );
        $projects = $by(DB::table('projects')->where('company_id', app('company_id'))->groupBy('client_id')->selectRaw('client_id, count(*) as c')->get());
        $quotes = $count('quotes');
        $invoices = $count('invoices');
        $fiscal = $count('invoices', fn ($q) => $q->whereNotNull('invoices.ncf'));
        $tickets = $count('tickets');
        $clients = Client::orderByDesc('created_at')->orderByDesc('id')->get()->map(fn ($c) => [
            'id' => $c->id, 'name' => $c->name, 'company' => $c->company, 'created_at' => $c->created_at, 'projects' => (int) ($projects[$c->id] ?? 0),
            'quotes' => (int) ($quotes[$c->id] ?? 0), 'invoices' => (int) ($invoices[$c->id] ?? 0), 'fiscal_invoices' => (int) ($fiscal[$c->id] ?? 0),
            'tickets' => (int) ($tickets[$c->id] ?? 0), 'suspect' => self::looksLikeTest($c->name, $c->company),
        ])->all();
        $used = DB::table('quote_items')->where('company_id', app('company_id'))->whereNotNull('product_id')->groupBy('product_id')
            ->selectRaw('product_id, count(*) as c')->pluck('c', 'product_id')->all();
        $products = Product::orderBy('code')->get()->map(fn ($p) => [
            'id' => $p->id, 'code' => $p->code, 'name' => $p->name, 'price' => (float) ($p->price ?? 0),
            'used_in_quotes' => (int) ($used[$p->id] ?? 0), 'suspect' => self::looksLikeTest($p->name),
        ])->all();

        return ['clients' => $clients, 'products' => $products, 'confirm_word' => self::CONFIRM_WORD];
    }
}
