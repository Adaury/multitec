<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Invoice extends Model
{
    use BelongsToCompany;

    /** Forma de pago de la venta: cada una cae en su propia columna del 607. */
    public const PAYMENT_METHODS = ['efectivo', 'cheque_transferencia', 'tarjeta', 'credito', 'bonos', 'permuta', 'otras'];

    /** Tipos de anulación del formato 608 de la DGII. */
    public const VOID_REASONS = [
        '01' => 'Deterioro de factura preimpresa', '02' => 'Errores de impresión (factura preimpresa)',
        '03' => 'Impresión defectuosa', '04' => 'Corrección de la información', '05' => 'Cambio de productos',
        '06' => 'Devolución de productos', '07' => 'Omisión de productos', '08' => 'Errores en secuencia de NCF',
        '09' => 'Por cese de operaciones', '10' => 'Pérdida o hurto de talonarios',
    ];

    public $timestamps = false;
    protected $guarded = ['id', 'company_id'];
    protected $casts = [
        'subtotal' => 'float', 'itbis' => 'float', 'total' => 'float', 'itbis_withheld' => 'float', 'isr_withheld' => 'float',
        'retention_date' => 'date:Y-m-d', 'paid_at' => 'date:Y-m-d', 'voided_at' => 'datetime', 'created_at' => 'datetime',
    ];

    public function items(): HasMany
    {
        return $this->hasMany(InvoiceItem::class)->orderBy('id');
    }

    public function project(): BelongsTo
    {
        return $this->belongsTo(Project::class);
    }

    public function toOut(): array
    {
        return [
            'id' => $this->id, 'code' => $this->code, 'project_id' => $this->project_id, 'pre_invoice_id' => $this->pre_invoice_id,
            'ncf' => $this->ncf, 'ncf_type' => $this->ncf_type, 'subtotal' => (float) $this->subtotal,
            'itbis' => (float) $this->itbis, 'total' => (float) $this->total, 'payment_method' => $this->payment_method,
            'itbis_withheld' => (float) $this->itbis_withheld, 'isr_withheld' => (float) $this->isr_withheld,
            'retention_date' => $this->retention_date?->format('Y-m-d'), 'paid_at' => $this->paid_at?->format('Y-m-d'),
            'voided_at' => $this->voided_at, 'void_reason' => $this->void_reason, 'created_by' => $this->created_by,
            'created_at' => $this->created_at,
            'items' => $this->items->map(fn ($i) => [
                'id' => $i->id, 'product_id' => $i->product_id, 'description' => $i->description,
                'quantity' => (float) $i->quantity, 'unit_price' => (float) $i->unit_price,
                'subtotal' => (float) $i->subtotal, 'note' => $i->note,
            ])->values(),
        ];
    }
}
