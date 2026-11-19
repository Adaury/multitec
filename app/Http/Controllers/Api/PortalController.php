<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Company;
use App\Models\Invoice;
use App\Models\Project;
use App\Models\Quote;
use App\Models\QuoteHistory;
use App\Support\ApiException;
use App\Support\Audit;
use App\Support\Notify;
use App\Support\PdfBuilder;
use App\Support\QuoteApproval;
use App\Support\V;
use Illuminate\Http\Request;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;

/**
 * Portal del cliente: un enlace de solo lectura (sin sesión) para que vea su proyecto, sus cotizaciones y facturas, y
 * apruebe o rechace una cotización. La empresa sale del proyecto al que pertenece el enlace; después todo se filtra a ella.
 */
class PortalController extends Controller
{
    // ---- gestión del enlace (admin y oficina) ----------------------------------------------------------

    public function createLink(Request $r, int $project_id)
    {
        $p = Project::find($project_id);
        if (! $p) {
            throw new ApiException(404, 'Proyecto no encontrado');
        }
        $rotated = $p->public_token !== null;
        $token = rtrim(strtr(base64_encode(random_bytes(32)), '+/', '-_'), '=');
        $p->update(['public_token' => $token]);
        Audit::log($rotated ? 'portal_link_rotated' : 'portal_link_created', $r->attributes->get('user'), entity: 'project', entityId: $p->id,
            detail: ['proyecto' => $p->code], request: $r);

        return ['token' => $token];
    }

    public function revokeLink(Request $r, int $project_id)
    {
        $p = Project::find($project_id);
        if (! $p) {
            throw new ApiException(404, 'Proyecto no encontrado');
        }
        $p->update(['public_token' => null]);
        Audit::log('portal_link_revoked', $r->attributes->get('user'), entity: 'project', entityId: $p->id, detail: ['proyecto' => $p->code], request: $r);

        return response()->noContent();
    }

    // ---- portal público -------------------------------------------------------------------------

    /** Localiza el proyecto por su token. Esa búsqueda es lo único que corre sin filtro; luego todo queda fijado a su empresa. */
    private function byToken(string $token): Project
    {
        $owner = $token !== '' ? Project::withoutGlobalScopes()->where('public_token', $token)->first() : null;
        $company = $owner ? Company::find($owner->company_id) : null;
        if (! $company || ! $company->is_active) {
            throw new ApiException(404, 'Enlace no válido');
        }
        app()->instance('company_id', $company->id);

        return Project::with(['client', 'quotes.items', 'invoices.items', 'tickets.technician', 'survey.assets.markers'])
            ->where('public_token', $token)->firstOrFail();
    }

    private function out(Project $p): array
    {
        return [
            'code' => $p->code, 'status' => $p->status, 'date' => $p->date?->format('Y-m-d'), 'description' => $p->description,
            'client_name' => $p->client->name,
            'quotes' => $p->quotes->sortByDesc('created_at')->map(fn ($q) => [
                'id' => $q->id, 'code' => $q->code, 'status' => $q->status, 'subtotal' => (float) $q->subtotal, 'itbis' => (float) $q->itbis,
                'total' => (float) $q->total, 'created_at' => $q->created_at,
                'items' => $q->items->map(fn ($i) => [
                    'description' => $i->description, 'quantity' => (float) $i->quantity, 'unit_price' => (float) $i->unit_price, 'subtotal' => (float) $i->subtotal,
                ])->values(),
            ])->values(),
            'invoices' => $p->invoices->whereNull('voided_at')->map(fn ($i) => [
                'id' => $i->id, 'code' => $i->code, 'ncf' => $i->ncf, 'subtotal' => (float) $i->subtotal, 'itbis' => (float) $i->itbis,
                'total' => (float) $i->total, 'created_at' => $i->created_at,
            ])->values(),
            'tickets' => $p->tickets->map(fn ($t) => [
                'code' => $t->code, 'problem' => $t->problem, 'solution' => $t->solution, 'status' => $t->status,
                'technician_name' => $t->technician?->name, 'created_at' => $t->created_at, 'resolved_at' => $t->resolved_at,
            ])->values(),
        ];
    }

    public function show(string $token)
    {
        $p = $this->byToken($token);
        $first = $p->portal_first_viewed_at === null;
        $p->update(['portal_first_viewed_at' => $first ? Carbon::now() : $p->portal_first_viewed_at, 'portal_last_viewed_at' => Carbon::now()]);
        if ($first) {
            Notify::portalFirstViewed($p);
        }

        return $this->out($p);
    }

    public function approve(Request $r, string $token, int $quote_id)
    {
        $p = $this->byToken($token);
        if (! $p->quotes->contains('id', $quote_id)) {
            throw new ApiException(404, 'Cotización no encontrada');
        }
        $signer = trim((string) V::text($r->input('signer_name'), 120, 'signer_name'));
        $note = 'Aprobada por el cliente desde el portal'.($signer !== '' ? " — firmó: $signer" : '');
        DB::transaction(function () use ($quote_id, $note) {
            // Bloquea la fila: dos aprobaciones simultáneas (doble clic, reintento de red) no duplican materiales ni prefactura.
            $q = Quote::with('items')->lockForUpdate()->find($quote_id);
            if ($q->status !== 'pendiente') {
                throw new ApiException(400, "No se puede aprobar una cotización '{$q->status}'");
            }
            QuoteApproval::approve($q, null, $note);
        });
        Notify::quoteDecidedByClient(Quote::find($quote_id), true, null);

        return $this->out($this->byToken($token));
    }

    public function reject(Request $r, string $token, int $quote_id)
    {
        $p = $this->byToken($token);
        if (! $p->quotes->contains('id', $quote_id)) {
            throw new ApiException(404, 'Cotización no encontrada');
        }
        $reason = trim((string) V::text($r->input('reason'), 1000, 'reason'));
        $signer = trim((string) V::text($r->input('signer_name'), 120, 'signer_name'));
        $note = 'Rechazada por el cliente desde el portal'.($signer !== '' ? " — $signer" : '').($reason !== '' ? ": $reason" : '');
        DB::transaction(function () use ($quote_id, $note) {
            $q = Quote::lockForUpdate()->find($quote_id);
            if ($q->status !== 'pendiente') {
                throw new ApiException(400, "No se puede rechazar una cotización '{$q->status}'");
            }
            $q->update(['status' => 'no_aprobada', 'decided_at' => Carbon::now(), 'updated_at' => now()]);
            QuoteHistory::add($q->id, 'rechazada', $note);
        });
        Notify::quoteDecidedByClient(Quote::find($quote_id), false, $reason);

        return $this->out($this->byToken($token));
    }

    public function quotePdf(string $token, int $quote_id)
    {
        $p = $this->byToken($token);
        $q = $p->quotes->firstWhere('id', $quote_id);
        if (! $q) {
            throw new ApiException(404, 'Cotización no encontrada');
        }

        return response(PdfBuilder::quote($q, 'detallada', 'marked'), 200, [
            'Content-Type' => 'application/pdf', 'Content-Disposition' => 'attachment; filename="'.$q->code.'.pdf"',
        ]);
    }

    public function invoicePdf(string $token, int $invoice_id)
    {
        $p = $this->byToken($token);
        $i = $p->invoices->whereNull('voided_at')->firstWhere('id', $invoice_id);
        if (! $i) {
            throw new ApiException(404, 'Factura no encontrada');
        }

        return response(PdfBuilder::invoice($i), 200, [
            'Content-Type' => 'application/pdf', 'Content-Disposition' => 'attachment; filename="'.$i->code.'.pdf"',
        ]);
    }
}
