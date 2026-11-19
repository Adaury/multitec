<?php

namespace App\Support;

use App\Models\CompanyProfile;
use App\Models\Invoice;
use App\Models\PurchaseInvoice;
use Illuminate\Support\Carbon;

/** Reportes fiscales de la DGII: 606 (compras), 607 (ventas) y 608 (anulados). Mismas columnas y reglas que la versión original. */
class Dgii
{
    public const H606 = [
        'RNC/Cédula Proveedor', 'Tipo Identificación', 'Tipo de Bienes y Servicios Comprados', 'NCF', 'NCF Modificado',
        'Fecha Comprobante', 'Fecha Pago', 'Monto Facturado en Servicios', 'Monto Facturado en Bienes', 'Total Monto Facturado',
        'ITBIS Facturado', 'ITBIS Retenido', 'ITBIS sujeto a Proporcionalidad', 'ITBIS llevado al Costo', 'ITBIS por Adelantar',
        'ITBIS percibido en compras', 'Tipo de Retención en ISR', 'Monto Retención Renta', 'ISR Percibido en compras',
        'Impuesto Selectivo al Consumo', 'Otros Impuestos/Tasas', 'Monto Propina Legal', 'Forma de Pago',
    ];

    public const H607 = [
        'RNC/Cédula Comprador', 'Tipo Identificación', 'NCF', 'NCF Modificado', 'Tipo de Ingreso', 'Fecha Comprobante',
        'Fecha Retención', 'Monto Facturado', 'ITBIS Facturado', 'ITBIS Retenido por Terceros', 'ITBIS Percibido',
        'Retención Renta por Terceros', 'ISR Percibido', 'Impuesto Selectivo al Consumo', 'Otros Impuestos/Tasas',
        'Monto Propina Legal', 'Efectivo', 'Cheque/Transferencia/Depósito', 'Tarjeta Débito/Crédito', 'Venta a Crédito',
        'Bonos o Certificados de Regalo', 'Permuta', 'Otras Formas de Venta',
    ];

    public const H608 = ['Número de Comprobante Fiscal', 'Fecha de Comprobante', 'Tipo de Anulación', 'Descripción del Tipo de Anulación'];

    /** Posición de la columna de cada forma de pago en el 607. */
    private const PAYMENT_COLUMN = ['efectivo' => 16, 'cheque_transferencia' => 17, 'tarjeta' => 18, 'credito' => 19, 'bonos' => 20, 'permuta' => 21, 'otras' => 22];

    /** Norma General 10-18: las facturas de consumo (B02) menores de este monto no se detallan en el 607. */
    private const CONSUMPTION_THRESHOLD = 250000.00;

    private static function local($dt): Carbon
    {
        return Carbon::parse($dt)->setTimezone('America/Santo_Domingo');
    }

    /** 1 = RNC (9 dígitos), 2 = Cédula (11). Sin documento queda en blanco. */
    private static function idType607(?string $rnc): string
    {
        if (! $rnc) {
            return '';
        }

        return strlen(preg_replace('/\D/', '', $rnc)) === 11 ? '2' : '1';
    }

    private static function idType606(?string $rnc): string
    {
        return strlen(preg_replace('/\D/', '', (string) $rnc)) === 11 ? '2' : '1';
    }

    private static function summarized(Invoice $inv): bool
    {
        return $inv->ncf_type === 'B02' && (float) $inv->total < self::CONSUMPTION_THRESHOLD;
    }

    public static function rows607(int $year, int $month): array
    {
        $rows = [];
        foreach (Invoice::with('project.client')->whereNull('voided_at')->orderBy('created_at')->orderBy('id')->get() as $inv) {
            $issued = self::local($inv->created_at);
            if ($issued->year !== $year || $issued->month !== $month || self::summarized($inv)) {
                continue;
            }
            $client = $inv->project->client;
            $itbisW = (float) $inv->itbis_withheld;
            $isrW = (float) $inv->isr_withheld;
            $row = array_fill(0, count(self::H607), '');
            $row[0] = $client->rnc ?: '';
            $row[1] = self::idType607($client->rnc);
            $row[2] = $inv->ncf ?: '';
            $row[4] = '01'; // ingresos por operaciones (régimen ordinario)
            $row[5] = $issued->format('Ymd');
            $row[7] = (float) $inv->subtotal;
            $row[8] = (float) $inv->itbis;
            if ($itbisW > 0 || $isrW > 0) {
                if ($inv->retention_date) {
                    $row[6] = $inv->retention_date->format('Ymd');
                }
                if ($itbisW > 0) {
                    $row[9] = $itbisW;
                }
                if ($isrW > 0) {
                    $row[11] = $isrW; // «Retención Renta por Terceros»; la 13 es ISR percibido
                }
            }
            $col = self::PAYMENT_COLUMN[$inv->payment_method ?? ''] ?? null;
            if ($col !== null) {
                $row[$col] = (float) $inv->total; // la forma de pago va con el total cobrado
            }
            $rows[] = $row;
        }

        return $rows;
    }

    /** Resumen de facturas de consumo menores de RD$250,000 del mes: se digita en la Oficina Virtual. */
    public static function consumptionSummary(int $year, int $month): array
    {
        $count = 0;
        $sub = 0;
        $total = 0;
        foreach (Invoice::whereNull('voided_at')->get() as $inv) {
            $issued = self::local($inv->created_at);
            if ($issued->year === $year && $issued->month === $month && self::summarized($inv)) {
                $count++;
                $sub += Money::cents($inv->subtotal);
                $total += Money::cents($inv->total);
            }
        }

        return ['count' => $count, 'subtotal' => Money::fromCents($sub), 'total' => Money::fromCents($total)];
    }

    public static function rows606(int $year, int $month): array
    {
        $rows = [];
        foreach (PurchaseInvoice::with('supplier')->orderBy('invoice_date')->orderBy('id')->get() as $inv) {
            if ((int) $inv->invoice_date->format('Y') !== $year || (int) $inv->invoice_date->format('n') !== $month) {
                continue;
            }
            $services = (float) $inv->services_amount;
            $goods = (float) $inv->goods_amount;
            $itbis = (float) $inv->itbis_invoiced;
            $itbisW = (float) $inv->itbis_withheld;
            $isrW = (float) $inv->isr_withheld;
            $rows[] = [
                $inv->supplier->rnc ?: '', self::idType606($inv->supplier->rnc), $inv->expense_type, $inv->ncf,
                $inv->ncf_modified ?: '', $inv->invoice_date->format('Ymd'), $inv->payment_date ? $inv->payment_date->format('Ymd') : '',
                $services, $goods, $services + $goods, $itbis, $itbisW > 0 ? $itbisW : '', '', '', $itbis, '',
                $isrW > 0 ? ($inv->isr_retention_type ?: '') : '', $isrW > 0 ? $isrW : '', '', '', '', '', $inv->payment_type,
            ];
        }

        return $rows;
    }

    /** @return array<int,array{0:string,1:string,2:string}> [ncf, fecha del comprobante, tipo de anulación] */
    public static function rows608(int $year, int $month): array
    {
        $rows = [];
        foreach (Invoice::whereNotNull('voided_at')->orderBy('voided_at')->orderBy('id')->get() as $inv) {
            $when = self::local($inv->voided_at);
            if ($when->year !== $year || $when->month !== $month || ! $inv->ncf) {
                continue;
            }
            $rows[] = [$inv->ncf, self::local($inv->created_at)->format('Ymd'), $inv->void_reason ?: ''];
        }

        return $rows;
    }

    public static function csv606(int $y, int $m): string
    {
        return Csv::build(self::H606, self::rows606($y, $m));
    }

    public static function csv607(int $y, int $m): string
    {
        return Csv::build(self::H607, self::rows607($y, $m));
    }

    public static function csv608(int $y, int $m): string
    {
        $rows = array_map(fn ($r) => [$r[0], $r[1], $r[2], Invoice::VOID_REASONS[$r[2]] ?? ''], self::rows608($y, $m));

        return Csv::build(self::H608, $rows);
    }

    // ---- archivo de envío (TXT) -------------------------------------------------------

    private static function txtCell($v): string
    {
        if ($v === null || $v === '') {
            return '';
        }
        if (is_float($v)) {
            return number_format($v, 2, '.', '');
        }

        return trim(str_replace(['|', "\r", "\n"], ' ', (string) $v));
    }

    public static function companyRnc(): string
    {
        $raw = (string) (CompanyProfile::first()?->rnc ?? '');
        $digits = preg_replace('/\D/', '', $raw);
        if (! in_array(strlen($digits), [9, 11], true)) {
            throw new ApiException(400, 'Para generar el archivo de la DGII hace falta el RNC de la empresa (9 u 11 dígitos). Escríbelo en «Mi empresa» (campo RNC).');
        }

        return $digits;
    }

    /** Línea de encabezado FORMATO|RNC|AAAAMM|CANTIDAD y un registro por línea, sin títulos de columna. */
    public static function txt(string $form, int $year, int $month, array $rows): string
    {
        $lines = [sprintf('%s|%s|%04d%02d|%d', $form, self::companyRnc(), $year, $month, count($rows))];
        foreach ($rows as $row) {
            $lines[] = implode('|', array_map([self::class, 'txtCell'], $row));
        }

        return implode("\r\n", $lines)."\r\n";
    }
}
