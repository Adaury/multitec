<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;

class QuoteHistory extends Model
{
    use BelongsToCompany;

    protected $table = 'quote_history';
    public $timestamps = false;
    protected $guarded = ['id', 'company_id'];
    protected $casts = ['created_at' => 'datetime'];

    public static function add(int $quoteId, string $action, ?string $note = null): void
    {
        self::create(['quote_id' => $quoteId, 'action' => $action, 'note' => $note, 'created_at' => now()]);
    }

    public function toOut(): array
    {
        return ['id' => $this->id, 'action' => $this->action, 'note' => $this->note, 'created_at' => $this->created_at];
    }
}
