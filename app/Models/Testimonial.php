<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Testimonial extends Model
{
    public $timestamps = false;
    protected $guarded = ['id'];
    protected $casts = ['published' => 'boolean', 'is_example' => 'boolean', 'rating' => 'integer', 'created_at' => 'datetime'];

    public function toOut(bool $withContact = true): array
    {
        return [
            'author' => $this->author, 'role' => $this->role, 'company' => $this->company, 'quote' => $this->quote,
            'rating' => (int) $this->rating, 'published' => (bool) $this->published, 'sort' => (int) $this->sort, 'id' => $this->id,
            'is_example' => (bool) $this->is_example, 'source' => $this->source, 'contact' => $withContact ? $this->contact : null,
        ];
    }
}
