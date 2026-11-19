<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\Relations\HasOne;

class Project extends Model
{
    use BelongsToCompany;

    protected $guarded = ['id', 'company_id'];
    protected $casts = [
        'date' => 'date:Y-m-d', 'created_at' => 'datetime', 'updated_at' => 'datetime',
        'portal_first_viewed_at' => 'datetime', 'portal_last_viewed_at' => 'datetime',
    ];

    public function client(): BelongsTo
    {
        return $this->belongsTo(Client::class);
    }

    public function survey(): HasOne
    {
        return $this->hasOne(Survey::class);
    }

    public function quotes(): HasMany
    {
        return $this->hasMany(Quote::class);
    }

    public function invoices(): HasMany
    {
        return $this->hasMany(Invoice::class);
    }

    public function tickets(): HasMany
    {
        return $this->hasMany(Ticket::class);
    }

    public function stages(): HasMany
    {
        return $this->hasMany(ProjectStage::class)->orderBy('order');
    }

    /** Dirección del sitio: la del proyecto, o la del cliente si el proyecto no tiene. */
    public function placeAddress(): ?string
    {
        return $this->address ?: $this->client?->address;
    }

    public function placeLocationUrl(): ?string
    {
        return $this->location_url ?: $this->client?->location_url;
    }

    public function toOut(): array
    {
        return [
            'id' => $this->id, 'code' => $this->code, 'client_id' => $this->client_id,
            'responsible_id' => $this->responsible_id, 'date' => $this->date?->format('Y-m-d'), 'status' => $this->status,
            'description' => $this->description, 'address' => $this->address, 'location_url' => $this->location_url,
            'survey_type' => $this->survey_type, 'created_by' => $this->created_by,
            'created_at' => $this->created_at, 'updated_at' => $this->updated_at,
        ];
    }
}
