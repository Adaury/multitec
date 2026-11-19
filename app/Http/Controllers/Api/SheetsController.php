<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Quote;
use App\Models\QuoteHistory;
use App\Support\ApiException;
use App\Support\Audit;
use App\Support\CatalogImport;
use App\Support\LineItemsIo;
use App\Support\Notify;
use App\Support\PdfBuilder;
use App\Support\Spreadsheets;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Mail;

/** Planillas Excel/CSV del catálogo y de las partidas, y envío de la cotización por correo. */
class SheetsController extends Controller
{
    private const MAX_FILES = 10;

    private function fmt(Request $r, string $default): string
    {
        $f = (string) $r->query('format', $default);
        if (! in_array($f, ['csv', 'xlsx'], true)) {
            throw new ApiException(422, 'format debe ser csv o xlsx');
        }

        return $f;
    }

    private function flag(Request $r, string $key, bool $default): bool
    {
        $v = $r->query($key);

        return $v === null ? $default : filter_var($v, FILTER_VALIDATE_BOOLEAN);
    }

    /** @return array<int, array{0:string,1:string}> */
    private function uploads(Request $r, string $single, string $multi): array
    {
        // Un solo archivo llega como objeto, varios como arreglo: «(array)» sobre el objeto lo desarmaría en propiedades.
        $many = $r->file($multi);
        $list = array_filter(array_merge([$r->file($single)], is_array($many) ? $many : [$many]));
        if (! $list) {
            throw new ApiException(400, 'No llegó ningún archivo');
        }
        if (count($list) > self::MAX_FILES) {
            throw new ApiException(400, 'Sube como máximo '.self::MAX_FILES.' archivos a la vez');
        }
        $out = [];
        foreach (array_values($list) as $i => $f) {
            $out[] = [$f->getClientOriginalName() ?: 'archivo '.($i + 1), (string) file_get_contents($f->getRealPath(), false, null, 0, Spreadsheets::MAX_BYTES + 1)];
        }

        return $out;
    }

    // ---- catálogo -----------------------------------------------------------------

    public function importTemplate(Request $r)
    {
        $kind = (string) $r->query('kind', 'general');
        if ($kind !== 'general' && ! in_array($kind, CatalogImport::kitKinds(), true)) {
            throw new ApiException(400, 'Tipo de plantilla desconocido');
        }

        return Spreadsheets::download(...CatalogImport::templateFile($kind, $this->fmt($r, 'csv')));
    }

    public function baseKits()
    {
        return CatalogImport::kitSummary();
    }

    public function export(Request $r)
    {
        return Spreadsheets::download(...CatalogImport::export($this->fmt($r, 'xlsx')));
    }

    public function import(Request $r)
    {
        $user = $r->attributes->get('user');
        try {
            return CatalogImport::import($this->uploads($r, 'file', 'files'), $user->id, $this->flag($r, 'dry_run', true), $this->flag($r, 'create_categories', false));
        } catch (\InvalidArgumentException $e) {
            throw new ApiException(400, $e->getMessage());
        }
    }

    /** Crea los artículos del catálogo base que todavía no existan (sin precio). Por defecto es vista previa. */
    public function baseCatalog(Request $r)
    {
        $user = $r->attributes->get('user');
        $dry = $this->flag($r, 'dry_run', true);
        $kinds = array_values(array_filter(explode(',', (string) $r->query('kinds', ''))));
        $chosen = $kinds ?: CatalogImport::kitKinds();
        if (array_diff($chosen, CatalogImport::kitKinds()) || ! $chosen) {
            throw new ApiException(400, 'Tipo de lista desconocido');
        }
        $rows = [];
        foreach ($chosen as $k) {
            $rows = array_merge($rows, CatalogImport::kitRows($k));
        }
        $data = Spreadsheets::buildCsvSemicolon(CatalogImport::HEADERS, $rows);
        try {
            $result = DB::transaction(function () use ($dry, $data, $user) {
                $roots = $dry ? [] : CatalogImport::ensureRoots();
                $res = CatalogImport::import([['catalogo_base.csv', $data]], $user->id, $dry, true, true);
                $res['_roots'] = $roots;

                return $res;
            });
        } catch (\InvalidArgumentException $e) {
            throw new ApiException(400, $e->getMessage());
        }
        $roots = $result['_roots'];
        unset($result['_roots']);
        if (! $dry) {
            Audit::log('catalog.base_load', $user, entity: 'catalog', request: $r,
                detail: ['listas' => $chosen, 'creados' => $result['created'], 'categorias' => array_merge($roots, $result['new_categories'])]);
        }

        return $result;
    }

    // ---- partidas -----------------------------------------------------------------

    public function lineItemsTemplate(Request $r)
    {
        return Spreadsheets::download(...LineItemsIo::template($this->fmt($r, 'xlsx')));
    }

    public function lineItemsParse(Request $r)
    {
        $files = $r->file('files');
        if (! $files) {
            throw new ApiException(400, 'No llegó ningún archivo');
        }
        try {
            return LineItemsIo::parse($this->uploads($r, 'file', 'files'));
        } catch (\InvalidArgumentException $e) {
            throw new ApiException(400, $e->getMessage());
        }
    }

    public function quoteItemsFile(Request $r, int $quote_id)
    {
        $q = Quote::with('items')->find($quote_id) ?? throw new ApiException(404, 'Cotización no encontrada');

        return Spreadsheets::download(...LineItemsIo::export($q, $this->fmt($r, 'xlsx')));
    }

    // ---- correo -------------------------------------------------------------------

    private const VARIANT_LABELS = ['detallada' => 'detallada', 'ejecutiva' => 'resumen por categoría', 'global' => 'monto general'];
    private const PDF_SUFFIX = ['detallada' => '', 'ejecutiva' => '-ejecutiva', 'global' => '-monto-general'];

    /** Envía al cliente la cotización con el PDF adjunto. Aquí el usuario pidió el envío: si falla, se le dice. */
    public function sendQuoteEmail(Request $r, int $quote_id)
    {
        $user = $r->attributes->get('user');
        if (! Notify::mailConfigured()) {
            throw new ApiException(409, 'El envío por correo no está configurado en el servidor (falta SMTP). Usa WhatsApp o descarga el PDF.');
        }
        $to = trim((string) $r->input('to'));
        if (! filter_var($to, FILTER_VALIDATE_EMAIL) || strlen($to) > 254) {
            throw new ApiException(422, 'El correo del destinatario no es válido');
        }
        $variant = (string) $r->input('variant', 'detallada');
        $photos = (string) $r->input('photos', 'none');
        if (! isset(self::VARIANT_LABELS[$variant]) || ! in_array($photos, ['none', 'marked', 'all'], true)) {
            throw new ApiException(422, 'Formato de cotización no válido');
        }
        $message = trim((string) $r->input('message', ''));
        if (mb_strlen($message) > 2000) {
            throw new ApiException(422, 'El mensaje es demasiado largo (máximo 2000 caracteres)');
        }
        $q = Quote::with('items', 'project.client')->find($quote_id) ?? throw new ApiException(404, 'Cotización no encontrada');
        $pdf = PdfBuilder::quote($q, $variant, $photos);
        $filename = $q->code.self::PDF_SUFFIX[$variant].($photos !== 'none' ? '-fotos' : '').'.pdf';
        $company = (string) (\App\Models\Company::find($q->company_id)?->name ?: 'Multitec');
        $client = $q->project?->client;
        $greeting = $client?->name ? "Hola {$client->name}," : 'Hola,';
        $body = $message !== '' ? $message
            : "$greeting\n\nLe compartimos la cotización {$q->code} por un total de RD$ ".number_format((float) $q->total, 2).". Adjuntamos el PDF.\n\nQuedamos atentos a cualquier pregunta.\n\n$company";
        try {
            Mail::raw($body, function ($m) use ($to, $q, $company, $pdf, $filename) {
                $m->to($to)->subject("Cotización {$q->code} — $company")->attachData($pdf, $filename, ['mime' => 'application/pdf']);
            });
        } catch (\Throwable $e) {
            report($e);
            throw new ApiException(502, 'El servidor de correo no aceptó el envío. Intenta de nuevo o envíala por WhatsApp.');
        }
        QuoteHistory::add($q->id, 'enviada', "Por correo a $to (".self::VARIANT_LABELS[$variant].')');
        Audit::log('cotizacion.enviada', $user, entity: 'quote', entityId: $q->id, detail: ['canal' => 'correo', 'a' => $to, 'formato' => $variant], request: $r);

        return ['sent_to' => $to, 'filename' => $filename];
    }
}
