<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Client;
use App\Models\Invoice;
use App\Models\InvoiceHistory;
use App\Models\PreInvoice;
use App\Models\Project;
use App\Models\Quote;
use App\Support\ApiException;
use App\Support\Audit;
use App\Support\Codes;
use App\Support\Csv;
use App\Support\DocItems;
use App\Support\Money;
use App\Support\Ncf;
use App\Support\QuoteApproval;
use App\Support\V;
use Illuminate\Database\QueryException;
use Illuminate\Http\Request;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;

class InvoiceController extends Controller
{
    private function pre(int $id): PreInvoice
    {
        $p = PreInvoice::with('items')->find($id);
        if (! $p) {
            throw new ApiException(404, 'Prefactura no encontrada');
        }

        return $p;
    }

    private function invoice(int $id): Invoice
    {
        $i = Invoice::with('items')->find($id);
        if (! $i) {
            throw new ApiException(404, 'Factura no encontrada');
        }

        return $i;
    }

    private function validDate($v, string $field): ?string
    {
        if ($v === null || $v === '') {
            return null;
        }
        if (! is_string($v) || ! preg_match('/^\d{4}-\d{2}-\d{2}$/', $v) || ! strtotime($v)) {
            throw new ApiException(422, "$field inválida (usa AAAA-MM-DD)");
        }

        return $v;
    }

    // ---- prefacturas ----------------------------------------------------------------

    public function listPre(int $project_id)
    {
        return PreInvoice::with('items')->where('project_id', $project_id)->orderByDesc('created_at')->orderByDesc('id')
            ->get()->map(fn ($p) => $p->toOut())->values();
    }

    public function storePre(Request $r, int $project_id)
    {
        if (! Project::whereKey($project_id)->exists()) {
            throw new ApiException(404, 'Proyecto no encontrado');
        }
        $items = DocItems::fromRequest($r);
        $notes = V::text($r->input('notes'), 5000, 'notes');
        $pre = DB::transaction(function () use ($project_id, $items, $notes, $r) {
            $p = PreInvoice::create([
                'code' => Codes::next('PFC'), 'project_id' => $project_id, 'notes' => $notes,
                'created_by' => $r->attributes->get('user')->id, 'created_at' => now(),
            ]);
            foreach ($items as $it) {
                $p->items()->create($it + ['subtotal' => Money::fromCents(Money::line($it['quantity'], $it['unit_price']))]);
            }
            [$sub, $tax, $total] = Money::totals($items);
            $p->update(['subtotal' => $sub, 'itbis' => $tax, 'total' => $total]);

            return $p;
        });

        return response()->json($this->pre($pre->id)->toOut(), 201);
    }

    public function generatePre(Request $r, int $quote_id)
    {
        $q = Quote::with('items')->find($quote_id);
        if (! $q) {
            throw new ApiException(404, 'Cotización no encontrada');
        }
        if ($q->status !== 'aprobada') {
            throw new ApiException(400, 'Solo se puede generar prefactura de una cotización aprobada');
        }
        $pre = DB::transaction(fn () => QuoteApproval::preInvoice($q, $r->attributes->get('user')->id));

        return response()->json($this->pre($pre->id)->toOut(), 201);
    }

    public function showPre(int $pre_invoice_id)
    {
        return $this->pre($pre_invoice_id)->toOut();
    }

    // ---- facturas ------------------------------------------------------------------

    /** §13-14: «el administrador decide convertir a factura» — único endpoint solo admin. */
    public function convert(Request $r, int $pre_invoice_id)
    {
        $user = $r->attributes->get('user');
        $type = $r->input('ncf_type');
        if ($type !== null && ! in_array($type, ['B01', 'B02', 'B14', 'B15'], true)) {
            throw new ApiException(422, 'ncf_type debe ser B01, B02, B14 o B15');
        }
        $pre = $this->pre($pre_invoice_id);
        if ($pre->status === 'facturada') {
            throw new ApiException(400, 'Esta prefactura ya fue facturada');
        }
        $client = Client::find(Project::find($pre->project_id)->client_id);
        $type = $type ?: Ncf::defaultType($client);

        try {
            $invoice = DB::transaction(function () use ($pre, $type, $user) {
                // Bloquea la prefactura: dos conversiones simultáneas no consumen dos NCF.
                $locked = PreInvoice::lockForUpdate()->find($pre->id);
                if ($locked->status === 'facturada') {
                    throw new ApiException(400, 'Esta prefactura ya fue facturada');
                }
                $ncf = Ncf::assign($type);
                $inv = Invoice::create([
                    'code' => Codes::next('FAC'), 'project_id' => $pre->project_id, 'pre_invoice_id' => $pre->id,
                    'ncf' => $ncf, 'ncf_type' => $type, 'subtotal' => $pre->subtotal, 'itbis' => $pre->itbis,
                    'total' => $pre->total, 'created_by' => $user->id, 'created_at' => now(),
                ]);
                foreach ($pre->items as $i) {
                    $inv->items()->create([
                        'product_id' => $i->product_id, 'description' => $i->description, 'quantity' => $i->quantity,
                        'unit_price' => $i->unit_price, 'subtotal' => $i->subtotal, 'note' => $i->note,
                    ]);
                }
                $locked->update(['status' => 'facturada', 'updated_at' => now()]);
                InvoiceHistory::add($inv->id, 'creada', "Convertida desde prefactura {$pre->code}");

                return $inv;
            });
        } catch (QueryException $e) {
            if (str_contains($e->getMessage(), 'Duplicate entry')) {
                throw new ApiException(400, "El NCF ya fue usado. Probablemente hay dos secuencias $type activas con rangos superpuestos — revisa las secuencias NCF en Configuración > NCF y desactiva la duplicada.");
            }
            throw $e;
        }

        return response()->json($this->invoice($invoice->id)->toOut(), 201);
    }

    public function listByProject(int $project_id)
    {
        return Invoice::with('items')->where('project_id', $project_id)->orderByDesc('created_at')->orderByDesc('id')
            ->get()->map(fn ($i) => $i->toOut())->values();
    }

    public function export()
    {
        $rows = [];
        foreach (Invoice::with('project.client')->orderByDesc('created_at')->orderByDesc('id')->get() as $i) {
            $rows[] = [
                $i->code, $i->ncf ?: '', $i->project->code, $i->project->client->name, (float) $i->subtotal, (float) $i->itbis,
                (float) $i->total, Carbon::parse($i->created_at)->format('Y-m-d'),
            ];
        }

        return Csv::response(Csv::build(['Código', 'NCF', 'Proyecto', 'Cliente', 'Subtotal', 'ITBIS', 'Total', 'Fecha'], $rows), 'facturas.csv');
    }

    public function show(int $invoice_id)
    {
        return $this->invoice($invoice_id)->toOut();
    }

    public function history(int $invoice_id)
    {
        $this->invoice($invoice_id);

        return InvoiceHistory::where('invoice_id', $invoice_id)->orderBy('created_at')->orderBy('id')->get()->map(fn ($h) => $h->toOut())->values();
    }

    /** Forma de pago y retenciones de una factura emitida: alimentan las columnas del 607. */
    public function payment(Request $r, int $invoice_id)
    {
        $inv = $this->invoice($invoice_id);
        $method = $r->input('payment_method');
        if ($method !== null && ! in_array($method, Invoice::PAYMENT_METHODS, true)) {
            throw new ApiException(422, 'Forma de pago inválida');
        }
        $itbisW = V::num($r->input('itbis_withheld', 0), 'itbis_withheld', 0.0) ?? 0.0;
        $isrW = V::num($r->input('isr_withheld', 0), 'isr_withheld', 0.0) ?? 0.0;
        $retDate = $this->validDate($r->input('retention_date'), 'La fecha de retención');
        if ($itbisW > (float) $inv->itbis + 0.005) {
            throw new ApiException(400, 'El ITBIS retenido no puede ser mayor que el ITBIS de la factura');
        }
        if ($isrW > (float) $inv->subtotal + 0.005) {
            throw new ApiException(400, 'La retención de renta no puede ser mayor que el subtotal');
        }
        $hasRetention = $itbisW > 0 || $isrW > 0;
        if ($hasRetention && $retDate === null) {
            throw new ApiException(400, 'Indica la fecha de la retención');
        }
        $data = [
            'payment_method' => $method, 'itbis_withheld' => $itbisW, 'isr_withheld' => $isrW,
            'retention_date' => $hasRetention ? $retDate : null,
        ];
        // De contado, transferencia, tarjeta…: ya está cobrada. A crédito sigue por cobrar hasta que alguien la marque.
        if ($method !== null && $method !== 'credito' && $inv->paid_at === null && $inv->voided_at === null) {
            $data['paid_at'] = Ncf::today();
        }
        DB::transaction(function () use ($inv, $data, $method, $itbisW, $isrW) {
            $inv->update($data);
            InvoiceHistory::add($inv->id, 'pago actualizado', sprintf(
                'Forma de pago: %s; ITBIS retenido %.2f; renta retenida %.2f', $method ?: 'sin definir', $itbisW, $isrW));
        });

        return $this->invoice($invoice_id)->toOut();
    }

    /** Marca como cobrada (por defecto hoy) o devuelve a «por cobrar». */
    public function paid(Request $r, int $invoice_id)
    {
        $inv = $this->invoice($invoice_id);
        if ($inv->voided_at !== null) {
            throw new ApiException(400, 'Una factura anulada no se cobra');
        }
        $paid = filter_var($r->input('paid', true), FILTER_VALIDATE_BOOLEAN);
        if ($paid) {
            $date = $this->validDate($r->input('paid_at'), 'La fecha de cobro') ?? Ncf::today();
            if ($date > Ncf::today()) {
                throw new ApiException(400, 'La fecha de cobro no puede ser futura');
            }
            $inv->update(['paid_at' => $date]);
            $note = 'Cobrada el '.Carbon::parse($date)->format('d/m/Y');
        } else {
            $inv->update(['paid_at' => null]);
            $note = 'Vuelve a por cobrar';
        }
        InvoiceHistory::add($inv->id, 'cobro', $note);

        return $this->invoice($invoice_id)->toOut();
    }

    /** Anula una factura (solo admin): el NCF queda consumido, se reporta en el 608 y deja de contar como venta. */
    public function void(Request $r, int $invoice_id)
    {
        $user = $r->attributes->get('user');
        $code = (string) $r->input('reason_code', '');
        if (! isset(Invoice::VOID_REASONS[$code])) {
            throw new ApiException(422, 'reason_code debe ser un tipo de anulación entre 01 y 10');
        }
        $note = V::text($r->input('note'), 300, 'note');
        DB::transaction(function () use ($invoice_id, $code, $note, $user, $r) {
            $inv = Invoice::lockForUpdate()->find($invoice_id);
            if (! $inv) {
                throw new ApiException(404, 'Factura no encontrada');
            }
            if ($inv->voided_at !== null) {
                throw new ApiException(400, 'Esta factura ya está anulada');
            }
            $inv->update(['voided_at' => Carbon::now(), 'void_reason' => $code, 'voided_by' => $user->id]);
            $text = "$code - ".Invoice::VOID_REASONS[$code].($note ? ": $note" : '');
            InvoiceHistory::add($inv->id, 'anulada', $text);
            Audit::log('invoice_voided', $user, entity: 'invoice', entityId: $inv->id,
                detail: ['factura' => $inv->code, 'ncf' => $inv->ncf, 'motivo' => $code], request: $r);
        });

        return $this->invoice($invoice_id)->toOut();
    }

    public function pdf(Request $r, int $invoice_id)
    {
        $variant = (string) $r->query('variant', 'detallada');
        if (! in_array($variant, ['detallada', 'global'], true)) {
            throw new ApiException(422, 'variant debe ser detallada o global');
        }
        $inv = $this->invoice($invoice_id);

        return response(\App\Support\PdfBuilder::invoice($inv, $variant), 200, [
            'Content-Type' => 'application/pdf',
            'Content-Disposition' => 'attachment; filename="'.$inv->code.($variant === 'global' ? '-global' : '').'.pdf"',
        ]);
    }

    public function margin(int $invoice_id)
    {
        return \App\Support\Margin::compute($this->invoice($invoice_id)->items, 'facturado');
    }

    /** (reservado) */
    public function notMigrated()
    {
        throw new ApiException(501, 'Esta función (PDF o margen de la factura) aún no está disponible en esta versión.');
    }
}
