<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Carbon;

class Company extends Model
{
    public $timestamps = false;
    protected $guarded = [];
    protected $casts = [
        'is_active' => 'boolean', 'is_demo' => 'boolean',
        'trial_ends_at' => 'datetime', 'paid_until' => 'datetime', 'created_at' => 'datetime',
        'setup_paid_at' => 'datetime', 'reviewed_at' => 'datetime', 'setup_fee' => 'float', 'monthly_fee' => 'float',
    ];

    public const SUSPENDED = 'Tu empresa está suspendida. Contacta al administrador de la plataforma.';
    public const TRIAL_ENDED = 'El periodo de prueba de tu empresa terminó. Contacta al administrador de la plataforma.';
    public const PAYMENT_OVERDUE = 'La mensualidad de tu empresa está vencida. Realiza el pago y avísale a Multitec para reactivar el acceso.';
    public const GRACE_DAYS = 5;

    /** Pasó «pagado hasta» (todavía puede estar dentro de los días de gracia). */
    public function paymentOverdue(): bool
    {
        return $this->paid_until !== null && $this->paid_until->lte(Carbon::now());
    }

    /** Pasaron también los días de gracia: ya no entra. */
    public function paymentCutOff(): bool
    {
        return $this->paid_until !== null && $this->paid_until->copy()->addDays(self::GRACE_DAYS)->lte(Carbon::now());
    }

    /** suspendida | prueba | vencida (prueba terminada) | atrasada (en días de gracia) | cortada | activa */
    public function state(): string
    {
        if (! $this->is_active) {
            return 'suspendida';
        }
        if ($this->paid_until !== null) {
            if ($this->paymentCutOff()) {
                return 'cortada';
            }

            return $this->paymentOverdue() ? 'atrasada' : 'activa';
        }
        if ($this->trial_ends_at !== null) {
            return $this->trial_ends_at->lte(Carbon::now()) ? 'vencida' : 'prueba';
        }

        return 'activa';
    }

    /** La próxima fecha que importa: «pagado hasta» o el fin de la prueba. */
    public function endsAt(): ?Carbon
    {
        return $this->paid_until ?? $this->trial_ends_at;
    }

    /** Días que faltan (negativo = venció hace N días); null si no vence nunca. */
    public function daysLeft(): ?int
    {
        $ends = $this->endsAt();

        return $ends === null ? null : (int) floor(($ends->getTimestamp() - Carbon::now()->getTimestamp()) / 86400);
    }

    /** Por qué nadie de esta empresa puede entrar ahora (null = puede). */
    public function accessBlockReason(): ?string
    {
        if (! $this->is_active) {
            return self::SUSPENDED;
        }
        if ($this->paid_until !== null) {
            return $this->paid_until->copy()->addDays(self::GRACE_DAYS)->lte(Carbon::now()) ? self::PAYMENT_OVERDUE : null;
        }
        if ($this->trial_ends_at !== null && $this->trial_ends_at->lte(Carbon::now())) {
            return self::TRIAL_ENDED;
        }
        return null;
    }
}
