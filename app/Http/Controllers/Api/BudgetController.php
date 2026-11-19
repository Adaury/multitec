<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Budget;
use App\Models\Project;
use App\Models\Quote;
use App\Models\QuoteHistory;
use App\Support\ApiException;
use App\Support\Codes;
use App\Support\DocItems;
use App\Support\Money;
use App\Support\V;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class BudgetController extends Controller
{
    private function find(int $id): Budget
    {
        $b = Budget::with('items')->find($id);
        if (! $b) {
            throw new ApiException(404, 'Presupuesto no encontrado');
        }

        return $b;
    }

    private function fillItems(Budget $b, array $items): void
    {
        $b->items()->delete();
        foreach ($items as $it) {
            $b->items()->create($it);
        }
        $b->load('items');
        $b->update(['total' => Money::sum($b->items), 'updated_at' => now()]);
    }

    public function indexByProject(int $project_id)
    {
        return Budget::with('items')->where('project_id', $project_id)->orderByDesc('created_at')->orderByDesc('id')
            ->get()->map(fn ($b) => $b->toOut())->values();
    }

    public function index()
    {
        return Budget::with('items')->orderByDesc('created_at')->orderByDesc('id')->get()->map(fn ($b) => $b->toOut())->values();
    }

    public function store(Request $r, int $project_id)
    {
        if (! Project::whereKey($project_id)->exists()) {
            throw new ApiException(404, 'Proyecto no encontrado');
        }
        $items = DocItems::fromRequest($r);
        $notes = V::text($r->input('notes'), 5000, 'notes');
        $budget = DB::transaction(function () use ($project_id, $items, $notes, $r) {
            $b = Budget::create([
                'code' => Codes::next('PRE'), 'project_id' => $project_id, 'notes' => $notes,
                'created_by' => $r->attributes->get('user')->id, 'created_at' => now(),
            ]);
            $this->fillItems($b, $items);

            return $b;
        });

        return response()->json($this->find($budget->id)->toOut(), 201);
    }

    public function show(int $budget_id)
    {
        return $this->find($budget_id)->toOut();
    }

    public function update(Request $r, int $budget_id)
    {
        $b = $this->find($budget_id);
        $items = DocItems::fromRequest($r);
        $notes = V::text($r->input('notes'), 5000, 'notes');
        DB::transaction(function () use ($b, $items, $notes) {
            $b->update(['notes' => $notes]);
            $this->fillItems($b, $items);
        });

        return $this->find($budget_id)->toOut();
    }

    public function pdf(int $budget_id)
    {
        $b = $this->find($budget_id);

        return response(\App\Support\PdfBuilder::budget($b), 200, [
            'Content-Type' => 'application/pdf', 'Content-Disposition' => 'attachment; filename="'.$b->code.'-resumen.pdf"',
        ]);
    }

    /** Convierte el presupuesto en cotización: copia las líneas y calcula el ITBIS. */
    public function convertToQuote(Request $r, int $budget_id)
    {
        $b = $this->find($budget_id);
        $quote = DB::transaction(function () use ($b, $r) {
            $q = Quote::create([
                'code' => Codes::next('COT'), 'project_id' => $b->project_id, 'source_budget_id' => $b->id,
                'notes' => $b->notes, 'created_by' => $r->attributes->get('user')->id, 'created_at' => now(),
            ]);
            foreach ($b->items as $i) {
                $q->items()->create([
                    'product_id' => $i->product_id, 'description' => $i->description, 'quantity' => $i->quantity,
                    'unit_price' => $i->unit_price, 'subtotal' => Money::fromCents(Money::line($i->quantity, $i->unit_price)),
                    'note' => $i->note,
                ]);
            }
            [$sub, $tax, $total] = Money::totals($b->items);
            $q->update(['subtotal' => $sub, 'itbis' => $tax, 'total' => $total]);
            QuoteHistory::add($q->id, 'creada', "Generada desde presupuesto {$b->code}");

            return $q;
        });

        \App\Support\Notify::quotePending($quote);

        return response()->json(Quote::with('items')->find($quote->id)->toOut(), 201);
    }
}
