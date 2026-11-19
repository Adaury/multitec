<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Project;
use App\Models\PurchaseInvoice;
use App\Models\Supplier;
use App\Support\ApiException;
use App\Support\V;
use Illuminate\Http\Request;

class PurchaseInvoiceController extends Controller
{
    private function find(int $id): PurchaseInvoice
    {
        $p = PurchaseInvoice::with('supplier')->find($id);
        if (! $p) {
            throw new ApiException(404, 'Factura de compra no encontrada');
        }

        return $p;
    }

    private function date($v, string $field, bool $required = false): ?string
    {
        if ($v === null || $v === '') {
            if ($required) {
                throw new ApiException(422, "$field es obligatoria");
            }

            return null;
        }
        if (! is_string($v) || ! preg_match('/^\d{4}-\d{2}-\d{2}$/', $v) || ! strtotime($v)) {
            throw new ApiException(422, "$field inválida (usa AAAA-MM-DD)");
        }

        return $v;
    }

    /** Valida y normaliza el cuerpo (mismas reglas del instructivo del 606 que la versión original). */
    private function data(Request $r, ?int $excludeId = null): array
    {
        $ncf = strtoupper(trim((string) V::text($r->input('ncf'), 19, 'ncf', true)));
        if (mb_strlen($ncf) < 11) {
            throw new ApiException(422, 'El NCF debe tener al menos 11 caracteres');
        }
        $mod = $r->input('ncf_modified');
        $mod = $mod ? strtoupper(trim((string) V::text($mod, 19, 'ncf_modified'))) : null;
        $expense = (string) $r->input('expense_type', '09');
        $payType = (string) $r->input('payment_type', '04');
        if (! preg_match('/^(0[1-9]|1[01])$/', $expense)) {
            throw new ApiException(422, 'Tipo de gasto inválido, debe ser 01-11');
        }
        if (! preg_match('/^0[1-7]$/', $payType)) {
            throw new ApiException(422, 'Forma de pago inválida, debe ser 01-07');
        }
        $isrType = $r->input('isr_retention_type');
        $isrType = ($isrType === null || $isrType === '') ? null : (string) $isrType;
        if ($isrType !== null && ! preg_match('/^0[1-9]$/', $isrType)) {
            throw new ApiException(422, 'Tipo de retención de ISR inválido, debe ser 01-09');
        }
        $services = V::num($r->input('services_amount', 0), 'services_amount', 0.0) ?? 0.0;
        $goods = V::num($r->input('goods_amount', 0), 'goods_amount', 0.0) ?? 0.0;
        $itbis = V::num($r->input('itbis_invoiced', 0), 'itbis_invoiced', 0.0) ?? 0.0;
        $itbisW = V::num($r->input('itbis_withheld', 0), 'itbis_withheld', 0.0) ?? 0.0;
        $isrW = V::num($r->input('isr_withheld', 0), 'isr_withheld', 0.0) ?? 0.0;
        $payDate = $this->date($r->input('payment_date'), 'La fecha de pago');
        if ($isrW > 0 && ! $isrType) {
            throw new ApiException(422, 'Indica el tipo de retención de ISR (01-09): la DGII lo exige cuando hay retención de renta');
        }
        if (($isrW > 0 || $itbisW > 0) && $payDate === null) {
            throw new ApiException(422, 'Indica la fecha de pago: la DGII la exige cuando hay ITBIS o renta retenidos');
        }
        if ($isrW == 0) {
            $isrType = null;
        }
        $supplierId = V::int($r->input('supplier_id'), 'supplier_id');
        $projectId = V::int($r->input('project_id'), 'project_id');
        if (! $supplierId || ! Supplier::whereKey($supplierId)->exists()) {
            throw new ApiException(404, 'Proveedor no encontrado');
        }
        if ($projectId !== null && ! Project::whereKey($projectId)->exists()) {
            throw new ApiException(404, 'Proyecto no encontrado');
        }
        if (PurchaseInvoice::where('supplier_id', $supplierId)->where('ncf', $ncf)
            ->when($excludeId, fn ($q) => $q->where('id', '!=', $excludeId))->exists()) {
            throw new ApiException(409, 'Ya existe una factura de este proveedor con ese NCF');
        }

        return [
            'supplier_id' => $supplierId, 'project_id' => $projectId, 'ncf' => $ncf, 'ncf_modified' => $mod,
            'invoice_date' => $this->date($r->input('invoice_date'), 'La fecha de la factura', true), 'payment_date' => $payDate,
            'expense_type' => $expense, 'payment_type' => $payType, 'services_amount' => $services, 'goods_amount' => $goods,
            'itbis_invoiced' => $itbis, 'itbis_withheld' => $itbisW, 'isr_withheld' => $isrW, 'isr_retention_type' => $isrType,
            'notes' => V::text($r->input('notes'), 5000, 'notes'),
        ];
    }

    public function index(Request $r)
    {
        $q = PurchaseInvoice::with('supplier');
        if ($r->filled('supplier_id')) {
            $q->where('supplier_id', (int) $r->query('supplier_id'));
        }

        return $q->orderByDesc('invoice_date')->orderByDesc('id')->get()->map(fn ($p) => $p->toOut())->values();
    }

    public function store(Request $r)
    {
        $p = PurchaseInvoice::create($this->data($r) + ['created_by' => $r->attributes->get('user')->id, 'created_at' => now()]);

        return response()->json($this->find($p->id)->toOut(), 201);
    }

    public function show(int $invoice_id)
    {
        return $this->find($invoice_id)->toOut();
    }

    public function update(Request $r, int $invoice_id)
    {
        $p = $this->find($invoice_id);
        $p->update($this->data($r, $invoice_id) + ['updated_at' => now()]);

        return $this->find($invoice_id)->toOut();
    }

    public function destroy(int $invoice_id)
    {
        $this->find($invoice_id)->delete();

        return response()->noContent();
    }
}
