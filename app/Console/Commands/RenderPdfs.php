<?php

namespace App\Console\Commands;

use App\Models\Budget;
use App\Models\Invoice;
use App\Models\Quote;
use App\Models\Survey;
use App\Support\PdfBuilder;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;

/** Dibuja PDF con los datos REALES (base «real») para revisarlos a ojo. No escribe en la base. */
class RenderPdfs extends Command
{
    protected $signature = 'multitec:render-pdfs {dir} {--company=1}';
    protected $description = 'Genera PDF de ejemplo con datos reales (cotización con fotos, factura, presupuesto)';

    public function handle(): int
    {
        DB::setDefaultConnection('real');
        app()->instance('company_id', (int) $this->option('company'));
        $dir = rtrim((string) $this->argument('dir'), '\\/');
        @mkdir($dir, 0777, true);

        // Una cotización cuyo levantamiento tenga fotos que existan de verdad en disco (rutas antiguas sin prefijo incluidas).
        $quote = null;
        foreach (Quote::with('project.survey.assets')->orderByDesc('id')->get() as $q) {
            $photos = $q->project->survey?->assets->where('kind', 'photo') ?? collect();
            if ($photos->contains(fn ($a) => Storage::disk('local')->exists($a->file_path))) {
                $quote = $q;
                break;
            }
        }
        if ($quote) {
            $this->line("Cotización con fotos reales: {$quote->code} (proyecto {$quote->project->code})");
            file_put_contents("$dir/cotizacion_fotos.pdf", PdfBuilder::quote($quote, 'detallada', 'all'));
        } else {
            $this->warn('Ninguna cotización tiene fotos disponibles en disco');
        }
        if ($inv = Invoice::whereNull('voided_at')->orderByDesc('id')->first()) {
            file_put_contents("$dir/factura.pdf", PdfBuilder::invoice($inv));
            $this->line("Factura {$inv->code} ({$inv->ncf})");
        }
        if ($b = Budget::orderByDesc('id')->first()) {
            file_put_contents("$dir/presupuesto.pdf", PdfBuilder::budget($b));
            $this->line("Presupuesto {$b->code}");
        }
        $this->info('Fotos del levantamiento (total): '.\App\Models\SurveyAsset::where('kind', 'photo')->count().
            ' | en disco: '.\App\Models\SurveyAsset::where('kind', 'photo')->get()->filter(fn ($a) => Storage::disk('local')->exists($a->file_path))->count());

        return 0;
    }
}
