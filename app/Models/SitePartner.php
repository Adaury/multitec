<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class SitePartner extends Model
{
    public $timestamps = false;
    protected $guarded = ['id'];
    protected $casts = ['published' => 'boolean', 'created_at' => 'datetime'];

    public function toOut(): array
    {
        return [
            'name' => $this->name, 'description' => $this->description, 'url' => $this->url, 'logo_url' => $this->logo_url,
            'published' => (bool) $this->published, 'sort' => (int) $this->sort, 'id' => $this->id,
        ];
    }
}
