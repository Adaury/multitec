<?php

namespace App\Support;

use App\Models\Notification;
use App\Models\Quote;
use App\Models\Ticket;
use App\Models\User;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Mail;

/**
 * Avisos: dentro de la app (campanita) y por correo. Ninguno puede tumbar la operación de negocio que lo disparó:
 * la operación ya se guardó antes de avisar, así que un fallo aquí solo se registra.
 */
class Notify
{
    /** El correo solo sale si el servidor SMTP está configurado; si no, no hay a quién ni cómo avisar. */
    public static function mailConfigured(): bool
    {
        return config('mail.default') === 'smtp' && (string) config('mail.mailers.smtp.host') !== '' && config('mail.mailers.smtp.host') !== '127.0.0.1';
    }

    public static function email(string $to, string $subject, string $body, ?array $attachment = null): void
    {
        if (! self::mailConfigured() || $to === '') {
            return;
        }
        try {
            Mail::raw($body, function ($m) use ($to, $subject, $attachment) {
                $m->to($to)->subject($subject);
                if ($attachment) {
                    $m->attachData($attachment[1], $attachment[0], ['mime' => $attachment[2]]);
                }
            });
        } catch (\Throwable $e) {
            Log::warning('No se pudo enviar el correo a '.$to.': '.$e->getMessage());
        }
    }

    public static function user(int $userId, string $title, string $body, ?string $link = null): void
    {
        try {
            Notification::create(['user_id' => $userId, 'title' => $title, 'body' => $body, 'link' => $link, 'created_at' => now()]);
        } catch (\Throwable $e) {
            Log::warning("No se pudo crear la notificación para el usuario $userId: ".$e->getMessage());
        }
    }

    /** Admins activos de la empresa: aviso en la app a cada uno; correo a NOTIFICATION_EMAIL o, si no, a cada admin. */
    public static function admins(string $subject, string $body, ?string $link = null): void
    {
        $admins = User::where('company_id', app('company_id'))->where('role', 'admin')->where('is_active', true)->get();
        $override = trim((string) config('app.notification_email'));
        foreach ($override !== '' ? [$override] : $admins->pluck('email')->all() as $to) {
            self::email($to, $subject, $body);
        }
        foreach ($admins as $a) {
            self::user($a->id, $subject, $body, $link);
        }
    }

    private static function quoteBlock(Quote $q): string
    {
        $q->loadMissing('project.client');

        return "Código: {$q->code}\nProyecto: {$q->project->code} — {$q->project->client->name}\nTotal: RD$ ".number_format((float) $q->total, 2)."\n";
    }

    public static function quotePending(Quote $q): void
    {
        self::admins("Cotización {$q->code} pendiente de aprobar",
            "Hay una cotización nueva pendiente de decisión.\n\n".self::quoteBlock($q), "/proyectos/{$q->project_id}?tab=cotizacion");
    }

    public static function quoteStale(Quote $q, int $days): void
    {
        self::admins("Cotización {$q->code} lleva $days días sin respuesta",
            "La cotización sigue 'pendiente' desde hace $days días — puede valer la pena darle seguimiento al cliente.\n\n".self::quoteBlock($q),
            "/proyectos/{$q->project_id}?tab=cotizacion");
    }

    /** El cliente aprobó o rechazó la cotización desde el portal. */
    public static function quoteDecidedByClient(Quote $q, bool $approved, ?string $reason): void
    {
        $verb = $approved ? 'aprobada' : 'rechazada';
        $body = 'El cliente '.($approved ? 'aprobó' : 'rechazó')." la cotización desde el portal de seguimiento.\n\n".self::quoteBlock($q)
            .(! $approved && $reason ? "Motivo: $reason\n" : '');
        self::admins("Cotización {$q->code} $verb por el cliente", $body, "/proyectos/{$q->project_id}?tab=cotizacion");
    }

    /** La primera vez que el cliente abre el enlace del portal (no en cada refresco, para no generar ruido). */
    public static function portalFirstViewed(\App\Models\Project $p): void
    {
        $p->loadMissing('client');
        self::admins("El cliente abrió el portal — {$p->code}",
            "El cliente abrió por primera vez el enlace de seguimiento de su proyecto.\n\nProyecto: {$p->code} — {$p->client->name}\n", "/proyectos/{$p->id}");
    }

    public static function ticketAssigned(Ticket $t): void
    {
        if ($t->technician_id === null) {
            return;
        }
        $tech = User::find($t->technician_id);
        if (! $tech) {
            return;
        }
        $t->loadMissing('project');
        $subject = "Ticket {$t->code} asignado";
        $body = "Se te asignó un ticket de soporte.\n\nCódigo: {$t->code}\nProyecto: {$t->project->code}\nProblema: {$t->problem}\n";
        self::email($tech->email, $subject, $body);
        self::user($tech->id, $subject, $body, "/proyectos/{$t->project_id}?tab=tickets");
    }
}
