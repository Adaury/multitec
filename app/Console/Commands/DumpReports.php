<?php

namespace App\Console\Commands;

use App\Http\Controllers\Api\DashboardController;
use App\Models\Invoice;
use App\Models\Project;
use App\Models\Quote;
use App\Support\Dgii;
use App\Support\Margin;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

/**
 * Genera, con Laravel y la base «real», los MISMOS archivos que py_reports.py genera con el sistema original, para
 * compararlos uno a uno (reportes DGII 606/607/608 de cada mes, márgenes y seguimientos). No escribe en la base.
 */
class DumpReports extends Command
{
    protected $signature = 'multitec:dump-reports {dir} {--company=1}';
    protected $description = 'Genera los reportes de la base real para compararlos con los del sistema original';

    public function handle(): int
    {
        DB::setDefaultConnection('real');
        $dir = rtrim((string) $this->argument('dir'), '\\/');
        @mkdir($dir, 0777, true);
        app()->instance('company_id', (int) $this->option('company'));

        foreach ([2025, 2026] as $y) {
            for ($m = 1; $m <= 12; $m++) {
                $tag = sprintf('%d%02d', $y, $m);
                file_put_contents("$dir/606_$tag.csv", Dgii::csv606($y, $m));
                file_put_contents("$dir/607_$tag.csv", Dgii::csv607($y, $m));
                file_put_contents("$dir/608_$tag.csv", Dgii::csv608($y, $m));
                file_put_contents("$dir/607resumen_$tag.json", json_encode(Dgii::consumptionSummary($y, $m)));
            }
        }
        $w = fn ($name, $data) => file_put_contents("$dir/$name.json", json_encode($data));
        $w('margen_empresa', Margin::company());
        $w('margen_proyectos', Project::orderBy('id')->get()->mapWithKeys(fn ($p) => [(string) $p->id => Margin::project($p->id)])->all());
        $w('margen_cotizaciones', Quote::with('items')->orderBy('id')->get()->mapWithKeys(fn ($q) => [(string) $q->id => Margin::compute($q->items, 'cotizado')])->all());
        $w('margen_facturas', Invoice::with('items')->orderBy('id')->get()->mapWithKeys(fn ($i) => [(string) $i->id => Margin::compute($i->items, 'facturado')])->all());
        $w('seguimientos', json_decode(json_encode((new DashboardController)->followups()), true));
        $this->info("listo -> $dir");

        return 0;
    }
}
