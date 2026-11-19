<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;

class TicketHistory extends Model
{
    use BelongsToCompany;

    protected $table = 'ticket_history';
    public $timestamps = false;
    protected $guarded = ['id', 'company_id'];
    protected $casts = ['created_at' => 'datetime'];

    public static function add(int $ticketId, string $action, ?string $note = null): void
    {
        self::create(['ticket_id' => $ticketId, 'action' => $action, 'note' => $note, 'created_at' => now()]);
    }

    public function toOut(): array
    {
        return ['id' => $this->id, 'action' => $this->action, 'note' => $this->note, 'created_at' => $this->created_at];
    }
}
