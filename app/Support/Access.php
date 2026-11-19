<?php

namespace App\Support;

use App\Models\Client;
use App\Models\Project;
use App\Models\User;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

/**
 * Qué puede ver cada técnico. Admin y oficina ven todo el negocio. Un técnico ve solo lo suyo:
 *  - proyecto: lo creó, es el responsable, o tiene una visita o un ticket asignado;
 *  - cliente: lo creó, o es cliente de un proyecto suyo.
 * Lo que no es suyo responde 404 (no 403) para no revelar que existe.
 */
class Access
{
    public static function restricted(User $u): bool
    {
        return $u->role === 'tecnico';
    }

    /** Limita una consulta de Project a lo que el técnico puede ver (no hace nada para admin/oficina). */
    public static function projectScope(Builder $q, User $u): Builder
    {
        if (! self::restricted($u)) {
            return $q;
        }

        return $q->where(function (Builder $w) use ($u) {
            $w->where('projects.created_by', $u->id)
                ->orWhere('projects.responsible_id', $u->id)
                ->orWhereIn('projects.id', DB::table('visits')->where('technician_id', $u->id)->select('project_id'));
            if (Schema::hasTable('tickets')) {
                $w->orWhereIn('projects.id', DB::table('tickets')->where('technician_id', $u->id)->select('project_id'));
            }
        });
    }

    public static function clientScope(Builder $q, User $u): Builder
    {
        if (! self::restricted($u)) {
            return $q;
        }

        return $q->where(function (Builder $w) use ($u) {
            $w->where('clients.created_by', $u->id)->orWhereIn('clients.id',
                self::projectScope(Project::query(), $u)->select('projects.client_id'));
        });
    }

    public static function canSeeProject(User $u, int $projectId): bool
    {
        return self::projectScope(Project::query(), $u)->where('projects.id', $projectId)->exists();
    }

    public static function canSeeClient(User $u, int $clientId): bool
    {
        return self::clientScope(Client::query(), $u)->where('clients.id', $clientId)->exists();
    }

    /** Valida los parámetros de ruta (project_id, client_id, visit_id) de un técnico: 404 si no son suyos. */
    public static function enforce(User $u, array $params): void
    {
        if (! self::restricted($u)) {
            return;
        }
        $notFound = new ApiException(404, 'No encontrado');

        if (isset($params['project_id']) && ! self::canSeeProject($u, (int) $params['project_id'])) {
            throw $notFound;
        }
        if (isset($params['client_id'])) {
            $id = (int) $params['client_id'];
            if (Client::whereKey($id)->exists() && ! self::canSeeClient($u, $id)) {
                throw $notFound;
            }
        }
        if (isset($params['client_asset_id'])) { // OJO: no se llama asset_id, que ya es el de las fotos del levantamiento
            $e = \App\Models\ClientAsset::find((int) $params['client_asset_id']);
            if ($e && ! self::canSeeClient($u, $e->client_id)) {
                throw $notFound;
            }
        }
        if (isset($params['entry_id'])) {
            $e = \App\Models\LogEntry::find((int) $params['entry_id']);
            if ($e && ! self::canSeeProject($u, $e->project_id)) {
                throw $notFound;
            }
        }
        if (isset($params['ticket_id'])) {
            $t = \App\Models\Ticket::find((int) $params['ticket_id']);
            if ($t && $t->technician_id !== $u->id && ! self::canSeeProject($u, $t->project_id)) {
                throw $notFound;
            }
        }
        if (isset($params['visit_id'])) {
            $v = \App\Models\Visit::find((int) $params['visit_id']);
            if ($v && $v->technician_id !== $u->id && ! self::canSeeProject($u, $v->project_id)) {
                throw $notFound;
            }
        }
    }
}
