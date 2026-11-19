<?php

namespace App\Support;

use App\Models\Company;
use App\Models\CompanyPayment;
use App\Models\CompanyProfile;
use App\Models\PlatformPlan;
use Illuminate\Support\Carbon;

/**
 * Suscripciones de las empresas a la plataforma: prueba, instalación, mensualidad y pagos. La empresa se registra sola
 * y tiene PLATFORM_TRIAL_DAYS de prueba; luego paga una vez la instalación y cada mes el soporte y uso. Los pagos los
 * registra la plataforma a mano: cada mes pagado corre «pagado hasta» un mes.
 */
class Subscriptions
{
    public const KINDS = ['instalacion', 'mensualidad'];
    public const METHODS = ['transferencia', 'deposito', 'efectivo', 'tarjeta', 'otro'];

    public static function contactPhones(): array
    {
        return array_values(array_filter(array_map('trim', explode(',', (string) config('app.platform_contact_phone')))));
    }

    public static function planOf(Company $c): ?PlatformPlan
    {
        return $c->plan_id ? PlatformPlan::find($c->plan_id) : null;
    }

    /** Instalación y mensualidad: la tarifa propia de la empresa, si no la de su plan, si no la general. @return array{0:float,1:float} */
    public static function fees(Company $c): array
    {
        $plan = self::planOf($c);

        return [
            $c->setup_fee !== null ? (float) $c->setup_fee : ($plan ? (float) $plan->setup_price : (float) config('app.platform_setup_fee')),
            $c->monthly_fee !== null ? (float) $c->monthly_fee : ($plan ? (float) $plan->monthly_price : (float) config('app.platform_monthly_fee')),
        ];
    }

    /** Cómo pagarle a la plataforma: lo del .env o, si está vacío, las cuentas de «Mi empresa» de la empresa 1. */
    public static function paymentInfo(): string
    {
        $configured = str_replace('\\n', "\n", (string) config('app.platform_payment_info'));
        if (trim($configured) !== '') {
            return $configured;
        }

        return (string) (CompanyProfile::withoutGlobalScopes()->where('company_id', 1)->value('bank_info') ?? '');
    }

    public static function newTrialEnd(): Carbon
    {
        return Carbon::now()->addDays((int) config('app.platform_trial_days'));
    }

    /** Mismo día del mes N meses después (31 de enero + 1 = 28/29 de febrero). */
    public static function addMonths(Carbon $d, int $months): Carbon
    {
        return $d->copy()->addMonthsNoOverflow($months);
    }

    /**
     * Anota el pago. Si cubre meses, «pagado hasta» avanza desde hoy o desde lo ya pagado (lo que sea más tarde) y la
     * prueba termina: la empresa pasa a ser de pago. No abre transacción.
     */
    public static function registerPayment(Company $c, string $kind, float $amount, int $months, string $method, string $paidAt,
        ?string $reference, ?string $notes, ?int $userId): CompanyPayment
    {
        $now = Carbon::now();
        if ($kind === 'instalacion' && $c->setup_paid_at === null) {
            $c->setup_paid_at = Carbon::parse($paidAt)->startOfDay();
        }
        if ($months > 0) {
            $base = $c->paid_until ? $c->paid_until->copy() : $now->copy();
            if ($base->lt($now)) {
                $base = $now->copy();
            }
            $c->paid_until = self::addMonths($base, $months);
            $c->trial_ends_at = null;
        }
        $c->save();

        return CompanyPayment::create([
            'company_id' => $c->id, 'kind' => $kind, 'amount' => $amount, 'months' => $months, 'method' => $method,
            'reference' => $reference ?: null, 'notes' => $notes ?: null, 'paid_at' => $paidAt,
            'paid_until_after' => $c->paid_until, 'recorded_by' => $userId, 'created_at' => now(),
        ]);
    }

    public static function paymentsOf(int $companyId)
    {
        return CompanyPayment::where('company_id', $companyId)->orderByDesc('paid_at')->orderByDesc('id')->get();
    }

    /** Números del panel: empresas por estado, solicitudes nuevas, las que vencen pronto, cobrado este mes y lo esperado por mes. */
    public static function summary(): array
    {
        $companies = Company::where('is_demo', false)->get();
        $byState = [];
        foreach ($companies as $c) {
            $byState[$c->state()] = ($byState[$c->state()] ?? 0) + 1;
        }
        $soon = $companies->filter(fn ($c) => $c->is_active && $c->daysLeft() !== null && $c->daysLeft() <= 7)->sortBy(fn ($c) => $c->daysLeft());
        $monthStart = Carbon::now('America/Santo_Domingo')->startOfMonth()->toDateString();
        $collected = CompanyPayment::where('paid_at', '>=', $monthStart)->get(['amount'])->sum(fn ($p) => Money::cents($p->amount));
        $paying = $companies->filter(fn ($c) => $c->paid_until !== null && in_array($c->state(), ['activa', 'atrasada'], true));
        $monthly = $paying->sum(fn ($c) => Money::cents(self::fees($c)[1]));

        return [
            'by_state' => (object) $byState,
            'new_requests' => $companies->sortByDesc('created_at')->filter(fn ($c) => $c->source === 'registro' && $c->reviewed_at === null)
                ->map(fn ($c) => [
                    'id' => $c->id, 'name' => $c->name, 'created_at' => $c->created_at, 'contact_name' => $c->contact_name,
                    'contact_email' => $c->contact_email, 'contact_phone' => $c->contact_phone, 'days_left' => $c->daysLeft(),
                ])->values(),
            'expiring' => $soon->map(fn ($c) => ['id' => $c->id, 'name' => $c->name, 'state' => $c->state(), 'days_left' => $c->daysLeft()])->values(),
            'currency' => (string) config('app.platform_currency'),
            'collected_this_month' => Money::fromCents($collected), 'expected_monthly' => Money::fromCents($monthly),
            'paying_companies' => $paying->count(),
        ];
    }

    /** Aviso para el administrador de la empresa cuando falta poco o ya está en días de gracia (null = nada que avisar). */
    public static function noticeFor(Company $c): ?string
    {
        $days = $c->daysLeft();
        $state = $c->state();
        if ($state === 'atrasada') {
            return 'Tu mensualidad venció. Realiza el pago para no perder el acceso en los próximos días.';
        }
        if ($state === 'prueba' && $days !== null && $days <= 7) {
            return 'Tu prueba gratis termina en '.max($days, 0).' día(s). Coordina la instalación con Multitec para seguir usando el sistema.';
        }
        if ($state === 'activa' && $c->paid_until !== null && $days !== null && $days <= 5) {
            return 'Tu mensualidad vence en '.max($days, 0).' día(s).';
        }

        return null;
    }
}
