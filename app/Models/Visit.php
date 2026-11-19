<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Visit extends Model
{
    use BelongsToCompany;

    public const STATUSES = ['programada', 'en_sitio', 'completada', 'cancelada'];

    protected $guarded = ['id', 'company_id'];
    protected $casts = [
        'scheduled_date' => 'date:Y-m-d', 'checkin_at' => 'datetime', 'checkout_at' => 'datetime',
        'created_at' => 'datetime', 'updated_at' => 'datetime',
        'checkin_lat' => 'float', 'checkin_lng' => 'float', 'checkout_lat' => 'float', 'checkout_lng' => 'float',
    ];

    public function project(): BelongsTo
    {
        return $this->belongsTo(Project::class);
    }

    public function technician(): BelongsTo
    {
        return $this->belongsTo(User::class, 'technician_id');
    }

    public function toOut(): array
    {
        $p = $this->project;
        $mins = ($this->checkin_at && $this->checkout_at)
            ? max(0, (int) round(($this->checkout_at->getTimestamp() - $this->checkin_at->getTimestamp()) / 60)) : null;

        return [
            'id' => $this->id, 'project_id' => $this->project_id, 'project_code' => $p->code,
            'client_name' => $p->client->name, 'client_address' => $p->placeAddress(),
            'client_location_url' => $p->placeLocationUrl(), 'client_phone' => $p->client->phone,
            'technician_id' => $this->technician_id, 'technician_name' => $this->technician?->name,
            'scheduled_date' => $this->scheduled_date?->format('Y-m-d'), 'scheduled_time' => $this->scheduled_time,
            'duration_min' => $this->duration_min, 'notes' => $this->notes, 'status' => $this->status,
            'checkin_at' => $this->checkin_at, 'checkin_lat' => $this->checkin_lat, 'checkin_lng' => $this->checkin_lng,
            'checkout_at' => $this->checkout_at, 'checkout_lat' => $this->checkout_lat, 'checkout_lng' => $this->checkout_lng,
            'minutes_on_site' => $mins, 'created_by' => $this->created_by, 'created_at' => $this->created_at,
        ];
    }
}
