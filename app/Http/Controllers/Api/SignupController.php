<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Company;
use App\Models\CompanyProfile;
use App\Models\Notification;
use App\Models\PlatformPlan;
use App\Models\User;
use App\Support\ApiException;
use App\Support\Audit;
use App\Support\CatalogSeeder;
use App\Support\Notify;
use App\Support\SiteDefaults;
use App\Support\Subscriptions;
use App\Support\V;
use Illuminate\Database\QueryException;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;

/**
 * Registro público de empresas (página /registro) y «Mi suscripción» del administrador de cada empresa. Una empresa se
 * registra sola: se crea con su administrador (la clave la elige quien se registra), el catálogo de clasificaciones y el
 * catálogo base de artículos sin precio, y PLATFORM_TRIAL_DAYS de prueba. A la plataforma le llega el aviso.
 */
class SignupController extends Controller
{
    /** Lo que muestra la página de registro (sin datos de nadie): planes, moneda y días de prueba. */
    public function info()
    {
        SiteDefaults::ensure();
        $phones = Subscriptions::contactPhones();

        return [
            'enabled' => (bool) config('app.public_signup_enabled'), 'trial_days' => (int) config('app.platform_trial_days'),
            'currency' => (string) config('app.platform_currency'), 'setup_fee' => (float) config('app.platform_setup_fee'),
            'monthly_fee' => (float) config('app.platform_monthly_fee'), 'contact_phone' => $phones[0] ?? '',
            'plans' => PlatformPlan::where('active', true)->orderBy('sort')->orderBy('id')->get()->map(fn ($p) => $p->toOut())->values(),
        ];
    }

    private function slug(string $name): string
    {
        $base = mb_substr(Str::slug($name), 0, 50) ?: 'empresa';
        $slug = $base;
        for ($n = 2; Company::where('slug', $slug)->exists(); $n++) {
            $slug = $base.'-'.$n;
        }

        return $slug;
    }

    public function signup(Request $r)
    {
        if (! config('app.public_signup_enabled')) {
            throw new ApiException(404, 'El registro de empresas no está disponible');
        }
        if ($r->input('website')) { // robot: no se crea nada
            throw new ApiException(400, 'No se pudo completar el registro');
        }
        $companyName = trim((string) V::text($r->input('company_name'), 120, 'company_name', true));
        $adminName = trim((string) V::text($r->input('admin_name'), 120, 'admin_name', true));
        $phone = trim((string) V::text($r->input('phone'), 30, 'phone', true));
        if (mb_strlen($companyName) < 2 || mb_strlen($adminName) < 2 || mb_strlen($phone) < 7) {
            throw new ApiException(422, 'Completa el nombre de la empresa, tu nombre y un teléfono válido');
        }
        $email = mb_strtolower(trim((string) $r->input('email')));
        if (! filter_var($email, FILTER_VALIDATE_EMAIL) || strlen($email) > 255) {
            throw new ApiException(422, 'Correo electrónico inválido');
        }
        // La clave la genera el sistema (temporal, se muestra una sola vez) y la persona debe cambiarla al entrar.
        $password = rtrim(strtr(base64_encode(random_bytes(9)), '+/', 'Aa'), '=');
        if (! filter_var($r->input('accept_terms', false), FILTER_VALIDATE_BOOLEAN)) {
            throw new ApiException(400, 'Debes aceptar los términos del servicio');
        }

        SiteDefaults::ensure(); // los planes existen aunque nadie haya abierto antes la página pública
        $planId = V::int($r->input('plan_id'), 'plan_id');
        $plan = $planId ? PlatformPlan::find($planId) : null;
        if ($planId && (! $plan || ! $plan->active)) {
            throw new ApiException(400, 'Ese plan no está disponible');
        }
        $plan ??= PlatformPlan::where('active', true)->orderByDesc('highlighted')->orderBy('sort')->first(); // sin elegir: el destacado
        if (User::where('email', $email)->exists()) {
            throw new ApiException(400, 'Ya existe una cuenta con ese correo. Inicia sesión o usa otro correo.');
        }

        try {
            [$company, $admin] = DB::transaction(function () use ($companyName, $adminName, $email, $phone, $password, $plan, $r) {
                $c = Company::create([
                    'name' => $companyName, 'slug' => $this->slug($companyName), 'source' => 'registro', 'contact_name' => $adminName,
                    'contact_email' => $email, 'contact_phone' => $phone, 'trial_ends_at' => Subscriptions::newTrialEnd(),
                    'plan_id' => $plan?->id, 'max_users' => $plan?->max_users, 'created_at' => now(),
                ]);
                CompanyProfile::withoutGlobalScopes()->forceCreate(['company_id' => $c->id, 'name' => $companyName, 'phone' => $phone, 'email' => $email]);
                $u = User::create([
                    'company_id' => $c->id, 'name' => $adminName, 'email' => $email, 'hashed_password' => password_hash($password, PASSWORD_BCRYPT),
                    'role' => 'admin', 'must_change_password' => true, 'created_at' => now(),
                ]);
                Audit::log('company_signup', $u, entity: 'company', entityId: $c->id, detail: ['empresa' => $companyName, 'telefono' => $phone],
                    request: $r, companyId: $c->id);
                // Aviso en la campanita de cada administrador de la plataforma.
                foreach (User::where('is_platform_admin', true)->where('is_active', true)->get() as $pa) {
                    (new Notification)->forceFill([
                        'company_id' => $pa->company_id, 'user_id' => $pa->id, 'title' => "Nueva empresa registrada: {$c->name}",
                        'body' => "$adminName · $email · $phone. Prueba de ".config('app.platform_trial_days').' días.',
                        'link' => "/plataforma/{$c->id}", 'read' => false, 'created_at' => now(),
                    ])->save();
                }

                return [$c, $u];
            });
        } catch (QueryException $e) {
            if (str_contains($e->getMessage(), 'Duplicate entry')) {
                throw new ApiException(400, 'Ya existe una cuenta con ese correo. Inicia sesión o usa otro correo.');
            }
            throw $e;
        }

        // El catálogo se carga DENTRO de la empresa nueva; si falla, la empresa ya existe y se puede cargar después.
        app()->instance('company_id', $company->id);
        try {
            CatalogSeeder::categories();
            CatalogSeeder::ensureRoots();
            CatalogSeeder::baseCatalog($admin->id);
        } catch (\Throwable $e) {
            Log::error("No se pudo cargar el catálogo base de la empresa {$company->id}: ".$e->getMessage());
        } finally {
            app()->forgetInstance('company_id');
        }

        $notify = trim((string) config('app.notification_email'));
        if ($notify !== '') {
            Notify::email($notify, "Nueva empresa en Multitec: $companyName",
                "Se registró $companyName.\n\nContacto: $adminName\nCorreo: $email\nTeléfono: $phone\n\nTiene ".config('app.platform_trial_days')
                .' días de prueba. Coordina la instalación desde el panel de plataforma.');
        }

        return response()->json([
            'company_name' => $companyName, 'email' => $email, 'trial_days' => (int) config('app.platform_trial_days'),
            'trial_ends_at' => $company->fresh()->trial_ends_at,
            'temporary_password' => $password, // se muestra una sola vez; no se guarda en claro
        ], 201);
    }

    /** ¿Ese correo está libre para registrarse? Lo usa el formulario de registro mientras se escribe. */
    public function emailAvailable(Request $r)
    {
        $email = mb_strtolower(trim((string) $r->query('email')));
        if (! filter_var($email, FILTER_VALIDATE_EMAIL) || strlen($email) > 255) {
            return ['valid' => false, 'available' => false];
        }

        return ['valid' => true, 'available' => ! User::where('email', $email)->exists()];
    }

    /** «Mi suscripción»: estado, lo que se paga y el historial de pagos de la propia empresa. */
    public function mySubscription(Request $r)
    {
        $user = $r->attributes->get('user');
        $c = Company::find($user->company_id);
        [$setup, $monthly] = Subscriptions::fees($c);
        $phones = Subscriptions::contactPhones();

        return [
            'company_name' => $c->name, 'state' => $c->state(), 'trial_ends_at' => $c->trial_ends_at, 'paid_until' => $c->paid_until,
            'days_left' => $c->daysLeft(), 'setup_fee' => $setup, 'monthly_fee' => $monthly, 'setup_paid' => $c->setup_paid_at !== null,
            'notice' => Subscriptions::noticeFor($c), 'payment_info' => Subscriptions::paymentInfo(), 'contact_phone' => $phones[0] ?? '',
            'contact_phones' => $phones, 'plan_name' => Subscriptions::planOf($c)?->name, 'currency' => (string) config('app.platform_currency'),
            'payments' => Subscriptions::paymentsOf($c->id)->map(fn ($p) => $p->toOut())->values(),
        ];
    }
}
