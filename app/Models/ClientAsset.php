<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Carbon;

class ClientAsset extends Model
{
    use BelongsToCompany;

    /** Tipos de equipo que ofrece la app (en la base es texto libre). */
    public const KINDS = ['camara', 'grabador', 'panel_alarma', 'sensor', 'control_acceso', 'cerradura', 'intercomunicador', 'switch', 'router_wifi', 'ups', 'otro'];
    /** Una garantía que vence en menos de estos días se marca «por vencer»: hay tiempo de avisar al cliente. */
    public const WARRANTY_SOON_DAYS = 60;

    protected $guarded = ['id', 'company_id'];
    protected $casts = ['installed_on' => 'date:Y-m-d', 'warranty_until' => 'date:Y-m-d', 'created_at' => 'datetime', 'updated_at' => 'datetime'];

    /** vigente | por_vencer | vencida | null (sin fecha de garantía). Se calcula al responder, no se guarda. */
    public function warrantyStatus(): ?string
    {
        if (! $this->warranty_until) {
            return null;
        }
        $days = (int) Carbon::now('America/Santo_Domingo')->startOfDay()->diffInDays($this->warranty_until->copy()->startOfDay(), false);
        if ($days < 0) {
            return 'vencida';
        }

        return $days <= self::WARRANTY_SOON_DAYS ? 'por_vencer' : 'vigente';
    }

    public function toOut(): array
    {
        return [
            'id' => $this->id, 'client_id' => $this->client_id, 'project_id' => $this->project_id, 'kind' => $this->kind,
            'name' => $this->name, 'brand' => $this->brand, 'model' => $this->model, 'serial' => $this->serial, 'mac' => $this->mac,
            'ip_address' => $this->ip_address, 'location' => $this->location,
            'installed_on' => $this->installed_on?->format('Y-m-d'), 'warranty_until' => $this->warranty_until?->format('Y-m-d'),
            'notes' => $this->notes, 'created_at' => $this->created_at, 'warranty_status' => $this->warrantyStatus(),
        ];
    }
}
