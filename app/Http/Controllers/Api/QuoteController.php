<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Material;
use App\Models\Product;
use App\Models\Project;
use App\Models\Quote;
use App\Models\QuoteHistory;
use App\Support\ApiException;
use App\Support\Codes;
use App\Support\DocItems;
use App\Support\Money;
use App\Support\Notify;
use App\Support\QuoteApproval;
use App\Support\V;
use Illuminate\Http\Request;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;

class QuoteController extends Controller
{
    private function find(int $id): Quote
    {
        $q = Quote::with('items')->find($id);
        if (! $q) {
            throw new ApiException(404, 'Cotización no encontrada');
        }

        return $q;
    }

    /** Auto-archiva las pendientes con más de N días sin decisión (al listar/consultar, sin necesitar un cron). */
    private function archiveStale(?int $projectId = null): void
    {
        $days = (int) config('app.quote_stale_days', 7);
        $q = Quote::where('status', 'pendiente')->where('created_at', '<=', Carbon::now()->subDays($days));
        if ($projectId) {
            $q->where('project_id', $projectId);
        }
        foreach ($q->get() as $quote) {
            $quote->update(['status' => 'archivada']);
            QuoteHistory::add($quote->id, 'archivada', "Auto-archivada tras $days días sin aprobación.");
        }
    }

    /** Recalcula subtotal, ITBIS y total desde las líneas de la cotización. */
    private function recalc(Quote $q): void
    {
        $q->load('items');
        [$sub, $tax, $total] = Money::totals($q->items);
        $q->update(['subtotal' => $sub, 'itbis' => $tax, 'total' => $total]);
    }

    private function fillItems(Quote $q, array $items): void
    {
        $q->items()->delete();
        foreach ($items as $it) {
            $q->items()->create($it + ['subtotal' => Money::fromCents(Money::line($it['quantity'], $it['unit_price']))]);
        }
        $this->recalc($q);
    }

    // ---- consulta ------------------------------------------------------------

    public function indexByProject(int $project_id)
    {
        $this->archiveStale($project_id);

        return Quote::with('items')->where('project_id', $project_id)->orderByDesc('created_at')->orderByDesc('id')
            ->get()->map(fn ($q) => $q->toOut())->values();
    }

    public function index(Request $r)
    {
        $this->archiveStale();
        $q = Quote::with('items');
        if ($r->filled('status_filter')) {
            $q->where('status', $r->query('status_filter'));
        }

        return $q->orderByDesc('created_at')->orderByDesc('id')->get()->map(fn ($x) => $x->toOut())->values();
    }

    public function show(int $quote_id)
    {
        $this->archiveStale();

        return $this->find($quote_id)->toOut();
    }

    public function history(int $quote_id)
    {
        $this->find($quote_id);

        return QuoteHistory::where('quote_id', $quote_id)->orderBy('created_at')->orderBy('id')->get()->map(fn ($h) => $h->toOut())->values();
    }

    public function purchaseListPreview(int $quote_id)
    {
        $q = $this->find($quote_id);

        return [
            'quote_id' => $q->id,
            'already_generated' => Material::where('source_quote_id', $q->id)->exists(),
            'items' => QuoteApproval::materialRows($q),
        ];
    }

    // ---- creación y edición -----------------------------------------------------

    public function store(Request $r, int $project_id)
    {
        if (! Project::whereKey($project_id)->exists()) {
            throw new ApiException(404, 'Proyecto no encontrado');
        }
        $items = DocItems::fromRequest($r);
        $notes = V::text($r->input('notes'), 5000, 'notes');
        $quote = DB::transaction(function () use ($project_id, $items, $notes, $r) {
            $q = Quote::create([
                'code' => Codes::next('COT'), 'project_id' => $project_id, 'notes' => $notes,
                'created_by' => $r->attributes->get('user')->id, 'created_at' => now(),
            ]);
            $this->fillItems($q, $items);
            QuoteHistory::add($q->id, 'creada');

            return $q;
        });

        Notify::quotePending($quote);

        return response()->json($this->find($quote->id)->toOut(), 201);
    }

    public function update(Request $r, int $quote_id)
    {
        $q = $this->find($quote_id);
        if ($q->status !== 'pendiente') {
            throw new ApiException(400, 'Solo se pueden editar cotizaciones pendientes');
        }
        $items = DocItems::fromRequest($r);
        $notes = V::text($r->input('notes'), 5000, 'notes');
        DB::transaction(function () use ($q, $items, $notes) {
            $q->update(['notes' => $notes, 'stale_notified' => false, 'updated_at' => now()]);
            $this->fillItems($q, $items);
            QuoteHistory::add($q->id, 'editada');
        });

        return $this->find($quote_id)->toOut();
    }

    // ---- decisiones ----------------------------------------------------------------

    public function approve(Request $r, int $quote_id)
    {
        $user = $r->attributes->get('user');
        DB::transaction(function () use ($quote_id, $user) {
            // Bloquea la fila: dos aprobaciones simultáneas no duplican materiales ni prefactura.
            $q = Quote::with('items')->lockForUpdate()->find($quote_id);
            if (! $q) {
                throw new ApiException(404, 'Cotización no encontrada');
            }
            if (! in_array($q->status, ['pendiente', 'archivada'], true)) {
                throw new ApiException(400, "No se puede aprobar una cotización '{$q->status}'");
            }
            QuoteApproval::approve($q, $user->id);
        });

        return $this->find($quote_id)->toOut();
    }

    public function reject(Request $r, int $quote_id)
    {
        $q = $this->find($quote_id);
        if (! in_array($q->status, ['pendiente', 'archivada'], true)) {
            throw new ApiException(400, "No se puede rechazar una cotización '{$q->status}'");
        }
        $reason = V::text($r->input('reason'), 2000, 'reason', true);
        DB::transaction(function () use ($q, $reason) {
            $q->update(['status' => 'no_aprobada', 'decided_at' => Carbon::now(), 'updated_at' => now()]);
            QuoteHistory::add($q->id, 'rechazada', $reason);
        });

        return $this->find($quote_id)->toOut();
    }

    public function archive(int $quote_id)
    {
        $q = $this->find($quote_id);
        if ($q->status !== 'pendiente') {
            throw new ApiException(400, "No se puede archivar una cotización '{$q->status}'");
        }
        $q->update(['status' => 'archivada', 'updated_at' => now()]);
        QuoteHistory::add($q->id, 'archivada', 'Archivada manualmente');

        return $this->find($quote_id)->toOut();
    }

    public function reactivate(int $quote_id)
    {
        $q = $this->find($quote_id);
        if ($q->status !== 'archivada') {
            throw new ApiException(400, 'Solo se pueden reactivar cotizaciones archivadas');
        }
        $q->update(['status' => 'pendiente', 'decided_at' => null, 'updated_at' => now()]);
        QuoteHistory::add($q->id, 'reactivada');

        return $this->find($quote_id)->toOut();
    }

    // ---- actualizar precios y nuevas versiones ---------------------------------------

    /** Líneas cuyo precio ya no coincide con el del catálogo (las de texto libre no se tocan). @return array<int,array{0:\App\Models\QuoteItem,1:float}> */
    private function priceChanges(Quote $q): array
    {
        $ids = $q->items->pluck('product_id')->filter()->unique()->all();
        $prices = $ids ? Product::whereIn('id', $ids)->pluck('price', 'id')->map(fn ($p) => (float) $p)->all() : [];
        $out = [];
        foreach ($q->items as $item) {
            $new = $item->product_id !== null ? ($prices[$item->product_id] ?? null) : null;
            if ($new !== null && $new > 0 && abs($new - (float) $item->unit_price) > 0.005) {
                $out[] = [$item, $new];
            }
        }

        return $out;
    }

    private function changeRows(array $changes): array
    {
        return array_map(fn ($c) => [
            'item_id' => $c[0]->id, 'description' => $c[0]->description, 'quantity' => (float) $c[0]->quantity,
            'old_price' => (float) $c[0]->unit_price, 'new_price' => $c[1],
        ], $changes);
    }

    private function totalWith(Quote $q, array $overrides): float
    {
        $lines = $q->items->map(fn ($i) => ['quantity' => $i->quantity, 'unit_price' => $overrides[$i->id] ?? $i->unit_price]);

        return Money::totals($lines)[2];
    }

    public function repricePreview(int $quote_id)
    {
        $q = $this->find($quote_id);
        $changes = $this->priceChanges($q);
        $over = [];
        foreach ($changes as [$item, $new]) {
            $over[$item->id] = $new;
        }

        return ['changes' => $this->changeRows($changes), 'total_old' => (float) $q->total, 'total_new' => $this->totalWith($q, $over)];
    }

    /** Copia como cotización nueva (pendiente), con otros precios si se piden: lo que el cliente ya vio no se toca. */
    private function copyAsNewVersion(Quote $q, int $userId, array $prices): Quote
    {
        $new = Quote::create([
            'code' => Codes::next('COT'), 'project_id' => $q->project_id, 'source_budget_id' => $q->source_budget_id,
            'notes' => $q->notes, 'created_by' => $userId, 'created_at' => now(),
        ]);
        foreach ($q->items as $i) {
            $price = $prices[$i->id] ?? (float) $i->unit_price;
            $new->items()->create([
                'product_id' => $i->product_id, 'description' => $i->description, 'quantity' => $i->quantity,
                'unit_price' => $price, 'subtotal' => Money::fromCents(Money::line($i->quantity, $price)), 'note' => $i->note,
            ]);
        }
        $this->recalc($new);
        QuoteHistory::add($new->id, 'creada', "Nueva versión de {$q->code}");
        QuoteHistory::add($q->id, 'nueva_version', "Se creó {$new->code}");

        return $new;
    }

    public function reprice(Request $r, int $quote_id)
    {
        $user = $r->attributes->get('user');
        $q = $this->find($quote_id);
        $changes = $this->priceChanges($q);
        if (! $changes) {
            throw new ApiException(400, 'Los precios de esta cotización ya son los del catálogo');
        }
        $rows = $this->changeRows($changes);
        $newPrices = [];
        foreach ($changes as [$item, $new]) {
            $newPrices[$item->id] = $new;
        }

        $result = DB::transaction(function () use ($q, $changes, $newPrices, $user) {
            if ($q->status === 'pendiente') {
                foreach ($changes as [$item, $new]) {
                    $item->update(['unit_price' => $new, 'subtotal' => Money::fromCents(Money::line($item->quantity, $new))]);
                }
                $this->recalc($q);
                $q->update(['stale_notified' => false, 'updated_at' => now()]);
                QuoteHistory::add($q->id, 'repreciada', count($changes).' precio(s) actualizado(s)');

                return [$q, false];
            }
            $new = $this->copyAsNewVersion($q, $user->id, $newPrices);
            QuoteHistory::add($new->id, 'repreciada', count($changes).' precio(s) actualizado(s)');

            return [$new, true];
        });

        return ['quote' => $this->find($result[0]->id)->toOut(), 'created_new' => $result[1], 'changes' => $rows];
    }

    public function newVersion(Request $r, int $quote_id)
    {
        $q = $this->find($quote_id);
        $new = DB::transaction(fn () => $this->copyAsNewVersion($q, $r->attributes->get('user')->id, []));

        return response()->json($this->find($new->id)->toOut(), 201);
    }

    private const PDF_SUFFIX = ['detallada' => '', 'ejecutiva' => '-ejecutiva', 'global' => '-monto-general'];

    /** PDF en el formato pedido: detallada, ejecutiva (por categoría) o global; con anexo de fotos none|marked|all. */
    public function pdf(Request $r, int $quote_id)
    {
        $variant = (string) $r->query('variant', 'detallada');
        $photos = (string) $r->query('photos', 'none');
        if (! isset(self::PDF_SUFFIX[$variant])) {
            throw new ApiException(422, 'variant debe ser detallada, ejecutiva o global');
        }
        if (! in_array($photos, ['none', 'marked', 'all'], true)) {
            throw new ApiException(422, 'photos debe ser none, marked o all');
        }
        $q = $this->find($quote_id);
        $name = $q->code.self::PDF_SUFFIX[$variant].($photos !== 'none' ? '-fotos' : '').'.pdf';

        return response(\App\Support\PdfBuilder::quote($q, $variant, $photos), 200, [
            'Content-Type' => 'application/pdf', 'Content-Disposition' => 'attachment; filename="'.$name.'"',
        ]);
    }

    public function margin(int $quote_id)
    {
        return \App\Support\Margin::compute($this->find($quote_id)->items, 'cotizado');
    }

    /** Correo y planillas Excel/CSV: aún no migrados a esta versión. */
    public function notMigrated()
    {
        throw new ApiException(501, 'Esta función (PDF, correo, planillas o margen de la cotización) aún no está disponible en esta versión.');
    }
}
