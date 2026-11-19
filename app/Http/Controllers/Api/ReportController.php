<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Support\ApiException;
use App\Support\Csv;
use App\Support\Dgii;
use Illuminate\Http\Request;

class ReportController extends Controller
{
    private function period(Request $r): array
    {
        $y = $r->query('year');
        $m = $r->query('month');
        if (! is_numeric($y) || ! is_numeric($m)) {
            throw new ApiException(422, 'Indica year y month');
        }
        if ((int) $m < 1 || (int) $m > 12) {
            throw new ApiException(400, 'Mes inválido, debe ser 1-12');
        }

        return [(int) $y, (int) $m];
    }

    /** CSV (revisión en Excel) o TXT con el formato de envío de la DGII. */
    private function dgii(Request $r, string $form)
    {
        [$y, $m] = $this->period($r);
        $txt = strtolower((string) $r->query('format', 'csv')) === 'txt';
        if ($txt) {
            $rows = match ($form) { '606' => Dgii::rows606($y, $m), '607' => Dgii::rows607($y, $m), default => Dgii::rows608($y, $m) };
            $content = Dgii::txt($form, $y, $m, $rows);
            // Nombre que usa la DGII para el archivo de envío: DGII_F_607_<RNC>_<AAAAMM>.TXT
            $name = sprintf('DGII_F_%s_%s_%04d%02d.TXT', $form, Dgii::companyRnc(), $y, $m);

            return response($content, 200, ['Content-Type' => 'text/plain; charset=utf-8', 'Content-Disposition' => 'attachment; filename="'.$name.'"']);
        }
        $content = match ($form) { '606' => Dgii::csv606($y, $m), '607' => Dgii::csv607($y, $m), default => Dgii::csv608($y, $m) };

        return Csv::response($content, sprintf('%s_%04d%02d.csv', $form, $y, $m));
    }

    public function dgii606(Request $r)
    {
        return $this->dgii($r, '606');
    }

    public function dgii607(Request $r)
    {
        return $this->dgii($r, '607');
    }

    public function dgii608(Request $r)
    {
        return $this->dgii($r, '608');
    }

    public function consumptionSummary(Request $r)
    {
        [$y, $m] = $this->period($r);

        return Dgii::consumptionSummary($y, $m);
    }
}
