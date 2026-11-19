<?php

namespace App\Support;

use App\Models\Budget;
use App\Models\CompanyProfile;
use App\Models\Invoice;
use App\Models\Product;
use App\Models\Quote;
use Dompdf\Dompdf;
use Dompdf\Options;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\Storage;

/** PDF de cotizaciones, presupuestos y facturas (mismo diseño que la versión original). */
class PdfBuilder
{
    private const LOGO_MAX_H = 22; // mm
    private const LOGO_MAX_W = 60; // mm
    private const CONTENT_W = 175; // mm (Letter con 20 mm de margen)
    private const ANNEX_MAX_H = 105; // mm
    private const ANNEX_MAX_PHOTOS = 8;
    private const ANNEX_SIDE_PX = 1100;
    private const FALLBACK_CATEGORY = 'Mano de obra y servicios';

    // ---- documentos -----------------------------------------------------------------------

    public static function quote(Quote $q, string $variant = 'detallada', string $photos = 'none'): string
    {
        $q->loadMissing('items', 'project.client', 'project.survey.assets.markers');
        $titles = ['ejecutiva' => 'Cotización — Resumen ejecutivo', 'global' => 'Cotización — Monto general'];
        $categoryTotals = null;
        if ($variant === 'ejecutiva') {
            $names = Product::with('category')->whereIn('id', $q->items->pluck('product_id')->filter()->unique())->get()
                ->mapWithKeys(fn ($p) => [$p->id => $p->category?->name]);
            $totals = [];
            foreach ($q->items as $i) {
                $cat = ($i->product_id ? ($names[$i->product_id] ?? null) : null) ?: self::FALLBACK_CATEGORY;
                $totals[$cat] = ($totals[$cat] ?? 0) + Money::cents($i->subtotal);
            }
            $categoryTotals = array_map(fn ($name, $c) => [$name, Money::fromCents($c)], array_keys($totals), $totals);
        }

        return self::render([
            'docTitle' => $titles[$variant] ?? 'Cotización', 'code' => $q->code, 'createdAt' => $q->created_at,
            'client' => $q->project->client, 'project' => $q->project, 'items' => self::lines($q->items),
            'subtotal' => (float) $q->subtotal, 'itbis' => (float) $q->itbis, 'total' => (float) $q->total,
            'statusLabel' => ucfirst(str_replace('_', ' ', $q->status)), 'notes' => $q->notes,
            'categoryTotals' => $categoryTotals, 'showLinePrices' => $variant !== 'global',
            'annex' => self::annex($q->project->survey, $photos),
        ]);
    }

    public static function invoice(Invoice $inv, string $variant = 'detallada'): string
    {
        $inv->loadMissing('items', 'project.client');
        $prices = $variant !== 'global';
        $company = self::company();

        return self::render([
            'docTitle' => $prices ? 'Factura' : 'Factura — Detalle de trabajo', 'code' => $inv->code, 'createdAt' => $inv->created_at,
            'client' => $inv->project->client, 'project' => $inv->project, 'items' => self::lines($inv->items),
            'subtotal' => (float) $inv->subtotal, 'itbis' => (float) $inv->itbis, 'total' => (float) $inv->total,
            'ncf' => $prices ? $inv->ncf : null, 'dueDays' => (int) config('app.invoice_due_days', 7),
            'showLinePrices' => $prices, 'clientLabel' => 'FACTURADO A', 'closingNote' => $company['invoice_notes'] ?: null,
        ]);
    }

    /** Resumen para el cliente: nombres y cantidades (enteras) y el total final, sin precios unitarios ni ITBIS. */
    public static function budget(Budget $b): string
    {
        $b->loadMissing('items', 'project.client');

        return self::render([
            'docTitle' => 'Presupuesto — Resumen', 'code' => $b->code, 'createdAt' => $b->created_at,
            'client' => $b->project->client, 'project' => $b->project, 'items' => self::lines($b->items, false),
            'subtotal' => 0, 'itbis' => 0, 'total' => (float) $b->total, 'notes' => $b->notes,
            'showLinePrices' => false, 'showQuantities' => true, 'quantityFirst' => true, 'integerQuantities' => true,
        ]);
    }

    // ---- piezas ---------------------------------------------------------------------------

    private static function lines($items, bool $withPrices = true): array
    {
        return $items->map(fn ($i) => [
            'description' => $i->description, 'note' => $i->note, 'quantity' => (float) $i->quantity,
            'unit_price' => $withPrices ? (float) $i->unit_price : 0.0,
            'subtotal' => $withPrices ? (float) $i->subtotal : 0.0,
        ])->values()->all();
    }

    private static function company(): array
    {
        $p = CompanyProfile::first();
        $out = [];
        foreach (array_keys(CompanyProfile::FIELDS) as $f) {
            $out[$f] = (string) ($p?->$f ?? '');
        }
        $out['logo_path'] = $p?->logo_path ?: null;

        return $out;
    }

    /** Logo ajustado a su caja (alto máximo 22 mm, ancho máximo 60 mm) como data URI, o null si no hay o no se lee. */
    private static function logo(?string $path): ?array
    {
        if (! $path || ! Storage::disk('local')->exists($path)) {
            return null;
        }
        $abs = Storage::disk('local')->path($path);
        $info = @getimagesize($abs);
        if (! $info || ! in_array($info['mime'], ['image/png', 'image/jpeg', 'image/webp'], true)) {
            return null;
        }
        $scale = min(self::LOGO_MAX_H / $info[1], self::LOGO_MAX_W / $info[0]);

        return [
            'uri' => 'data:'.$info['mime'].';base64,'.base64_encode((string) file_get_contents($abs)),
            'w' => round($info[0] * $scale, 2), 'h' => round($info[1] * $scale, 2),
        ];
    }

    /** Foto lista para el PDF: orientada según EXIF, reducida y en JPEG. [uri, ancho px, alto px] o null si no se puede abrir. */
    private static function photoData(string $abs): ?array
    {
        $info = @getimagesize($abs);
        if (! $info || ! function_exists('imagecreatetruecolor')) {
            return null;
        }
        $img = match ($info['mime']) {
            'image/jpeg' => @imagecreatefromjpeg($abs),
            'image/png' => @imagecreatefrompng($abs),
            'image/webp' => function_exists('imagecreatefromwebp') ? @imagecreatefromwebp($abs) : false,
            default => false, // HEIC: GD no lo abre
        };
        if (! $img) {
            return null;
        }
        if ($info['mime'] === 'image/jpeg' && function_exists('exif_read_data')) {
            $orient = @exif_read_data($abs)['Orientation'] ?? 1;
            $angle = [3 => 180, 6 => -90, 8 => 90][$orient] ?? 0;
            if ($angle) {
                $img = imagerotate($img, $angle, 0) ?: $img;
            }
        }
        $w = imagesx($img);
        $h = imagesy($img);
        $k = min(1, self::ANNEX_SIDE_PX / max($w, $h));
        if ($k < 1) {
            $img = imagescale($img, (int) round($w * $k), (int) round($h * $k)) ?: $img;
            $w = imagesx($img);
            $h = imagesy($img);
        }
        ob_start();
        imagejpeg($img, null, 82);
        $jpeg = (string) ob_get_clean();

        return ['data:image/jpeg;base64,'.base64_encode($jpeg), $w, $h];
    }

    /** Anexo fotográfico: fotos del levantamiento con los puntos numerados encima. `marked` = solo las que tienen puntos. */
    private static function annex($survey, string $mode): array
    {
        if (! $survey || ! in_array($mode, ['marked', 'all'], true)) {
            return [];
        }
        $out = [];
        foreach ($survey->assets->sortBy('id') as $asset) {
            if ($asset->kind !== 'photo') {
                continue;
            }
            $markers = $asset->markers->sortBy('number');
            if ($mode === 'marked' && $markers->isEmpty()) {
                continue;
            }
            if (! Uploads::owns($asset->file_path) || ! Storage::disk('local')->exists($asset->file_path)) {
                continue;
            }
            $data = self::photoData(Storage::disk('local')->path($asset->file_path));
            if (! $data) {
                continue; // foto ilegible: no tumba toda la cotización
            }
            [$uri, $pw, $ph] = $data;
            $ratio = $ph / $pw;
            $w = self::CONTENT_W;
            $h = $w * $ratio;
            if ($h > self::ANNEX_MAX_H) {
                $h = self::ANNEX_MAX_H;
                $w = $h / $ratio;
            }
            $d = max(5.0, $w * 0.044);
            $pins = $markers->map(fn ($m) => [
                'n' => $m->number, 'd' => round($d, 2), 'font' => round(max(7, $d * 1.15), 1),
                'left' => round($m->x * $w - $d / 2, 2), 'top' => round($m->y * $h - $d / 2, 2),
            ])->values()->all();
            $out[] = [
                'uri' => $uri, 'w' => round($w, 2), 'h' => round($h, 2), 'title' => $asset->description, 'pins' => $pins,
                'legend' => $markers->map(fn ($m) => [$m->number, $m->label])->values()->all(),
            ];
            if (count($out) >= self::ANNEX_MAX_PHOTOS) {
                break;
            }
        }

        return $out;
    }

    // ---- render ---------------------------------------------------------------------------

    private static function render(array $p): string
    {
        $company = self::company();
        $local = Carbon::parse($p['createdAt'])->setTimezone('America/Santo_Domingo');
        $client = $p['client'];

        $idLine = implode(' · ', array_filter([
            $company['rnc'] ? 'RNC: '.$company['rnc'] : null, $company['cedula'] ? 'Cédula: '.$company['cedula'] : null,
        ]));
        $contactLine = implode(' · ', array_filter([$company['phone'], $company['email'], $company['website']]));
        $details = [['Fecha', $local->format('d/m/Y')]];
        if (! empty($p['dueDays'])) {
            $details[] = ['Vencimiento', $local->copy()->addDays($p['dueDays'])->format('d/m/Y')];
        }
        if (! empty($p['ncf'])) {
            $details[] = ['NCF', $p['ncf']];
        }
        $details[] = ['Proyecto', $p['project']->code];
        if (! empty($p['statusLabel'])) {
            $details[] = ['Estado', $p['statusLabel']];
        }
        [$mainTitle, $subtitle] = array_pad(explode(' — ', $p['docTitle'], 2), 2, '');
        $rate = (float) config('app.itbis_rate', 0.18);
        $integer = $p['integerQuantities'] ?? false;

        $html = view('pdf.document', [
            'company' => $company, 'logo' => self::logo($company['logo_path']),
            'companyLines' => array_values(array_filter([$idLine, $company['address'], $contactLine])),
            'mainTitle' => $mainTitle, 'subtitle' => $subtitle, 'code' => $p['code'], 'client' => $client,
            'clientLabel' => $p['clientLabel'] ?? 'CLIENTE', 'details' => $details, 'items' => $p['items'],
            'categoryTotals' => $p['categoryTotals'] ?? null, 'showLinePrices' => $p['showLinePrices'] ?? true,
            'showQuantities' => $p['showQuantities'] ?? true, 'quantityFirst' => $p['quantityFirst'] ?? false,
            'showBreakdown' => $p['showBreakdown'] ?? true, 'subtotal' => $p['subtotal'], 'itbis' => $p['itbis'],
            'total' => $p['total'], 'itbisPct' => rtrim(rtrim(number_format($rate * 100, 2, '.', ''), '0'), '.'),
            'notes' => $p['notes'] ?? null, 'bankLines' => array_values(array_filter(array_map('trim', preg_split('/\R/', $company['bank_info'])))),
            'closingNote' => $p['closingNote'] ?? null, 'annex' => $p['annex'] ?? [],
            'fmt' => fn ($v) => 'RD$ '.number_format((float) $v, 2, '.', ','),
            'qty' => fn ($v) => $integer ? (string) (int) round($v) : V::g((float) $v),
        ])->render();

        $opts = new Options();
        $opts->set('defaultFont', 'Helvetica');
        $opts->set('isRemoteEnabled', false);
        $opts->set('isHtml5ParserEnabled', true);
        $opts->set('chroot', [base_path()]);
        $dompdf = new Dompdf($opts);
        $dompdf->loadHtml($html, 'UTF-8');
        $dompdf->setPaper('letter', 'portrait');
        $dompdf->render();

        // Pie de cada página: línea fina, contacto de la empresa y número de página.
        $canvas = $dompdf->getCanvas();
        $fm = $dompdf->getFontMetrics();
        $font = $fm->getFont('Helvetica');
        $w = $canvas->get_width();
        $h = $canvas->get_height();
        $mm = 72 / 25.4;
        $left = 20 * $mm;
        $right = $w - 20 * $mm;
        $contact = implode(' · ', array_filter([$company['name'], $company['phone'], $company['email'], $company['website']]));
        $canvas->page_script(function ($pageNumber, $pageCount, $canvas, $fontMetrics) use ($left, $right, $h, $mm, $font, $contact) {
            $canvas->line($left, $h - 14 * $mm, $right, $h - 14 * $mm, [0.9, 0.91, 0.92], 0.5);
            $canvas->text($left, $h - 10 * $mm, $contact, $font, 7.5, [0.61, 0.64, 0.69]);
            $label = 'Página '.$pageNumber;
            $canvas->text($right - $fontMetrics->getTextWidth($label, $font, 7.5), $h - 10 * $mm, $label, $font, 7.5, [0.61, 0.64, 0.69]);
        });

        return (string) $dompdf->output();
    }
}
