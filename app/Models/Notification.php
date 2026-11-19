<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;

class Notification extends Model
{
    use BelongsToCompany;

    public $timestamps = false;
    protected $guarded = ['id', 'company_id'];
    protected $casts = ['read' => 'boolean', 'created_at' => 'datetime'];

    public function toOut(): array
    {
        return [
            'id' => $this->id, 'title' => $this->title, 'body' => $this->body, 'link' => $this->link,
            'read' => (bool) $this->read, 'created_at' => $this->created_at,
        ];
    }
}
