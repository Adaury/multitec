<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Company;
use App\Models\CompanyProfile;
use App\Models\PlatformPlan;
use App\Models\RefreshToken;
use App\Models\User;
use App\Support\ApiException;
use App\Support\Audit;
use App\Support\CatalogSeeder;
use App\Support\PasswordPolicy;
use App\Support\Subscriptions;
use App\Support\V;
use Firebase\JWT\JWT;
use Illuminate\Database\QueryException;
use Illuminate\Http\Request;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

/**
 * Panel de la plataforma: el dueño del sistema da de alta empresas, cada una con su administrador, y las suspende o
 * reactiva. Solo is_platform_admin. Todo se audita. Actúa sobre TODAS las empresas: el filtro por empresa está apagado en
 * estas rutas (middleware «platform») y cada escritura lleva su company_id explícito.
 */
class PlatformController extends Controller
{
    // ---- helpers -----------------------------------------------------------------------------

    private function company(int $id): Company
    {
        $c = Company::find($id);
        if (! $c) {
            throw new ApiException(404, 'Empresa no encontrada');
        }

        return $c;
    }

    private function tempPassword(): string
    {
        return rtrim(strtr(base64_encode(random_bytes(9)), '+/', '-_'), '=');
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

    private function revokeAll(int $userId): void
    {
        RefreshToken::where('user_id', $userId)->where('revoked', false)->update(['revoked' => true]);
    }

    /** Ejecuta algo DENTRO de una empresa (sus datos quedan filtrados a ella) y vuelve a apagar el filtro. */
    private function inCompany(int $companyId, callable $fn)
    {
        app()->instance('company_id', $companyId);
        try {
            return $fn();
        } finally {
            app()->forgetInstance('company_id');
        }
    }

    /** Usuarios, proyectos y facturas vigentes por empresa, en tres consultas (no una por empresa). */
    private function counts(): array
    {
        $g = fn ($table, $where = null) => DB::table($table)->when($where, fn ($q) => $q->whereNull($where))
            ->select('company_id', DB::raw('count(*) as c'))->groupBy('company_id')->pluck('c', 'company_id')->all();

        return ['users' => $g('users'), 'projects' => $g('projects'), 'invoices' => $g('invoices', 'voided_at')];
    }

    private function out(Company $c, array $counts): array
    {
        [$setup, $monthly] = Subscriptions::fees($c);

        return [
            'id' => $c->id, 'name' => $c->name, 'slug' => $c->slug, 'is_active' => (bool) $c->is_active, 'notes' => $c->notes,
            'created_at' => $c->created_at, 'trial_ends_at' => $c->trial_ends_at, 'days_left' => $c->daysLeft(),
            'max_users' => $c->max_users, 'is_demo' => (bool) $c->is_demo, 'state' => $c->state(), 'source' => $c->source ?: 'panel',
            'contact_name' => $c->contact_name, 'contact_email' => $c->contact_email, 'contact_phone' => $c->contact_phone,
            'setup_fee' => $setup, 'monthly_fee' => $monthly, 'setup_paid_at' => $c->setup_paid_at, 'paid_until' => $c->paid_until,
            'reviewed_at' => $c->reviewed_at, 'plan_id' => $c->plan_id, 'plan_name' => Subscriptions::planOf($c)?->name,
            'users' => (int) ($counts['users'][$c->id] ?? 0), 'projects' => (int) ($counts['projects'][$c->id] ?? 0),
            'invoices' => (int) ($counts['invoices'][$c->id] ?? 0),
        ];
    }

    private function storageMb(int $companyId): float
    {
        $dirs = [storage_path('app/private/uploads/c'.$companyId)];
        if ($companyId === 1) { // los archivos anteriores a multi-empresa son de la empresa original
            foreach (\App\Support\Uploads::LEGACY_DIRS as $d) {
                $dirs[] = storage_path('app/private/uploads/'.$d);
            }
        }
        $bytes = 0;
        foreach ($dirs as $dir) {
            if (is_dir($dir)) {
                foreach (new \RecursiveIteratorIterator(new \RecursiveDirectoryIterator($dir, \FilesystemIterator::SKIP_DOTS)) as $f) {
                    $bytes += $f->isFile() ? $f->getSize() : 0;
                }
            }
        }

        return round($bytes / (1024 * 1024), 2);
    }

    private function detail(Company $c): array
    {
        $team = User::where('company_id', $c->id)->orderBy('role')->orderBy('name')->get();

        return $this->out($c, $this->counts()) + [
            'team' => $team->map(fn ($u) => [
                'id' => $u->id, 'name' => $u->name, 'email' => $u->email, 'role' => $u->role, 'is_active' => (bool) $u->is_active,
                'last_login_at' => $u->last_login_at, 'is_platform_admin' => (bool) $u->is_platform_admin,
            ])->values(),
            'storage_mb' => $this->storageMb($c->id),
            'payments' => Subscriptions::paymentsOf($c->id)->map(fn ($p) => $p->toOut())->values(),
        ];
    }

    private function email($v): string
    {
        $e = mb_strtolower(trim((string) $v));
        if (! filter_var($e, FILTER_VALIDATE_EMAIL) || strlen($e) > 255) {
            throw new ApiException(422, 'Correo electrónico inválido');
        }

        return $e;
    }

    // ---- empresas ----------------------------------------------------------------------------

    public function companies()
    {
        $counts = $this->counts();

        return Company::orderBy('id')->get()->map(fn ($c) => $this->out($c, $counts))->values();
    }

    /** Crea la empresa, su membrete, su administrador (clave temporal que debe cambiar) y las clasificaciones base. No hereda nada de otra empresa. */
    public function create(Request $r)
    {
        $admin = $r->attributes->get('user');
        $name = trim((string) V::text($r->input('name'), 120, 'name', true));
        $adminName = trim((string) V::text($r->input('admin_name'), 120, 'admin_name', true));
        if (mb_strlen($name) < 2 || mb_strlen($adminName) < 2) {
            throw new ApiException(422, 'Escribe al menos 2 caracteres');
        }
        $email = $this->email($r->input('admin_email'));
        $notes = V::text($r->input('notes'), 2000, 'notes');
        $trial = V::int($r->input('trial_days'), 'trial_days');
        $max = V::int($r->input('max_users'), 'max_users');
        if (($trial !== null && ($trial < 1 || $trial > 365)) || ($max !== null && ($max < 1 || $max > 1000))) {
            throw new ApiException(422, 'Días de prueba (1-365) o tope de usuarios (1-1000) fuera de rango');
        }
        if (User::where('email', $email)->exists()) {
            throw new ApiException(400, 'Ya existe un usuario con ese correo');
        }
        $temporary = $this->tempPassword();
        try {
            [$company, $adminUser] = DB::transaction(function () use ($name, $adminName, $email, $notes, $trial, $max, $temporary, $admin, $r) {
                $c = Company::create([
                    'name' => $name, 'slug' => $this->slug($name), 'notes' => $notes, 'max_users' => $max, 'created_at' => now(),
                    'trial_ends_at' => $trial ? Carbon::now()->addDays($trial) : null,
                ]);
                CompanyProfile::withoutGlobalScopes()->forceCreate(['company_id' => $c->id, 'name' => $name]);
                $u = User::create([
                    'company_id' => $c->id, 'name' => $adminName, 'email' => $email, 'hashed_password' => password_hash($temporary, PASSWORD_BCRYPT),
                    'role' => 'admin', 'must_change_password' => true, 'created_by' => $admin->id, 'created_at' => now(),
                ]);
                Audit::log('company_created', $admin, entity: 'company', entityId: $c->id, detail: ['empresa' => $name, 'admin' => $email],
                    request: $r, companyId: $c->id);

                return [$c, $u];
            });
        } catch (QueryException $e) {
            if (str_contains($e->getMessage(), 'Duplicate entry')) {
                throw new ApiException(400, 'Ya existe un usuario con ese correo');
            }
            throw $e;
        }
        $this->inCompany($company->id, fn () => CatalogSeeder::categories()); // el catálogo base se siembra DENTRO de la empresa nueva

        return response()->json([
            'company' => $this->out($company->fresh(), $this->counts()), 'admin_email' => $email, 'admin_user_id' => $adminUser->id,
            'temporary_password' => $temporary, // se muestra una sola vez
        ], 201);
    }

    public function show(int $company_id)
    {
        return $this->detail($this->company($company_id));
    }

    public function update(Request $r, int $company_id)
    {
        $user = $r->attributes->get('user');
        $c = $this->company($company_id);
        $d = [];
        if ($r->filled('name')) {
            $d['name'] = trim((string) V::text($r->input('name'), 120, 'name'));
        }
        if ($r->has('notes')) {
            $d['notes'] = V::text($r->input('notes'), 2000, 'notes');
        }
        if (filter_var($r->input('clear_trial', false), FILTER_VALIDATE_BOOLEAN)) {
            $d['trial_ends_at'] = null;
        } elseif ($r->filled('extend_days')) {
            $days = V::int($r->input('extend_days'), 'extend_days');
            if ($days < 1 || $days > 365) {
                throw new ApiException(422, 'extend_days debe estar entre 1 y 365');
            }
            // Desde hoy si ya venció, o desde su fecha de vencimiento si sigue vigente.
            $base = $c->trial_ends_at && $c->trial_ends_at->gt(Carbon::now()) ? $c->trial_ends_at->copy() : Carbon::now();
            $d['trial_ends_at'] = $base->addDays($days);
        }
        if (filter_var($r->input('clear_max_users', false), FILTER_VALIDATE_BOOLEAN)) {
            $d['max_users'] = null;
        } elseif ($r->filled('max_users')) {
            $d['max_users'] = V::int($r->input('max_users'), 'max_users');
        }
        if (filter_var($r->input('clear_fees', false), FILTER_VALIDATE_BOOLEAN)) {
            $d['setup_fee'] = null;
            $d['monthly_fee'] = null;
        } else {
            if ($r->input('setup_fee') !== null) {
                $d['setup_fee'] = V::num($r->input('setup_fee'), 'setup_fee', 0.0);
            }
            if ($r->input('monthly_fee') !== null) {
                $d['monthly_fee'] = V::num($r->input('monthly_fee'), 'monthly_fee', 0.0);
            }
        }
        if ($r->filled('paid_until')) {
            $pu = (string) $r->input('paid_until');
            if (! preg_match('/^\d{4}-\d{2}-\d{2}$/', $pu) || ! strtotime($pu)) {
                throw new ApiException(422, 'paid_until inválida (usa AAAA-MM-DD)');
            }
            $d['paid_until'] = Carbon::parse($pu)->startOfDay();
            $d['trial_ends_at'] = null;
        }
        if ($r->filled('plan_id')) {
            $plan = PlatformPlan::find((int) $r->input('plan_id'));
            if (! $plan) {
                throw new ApiException(400, 'Plan no encontrado');
            }
            $d['plan_id'] = $plan->id;
            $d['max_users'] = $plan->max_users;
        }
        if ($r->has('contact_phone')) {
            $d['contact_phone'] = trim((string) V::text($r->input('contact_phone'), 30, 'contact_phone')) ?: null;
        }
        $c->update($d);
        Audit::log('company_edited', $user, entity: 'company', entityId: $c->id, detail: ['campos' => array_keys($r->all())], request: $r, companyId: $c->id);

        return $this->out($c->fresh(), $this->counts());
    }

    private function setActive(Request $r, int $id, bool $active)
    {
        $user = $r->attributes->get('user');
        $c = $this->company($id);
        if (! $active && $c->id === $user->company_id) {
            throw new ApiException(400, 'No puedes suspender tu propia empresa: te quedarías sin acceso');
        }
        if ($c->is_active !== $active) {
            DB::transaction(function () use ($c, $active, $user, $r) {
                $c->update(['is_active' => $active]);
                if (! $active) { // una empresa suspendida pierde el acceso al instante: se cierran todas sus sesiones
                    foreach (User::where('company_id', $c->id)->pluck('id') as $uid) {
                        $this->revokeAll($uid);
                    }
                }
                Audit::log($active ? 'company_activated' : 'company_suspended', $user, entity: 'company', entityId: $c->id,
                    detail: ['empresa' => $c->name], request: $r, companyId: $c->id);
            });
        }

        return $this->out($c->fresh(), $this->counts());
    }

    public function suspend(Request $r, int $company_id)
    {
        return $this->setActive($r, $company_id, false);
    }

    public function activate(Request $r, int $company_id)
    {
        return $this->setActive($r, $company_id, true);
    }

    // ---- claves -----------------------------------------------------------------------------

    /** Clave temporal nueva para el administrador de una empresa (por si la perdió). Se muestra una sola vez. */
    public function resetAdminPassword(Request $r, int $company_id)
    {
        $user = $r->attributes->get('user');
        $this->company($company_id);
        $q = User::where('company_id', $company_id)->where('role', 'admin');
        if ($r->filled('user_id')) {
            $q->where('id', (int) $r->input('user_id'));
        } else {
            $q->where('is_active', true)->orderBy('id');
        }
        $admin = $q->first();
        if (! $admin) {
            throw new ApiException(404, 'Esa empresa no tiene un administrador con ese dato');
        }
        if ($admin->id === $user->id) {
            throw new ApiException(400, 'Para tu propia contraseña usa tu perfil');
        }
        $temp = $this->tempPassword();
        DB::transaction(function () use ($admin, $temp, $user, $r, $company_id) {
            $admin->update(['hashed_password' => password_hash($temp, PASSWORD_BCRYPT), 'must_change_password' => true]);
            $this->revokeAll($admin->id);
            Audit::log('password_reset_by_platform', $user, entity: 'user', entityId: $admin->id, detail: ['objetivo' => $admin->email],
                request: $r, companyId: $company_id);
        });

        return ['user_id' => $admin->id, 'email' => $admin->email, 'temporary_password' => $temp];
    }

    /** Cambia la clave de cualquier usuario de una empresa (a mano o al azar). Queda como temporal. */
    public function setUserPassword(Request $r, int $company_id, int $user_id)
    {
        $user = $r->attributes->get('user');
        $this->company($company_id);
        $target = User::where('company_id', $company_id)->where('id', $user_id)->first();
        if (! $target) {
            throw new ApiException(404, 'Usuario no encontrado en esa empresa');
        }
        if ($target->is_platform_admin) {
            throw new ApiException(400, 'Para la cuenta de la plataforma usa tu perfil');
        }
        $manual = trim((string) $r->input('password', ''));
        $password = $manual !== '' ? PasswordPolicy::enforce($manual) : $this->tempPassword();
        DB::transaction(function () use ($target, $password, $manual, $user, $r, $company_id) {
            $target->update(['hashed_password' => password_hash($password, PASSWORD_BCRYPT), 'must_change_password' => true]);
            $this->revokeAll($target->id);
            Audit::log('password_set_by_platform', $user, entity: 'user', entityId: $target->id,
                detail: ['objetivo' => $target->email, 'manual' => $manual !== ''], request: $r, companyId: $company_id);
        });

        return ['user_id' => $target->id, 'email' => $target->email, 'temporary_password' => $password];
    }

    // ---- panel, pagos, soporte --------------------------------------------------------------------

    public function summary()
    {
        return Subscriptions::summary();
    }

    public function reviewed(Request $r, int $company_id)
    {
        $c = $this->company($company_id);
        if ($c->reviewed_at === null) {
            $c->update(['reviewed_at' => Carbon::now()]);
            Audit::log('company_request_reviewed', $r->attributes->get('user'), entity: 'company', entityId: $c->id,
                detail: ['empresa' => $c->name], request: $r, companyId: $c->id);
        }

        return $this->out($c->fresh(), $this->counts());
    }

    /** Anota un pago recibido. La mensualidad (o la instalación que incluye meses) corre «pagado hasta». */
    public function addPayment(Request $r, int $company_id)
    {
        $user = $r->attributes->get('user');
        $c = $this->company($company_id);
        $kind = (string) $r->input('kind', '');
        $method = (string) $r->input('method', '');
        if (! in_array($kind, Subscriptions::KINDS, true)) {
            throw new ApiException(422, 'kind debe ser instalacion o mensualidad');
        }
        if (! in_array($method, Subscriptions::METHODS, true)) {
            throw new ApiException(422, 'method inválido');
        }
        $amount = V::num($r->input('amount'), 'amount', null, 0);
        if ($amount === null || $amount > 10_000_000) {
            throw new ApiException(422, 'El monto debe ser mayor que 0');
        }
        $months = V::int($r->input('months', 1), 'months') ?? 1;
        if ($months < 0 || $months > 36) {
            throw new ApiException(422, 'months debe estar entre 0 y 36');
        }
        $paidAt = $r->input('paid_at');
        if ($paidAt !== null && $paidAt !== '' && (! is_string($paidAt) || ! preg_match('/^\d{4}-\d{2}-\d{2}$/', $paidAt) || ! strtotime($paidAt))) {
            throw new ApiException(422, 'paid_at inválida (usa AAAA-MM-DD)');
        }
        $paidAt = $paidAt ?: Carbon::now('America/Santo_Domingo')->toDateString();
        DB::transaction(function () use ($c, $kind, $amount, $months, $method, $paidAt, $r, $user) {
            $p = Subscriptions::registerPayment($c, $kind, $amount, $months, $method, $paidAt,
                V::text($r->input('reference'), 120, 'reference'), V::text($r->input('notes'), 1000, 'notes'), $user->id);
            if ($c->reviewed_at === null) {
                $c->update(['reviewed_at' => Carbon::now()]);
            }
            Audit::log('company_payment_recorded', $user, entity: 'company', entityId: $c->id, detail: [
                'tipo' => $p->kind, 'monto' => $p->amount, 'meses' => $p->months, 'metodo' => $p->method, 'pagado_hasta' => $c->paid_until?->toIso8601String(),
            ], request: $r, companyId: $c->id);
        });

        return response()->json($this->detail($c->fresh()), 201);
    }

    /**
     * Entrar a una empresa para darle soporte, como su administrador, por SUPPORT_SESSION_MINUTES. Por defecto en solo
     * lectura; con allow_changes se pueden corregir datos. Queda en la auditoría de la plataforma y en la de la empresa.
     */
    public function supportSession(Request $r, int $company_id)
    {
        $user = $r->attributes->get('user');
        $c = $this->company($company_id);
        $allow = filter_var($r->input('allow_changes', false), FILTER_VALIDATE_BOOLEAN);
        $minutes = (int) config('app.support_session_minutes', 60);
        $exp = time() + $minutes * 60;
        $token = JWT::encode(['sub' => (string) $user->id, 'exp' => $exp, 'support_company' => $c->id, 'support_write' => $allow], config('app.jwt_secret'), 'HS256');
        Audit::log('support_session_started', $user, entity: 'company', entityId: $c->id,
            detail: ['empresa' => $c->name, 'permite_cambios' => $allow, 'minutos' => $minutes], request: $r, companyId: $c->id);

        return ['access_token' => $token, 'company_id' => $c->id, 'company_name' => $c->name, 'allow_changes' => $allow, 'expires_at' => date('c', $exp)];
    }

    /** example.com está reservado por la IANA para ejemplos: nunca recibe correo de verdad. */
    private const DEMO_DOMAIN = 'example.com';
    private const DEMO_CLIENTS = [
        ['Residencial Los Arcos (ejemplo)', 'Av. Principal #120, Santo Domingo', 'Instalar 8 cámaras IP con grabador y acceso remoto.'],
        ['Colmado Don Pepe (ejemplo)', 'Calle Duarte #45, Santiago', 'Alarma con sensores de movimiento y sirena; 4 cámaras interiores.'],
        ['Taller Mecánico Ramírez (ejemplo)', 'Carretera Sánchez km 9', 'Cerco eléctrico y control de acceso para el portón.'],
    ];

    /**
     * Empresa de demostración: un administrador y varios técnicos de prueba con clave temporal (se muestran una sola
     * vez), clientes y proyectos de ejemplo ya repartidos entre los técnicos, y vencimiento automático.
     */
    public function demo(Request $r)
    {
        $admin = $r->attributes->get('user');
        $techs = $r->input('technicians') !== null ? V::int($r->input('technicians'), 'technicians') : 3;
        $days = $r->input('days') !== null ? V::int($r->input('days'), 'days') : 14;
        if ($techs < 1 || $techs > 10 || $days < 1 || $days > 90) {
            throw new ApiException(422, 'Técnicos (1-10) o días (1-90) fuera de rango');
        }
        $name = $r->filled('name') ? trim((string) V::text($r->input('name'), 100, 'name')) : null;
        if ($name !== null && mb_strlen($name) < 2) {
            throw new ApiException(422, 'Escribe al menos 2 caracteres');
        }
        $name ??= 'Multitec Demo '.(Company::where('is_demo', true)->count() + 1);

        [$company, $accounts] = DB::transaction(function () use ($name, $techs, $days, $admin, $r) {
            $c = Company::create([
                'name' => $name, 'slug' => $this->slug($name), 'notes' => 'Empresa de demostración', 'is_demo' => true,
                'max_users' => $techs + 1, 'trial_ends_at' => Carbon::now()->addDays($days), 'created_at' => now(),
            ]);
            CompanyProfile::withoutGlobalScopes()->forceCreate(['company_id' => $c->id, 'name' => $name]);
            $specs = [['Administrador Demo', 'admin1', 'admin']];
            for ($n = 1; $n <= $techs; $n++) {
                $specs[] = ["Técnico Demo $n", "tecnico$n", 'tecnico'];
            }
            $accounts = [];
            foreach ($specs as [$uname, $local, $role]) {
                $password = $this->tempPassword();
                $u = User::create([
                    'company_id' => $c->id, 'name' => $uname, 'email' => "$local.{$c->slug}@".self::DEMO_DOMAIN,
                    'hashed_password' => password_hash($password, PASSWORD_BCRYPT), 'role' => $role, 'must_change_password' => true,
                    'created_by' => $admin->id, 'created_at' => now(),
                ]);
                $accounts[] = ['user_id' => $u->id, 'name' => $u->name, 'email' => $u->email, 'role' => $role, 'temporary_password' => $password];
            }
            Audit::log('demo_company_created', $admin, entity: 'company', entityId: $c->id,
                detail: ['empresa' => $name, 'tecnicos' => $techs, 'dias' => $days], request: $r, companyId: $c->id);

            return [$c, $accounts];
        });

        $adminId = collect($accounts)->firstWhere('role', 'admin')['user_id'];
        $techIds = collect($accounts)->where('role', 'tecnico')->pluck('user_id')->values()->all();
        $this->inCompany($company->id, function () use ($adminId, $techIds) {
            CatalogSeeder::categories();
            foreach (self::DEMO_CLIENTS as $i => [$cname, $address, $description]) {
                $client = \App\Models\Client::create(['name' => $cname, 'address' => $address, 'created_by' => $adminId, 'created_at' => now()]);
                $project = \App\Models\Project::create([
                    'code' => \App\Support\Codes::next('PRY'), 'client_id' => $client->id, 'responsible_id' => $techIds[$i % count($techIds)],
                    'date' => Carbon::now('America/Santo_Domingo')->toDateString(), 'status' => 'levantamiento', 'description' => $description,
                    'address' => $address, 'created_by' => $adminId, 'created_at' => now(),
                ]);
                \App\Models\Survey::create(['project_id' => $project->id, 'created_by' => $adminId, 'created_at' => now()]);
                \App\Models\Engineering::create(['project_id' => $project->id, 'created_by' => $adminId, 'created_at' => now()]);
                foreach (\App\Models\ProjectStage::NAMES as $order => $stage) {
                    \App\Models\ProjectStage::create(['project_id' => $project->id, 'name' => $stage, 'order' => $order]);
                }
            }
        });

        return response()->json(['company' => $this->out($company->fresh(), $this->counts()), 'accounts' => $accounts], 201);
    }
}
