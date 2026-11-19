<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;

class InvoiceHistory extends Model
{
    use BelongsToCompany;

    protected $table = 'invoice_history';
    public $timestamps = false;
    protected $guarded = ['id', 'company_id'];
    protected $casts = ['created_at' => 'datetime'];

    public static function add(int $invoiceId, string $action, ?string $note = null): void
    {
        self::create(['invoice_id' => $invoiceId, 'action' => $action, 'note' => $note, 'created_at' => now()]);
    }

    public function toOut(): array
    {
        return ['id' => $this->id, 'action' => $this->action, 'note' => $this->note, 'created_at' => $this->created_at];
    }
}
