<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class PurchaseInvoice extends Model
{
    use BelongsToCompany;

    protected $guarded = ['id', 'company_id'];
    protected $casts = [
        'invoice_date' => 'date:Y-m-d', 'payment_date' => 'date:Y-m-d', 'services_amount' => 'float', 'goods_amount' => 'float',
        'itbis_invoiced' => 'float', 'itbis_withheld' => 'float', 'isr_withheld' => 'float',
        'created_at' => 'datetime', 'updated_at' => 'datetime',
    ];

    public function supplier(): BelongsTo
    {
        return $this->belongsTo(Supplier::class);
    }

    public function toOut(): array
    {
        return [
            'supplier_id' => $this->supplier_id, 'project_id' => $this->project_id, 'ncf' => $this->ncf,
            'ncf_modified' => $this->ncf_modified, 'invoice_date' => $this->invoice_date?->format('Y-m-d'),
            'payment_date' => $this->payment_date?->format('Y-m-d'), 'expense_type' => $this->expense_type,
            'payment_type' => $this->payment_type, 'services_amount' => (float) $this->services_amount,
            'goods_amount' => (float) $this->goods_amount, 'itbis_invoiced' => (float) $this->itbis_invoiced,
            'itbis_withheld' => (float) $this->itbis_withheld, 'isr_withheld' => (float) $this->isr_withheld,
            'isr_retention_type' => $this->isr_retention_type, 'notes' => $this->notes,
            'id' => $this->id, 'supplier_name' => $this->supplier?->name, 'created_by' => $this->created_by,
            'created_at' => $this->created_at, 'updated_at' => $this->updated_at,
        ];
    }
}
