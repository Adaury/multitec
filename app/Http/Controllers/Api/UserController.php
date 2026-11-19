<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Company;
use App\Models\RefreshToken;
use App\Models\User;
use App\Support\ApiException;
use App\Support\Audit;
use App\Support\PasswordPolicy;
use Illuminate\Http\Request;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

class UserController extends Controller
{
    private const ROLES = ['admin', 'oficina', 'tecnico'];
    private const PROFILE = ['phone' => 30, 'zone' => 80, 'skills' => 255, 'vehicle' => 80];

    private function out(User $u): array
    {
        return [
            'id' => $u->id, 'name' => $u->name, 'email' => $u->email, 'role' => $u->role, 'is_active' => $u->is_active,
            'phone' => $u->phone, 'zone' => $u->zone, 'skills' => $u->skills, 'vehicle' => $u->vehicle,
            'last_login_at' => $u->last_login_at, 'created_by' => $u->created_by, 'created_at' => $u->created_at,
        ];
    }

    /** Usuarios de esta empresa (el modelo User no filtra solo, porque el login los busca entre todas). */
    private function scoped()
    {
        return User::where('company_id', app('company_id'));
    }

    private function find(int $id): User
    {
        $u = $this->scoped()->find($id);
        if (! $u) {
            throw new ApiException(404, 'Usuario no encontrado');
        }

        return $u;
    }

    private function ensureSeat(): void
    {
        $company = Company::find(app('company_id'));
        if (! $company || $company->max_users === null) {
            return;
        }
        if ($this->scoped()->where('is_active', true)->count() >= $company->max_users) {
            throw new ApiException(400, "Tu plan permite hasta {$company->max_users} usuarios activos. Desactiva a alguien o pide ampliar el plan.");
        }
    }

    private function email(?string $email): string
    {
        $email = mb_strtolower(trim((string) $email));
        if (! filter_var($email, FILTER_VALIDATE_EMAIL) || strlen($email) > 255) {
            throw new ApiException(422, 'Correo electrónico inválido');
        }

        return $email;
    }

    private function profileData(Request $r): array
    {
        $out = [];
        foreach (self::PROFILE as $f => $max) {
            if ($r->has($f)) {
                $v = $r->input($f);
                if ($v !== null && mb_strlen((string) $v) > $max) {
                    throw new ApiException(422, "El campo $f excede $max caracteres");
                }
                $out[$f] = $v;
            }
        }

        return $out;
    }

    private function revokeAll(int $userId): void
    {
        RefreshToken::where('user_id', $userId)->where('revoked', false)->update(['revoked' => true]);
    }

    // ---- endpoints -------------------------------------------------------

    public function index()
    {
        return $this->scoped()->orderBy('name')->get()->map(fn ($u) => $this->out($u))->values();
    }

    public function technicians()
    {
        return $this->scoped()->where('role', 'tecnico')->where('is_active', true)->orderBy('name')
            ->get(['id', 'name'])->map(fn ($u) => ['id' => $u->id, 'name' => $u->name])->values();
    }

    public function store(Request $r)
    {
        $admin = $r->attributes->get('user');
        $this->ensureSeat();
        $name = trim((string) $r->input('name', ''));
        if ($name === '' || mb_strlen($name) > 120) {
            throw new ApiException(422, 'El nombre es obligatorio (máximo 120 caracteres)');
        }
        $role = $r->input('role', 'oficina');
        if (! in_array($role, self::ROLES, true)) {
            throw new ApiException(422, 'Rol inválido');
        }
        $email = $this->email($r->input('email'));
        $password = PasswordPolicy::enforce((string) $r->input('password', ''));
        if (User::where('email', $email)->exists()) {
            throw new ApiException(400, 'Ya existe un usuario con ese correo');
        }
        $user = User::create([
            'company_id' => $admin->company_id, 'name' => $name, 'email' => $email,
            'hashed_password' => password_hash($password, PASSWORD_BCRYPT),
            'must_change_password' => true, // la eligió el admin: el usuario la cambia al entrar
            'role' => $role, 'created_by' => $admin->id, 'created_at' => Carbon::now(),
        ] + $this->profileData($r));
        Audit::log('user_created', $admin, entity: 'user', entityId: $user->id, detail: ['email' => $email, 'role' => $role], request: $r);

        return response()->json($this->out($user->fresh()), 201);
    }

    public function update(Request $r, int $id)
    {
        $admin = $r->attributes->get('user');
        $user = $this->find($id);
        $data = [];
        $changes = [];

        if ($r->has('name') && $r->input('name') !== null) {
            $n = trim((string) $r->input('name'));
            if ($n === '' || mb_strlen($n) > 120) {
                throw new ApiException(422, 'Nombre inválido');
            }
            $data['name'] = $n;
        }
        if ($r->filled('email')) {
            $data['email'] = $this->email($r->input('email'));
        }
        if ($r->has('role') && $r->input('role') !== null) {
            if (! in_array($r->input('role'), self::ROLES, true)) {
                throw new ApiException(422, 'Rol inválido');
            }
            $data['role'] = $r->input('role');
        }
        if ($r->has('is_active') && $r->input('is_active') !== null) {
            $data['is_active'] = filter_var($r->input('is_active'), FILTER_VALIDATE_BOOLEAN);
        }
        $data += $this->profileData($r);

        // Un admin no puede desactivarse ni quitarse el rol: evita quedarse sin administradores.
        if ($user->id === $admin->id) {
            if (($data['is_active'] ?? true) === false) {
                throw new ApiException(400, 'No puedes desactivar tu propia cuenta');
            }
            if (isset($data['role']) && $data['role'] !== 'admin') {
                throw new ApiException(400, 'No puedes quitarte el rol admin a ti mismo');
            }
        }
        if (($data['is_active'] ?? null) === true && ! $user->is_active) {
            $this->ensureSeat();
        }
        if (isset($data['email']) && $data['email'] !== $user->email && User::where('email', $data['email'])->exists()) {
            throw new ApiException(400, 'Ya existe un usuario con ese correo');
        }

        $password = $r->input('password');
        if ($password !== null && $password !== '') {
            PasswordPolicy::enforce((string) $password);
            $data['hashed_password'] = password_hash((string) $password, PASSWORD_BCRYPT);
            $data['must_change_password'] = $user->id !== $admin->id; // la puesta por otro admin es temporal
            $changes['password'] = 'cambiada';
        }
        if (($data['is_active'] ?? null) === false || isset($data['hashed_password'])) {
            $this->revokeAll($user->id);
        }
        foreach ($data as $f => $v) {
            if ($f === 'hashed_password' || $f === 'must_change_password') {
                continue;
            }
            if ($user->$f != $v) {
                $changes[$f] = in_array($f, ['role', 'is_active', 'email'], true) ? ['de' => $user->$f, 'a' => $v] : 'editado';
            }
        }
        $user->update($data);
        if ($changes) {
            Audit::log(array_keys($changes) === ['password'] ? 'password_reset_by_admin' : 'user_updated', $admin,
                entity: 'user', entityId: $user->id, detail: ['objetivo' => $user->email, 'cambios' => $changes], request: $r);
        }

        return $this->out($user->fresh());
    }

    public function resetPassword(Request $r, int $id)
    {
        $admin = $r->attributes->get('user');
        $user = $this->find($id);
        if ($user->id === $admin->id) {
            throw new ApiException(400, 'Para tu propia contraseña usa tu perfil');
        }
        $temporary = rtrim(strtr(base64_encode(random_bytes(9)), '+/', '-_'), '=');
        $user->update(['hashed_password' => password_hash($temporary, PASSWORD_BCRYPT), 'must_change_password' => true]);
        $this->revokeAll($user->id);
        Audit::log('password_reset_by_admin', $admin, entity: 'user', entityId: $user->id, detail: ['objetivo' => $user->email], request: $r);

        return ['temporary_password' => $temporary];
    }

    private function sessionRows(int $userId)
    {
        return RefreshToken::where('user_id', $userId)->where('revoked', false)->where('expires_at', '>', Carbon::now())
            ->orderByDesc('created_at')->get()->map(fn ($s) => [
                'id' => $s->id, 'created_at' => $s->created_at, 'last_used_at' => $s->last_used_at,
                'user_agent' => $s->user_agent, 'ip' => $s->ip, 'current' => false,
            ])->values();
    }

    public function sessions(int $id)
    {
        return $this->sessionRows($this->find($id)->id);
    }

    public function revokeSession(Request $r, int $id, int $sessionId)
    {
        $this->find($id); // comprueba que el usuario es de esta empresa antes de tocar sus sesiones
        $s = RefreshToken::where('id', $sessionId)->where('user_id', $id)->first();
        if (! $s) {
            throw new ApiException(404, 'Sesión no encontrada');
        }
        $s->update(['revoked' => true]);
        Audit::log('session_revoked', $r->attributes->get('user'), entity: 'user', entityId: $id, request: $r);

        return response()->noContent();
    }

    public function revokeAllSessions(Request $r, int $id)
    {
        $this->find($id);
        $this->revokeAll($id);
        Audit::log('sessions_revoked_all', $r->attributes->get('user'), entity: 'user', entityId: $id, request: $r);

        return response()->noContent();
    }

    // ---- carga de trabajo (visitas/tickets llegan en el paso 2: mientras no existan esas tablas, salen en 0) ----

    private function workload(User $u, string $first, string $last): array
    {
        $total = $pending = $done = $tickets = 0;
        $hours = 0.0;
        if (Schema::hasTable('visits')) {
            $visits = DB::table('visits')->where('technician_id', $u->id)->whereBetween('scheduled_date', [$first, $last])
                ->where('status', '!=', 'cancelada')->get();
            $total = $visits->count();
            $pending = $visits->whereIn('status', ['programada', 'en_sitio'])->count();
            $done = $visits->where('status', 'completada')->count();
            foreach ($visits as $v) {
                if ($v->checkin_at && $v->checkout_at) {
                    $hours += (strtotime($v->checkout_at) - strtotime($v->checkin_at)) / 3600;
                }
            }
        }
        if (Schema::hasTable('tickets')) {
            $tickets = DB::table('tickets')->where('technician_id', $u->id)
                ->whereIn('status', ['abierto', 'asignado', 'en_progreso', 'en_espera'])->count();
        }

        return ['user_id' => $u->id, 'name' => $u->name, 'visits_total' => $total, 'visits_pending' => $pending,
            'visits_done' => $done, 'open_tickets' => $tickets, 'hours_on_site' => round($hours, 2)];
    }

    private function range(Request $r): array
    {
        $today = Carbon::now('America/Santo_Domingo')->toDateString();
        $first = $r->query('start', $today);

        return [$first, $r->query('end', $first)];
    }

    public function teamWorkload(Request $r)
    {
        [$a, $b] = $this->range($r);

        return $this->scoped()->where('is_active', true)->whereIn('role', ['tecnico', 'admin'])->orderBy('name')->get()
            ->map(fn ($u) => $this->workload($u, $a, $b))->values();
    }

    public function userWorkload(Request $r, int $id)
    {
        [$a, $b] = $this->range($r);

        return $this->workload($this->find($id), $a, $b);
    }
}
