<?php

namespace App\Support;

use App\Models\Budget;
use App\Models\Engineering;
use App\Models\LogEntry;
use App\Models\Material;
use App\Models\Project;
use App\Models\Quote;
use App\Models\Survey;
use App\Models\Ticket;

/**
 * Resumen legible del expediente de un proyecto, para darlo a la IA como contexto. Con $includeMoney = false se omiten
 * presupuestos y cotizaciones: el técnico no tiene acceso a dinero y no debe poder sacarlo preguntándole a la IA.
 */
class ProjectContext
{
    public static function build(Project $p, bool $includeMoney = true): string
    {
        $p->loadMissing('client');
        $c = $p->client;
        $lines = [
            "Proyecto {$p->code} — estado: {$p->status}",
            'Cliente: '.($c?->name ?? '-').($c?->company ? " ({$c->company})" : ''),
            'Descripción: '.($p->description ?: '(sin descripción)'),
        ];
        if ($s = Survey::where('project_id', $p->id)->first()) {
            $lines[] = "\n== Levantamiento ==";
            $lines[] = 'Notas: '.($s->notes ?: '-');
            $lines[] = 'Medidas: '.($s->measurements ?: '-');
            $lines[] = 'Observaciones: '.($s->observations ?: '-');
            if ($s->ai_summary) {
                $lines[] = "Resumen IA previo: {$s->ai_summary}";
            }
            if ($points = SurveyPoints::context(SurveyPoints::markerCounts($p->id))) {
                $lines[] = $points;
            }
        }
        $e = Engineering::where('project_id', $p->id)->first();
        if ($e && ($e->recommended_equipment || $e->distribution || $e->conduits || $e->wiring || $e->technical_design)) {
            $lines[] = "\n== Ingeniería ==";
            $lines[] = 'Equipos recomendados: '.($e->recommended_equipment ?: '-');
            $lines[] = 'Distribución: '.($e->distribution ?: '-');
            $lines[] = 'Canalizaciones: '.($e->conduits ?: '-');
            $lines[] = 'Cableado: '.($e->wiring ?: '-');
            $lines[] = 'Diseño técnico: '.($e->technical_design ?: '-');
        }
        if ($includeMoney) {
            $budgets = Budget::where('project_id', $p->id)->get();
            if ($budgets->isNotEmpty()) {
                $lines[] = "\n== Presupuestos ==";
                foreach ($budgets as $b) {
                    $lines[] = "{$b->code}: total RD$ ".number_format((float) $b->total, 2, '.', '');
                }
            }
            $quotes = Quote::where('project_id', $p->id)->get();
            if ($quotes->isNotEmpty()) {
                $lines[] = "\n== Cotizaciones ==";
                foreach ($quotes as $q) {
                    $lines[] = "{$q->code}: estado {$q->status}, total RD$ ".number_format((float) $q->total, 2, '.', '');
                }
            }
        }
        $materials = Material::where('project_id', $p->id)->get();
        if ($materials->isNotEmpty()) {
            $lines[] = "\n== Materiales ==";
            foreach ($materials as $m) {
                $lines[] = rtrim(rtrim(number_format((float) $m->quantity, 4, '.', ''), '0'), '.')." x {$m->description} — {$m->status}";
            }
        }
        $log = LogEntry::where('project_id', $p->id)->orderBy('entry_date')->orderBy('id')->get();
        if ($log->isNotEmpty()) {
            $lines[] = "\n== Bitácora ==";
            foreach ($log as $l) {
                $lines[] = $l->entry_date?->format('Y-m-d').": {$l->comment}";
            }
        }
        $tickets = Ticket::where('project_id', $p->id)->get();
        if ($tickets->isNotEmpty()) {
            $lines[] = "\n== Tickets de soporte ==";
            foreach ($tickets as $t) {
                $lines[] = "{$t->code} ({$t->status}): {$t->problem}".($t->solution ? " → {$t->solution}" : '');
            }
        }

        return implode("\n", $lines);
    }
}
