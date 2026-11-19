<?php

namespace App\Support;

use PhpOffice\PhpSpreadsheet\Cell\DataType;
use PhpOffice\PhpSpreadsheet\IOFactory;
use PhpOffice\PhpSpreadsheet\Shared\Date as XlDate;
use PhpOffice\PhpSpreadsheet\Spreadsheet;
use PhpOffice\PhpSpreadsheet\Style\Fill;
use PhpOffice\PhpSpreadsheet\Cell\Coordinate;

/**
 * Leer y escribir hojas de cálculo para importar y exportar (catálogo, partidas de cotización). Se aceptan los dos
 * formatos que la gente tiene a mano: CSV (el «Guardar como CSV» de Excel, con `;` o `,`) y Excel (.xlsx). Lo que se lee
 * sale siempre como filas de TEXTO, para que el resto del código no tenga que saber de dónde vino el archivo.
 */
class Spreadsheets
{
    public const MAX_BYTES = 2 * 1024 * 1024;
    public const XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

    private static function decode(string $data): string
    {
        if (str_starts_with($data, "\xEF\xBB\xBF")) {
            return substr($data, 3);
        }
        if (mb_check_encoding($data, 'UTF-8')) {
            return $data;
        }

        return mb_convert_encoding($data, 'UTF-8', 'Windows-1252'); // el «Guardar como CSV» de Excel en Windows
    }

    /** Un .xlsx es un ZIP: se mira el contenido y no solo el nombre (un CSV renombrado no se cuela). */
    private static function isXlsx(string $data, ?string $filename): bool
    {
        return str_starts_with($data, "PK\x03\x04") && ($filename === null || ! str_ends_with(strtolower($filename), '.csv'));
    }

    private static function cellText($v): string
    {
        if ($v === null) {
            return '';
        }
        if (is_bool($v)) {
            return $v ? 'sí' : 'no';
        }
        if (is_float($v) || is_int($v)) {
            // 3500.0 -> "3500"; 12.5 -> "12.5" (sin notación científica ni ceros de más)
            return ($v == (int) $v && abs($v) < 1e15) ? (string) (int) $v : rtrim(rtrim(number_format((float) $v, 10, '.', ''), '0'), '.');
        }

        return trim((string) $v);
    }

    /** @return array<int, array<int, string>> */
    private static function csvRows(string $data): array
    {
        $text = self::decode($data);
        $lines = preg_split('/\r\n|\n|\r/', $text);
        $delimiter = null;
        if ($lines && str_starts_with(strtolower(trim($lines[0])), 'sep=') && strlen(trim($lines[0])) >= 5) {
            $delimiter = trim($lines[0])[4];
            array_shift($lines);
        }
        $first = null;
        foreach ($lines as $l) {
            if (trim($l) !== '') {
                $first = $l;
                break;
            }
        }
        if ($first === null) {
            return [];
        }
        if ($delimiter === null) {
            $delimiter = ';';
            $best = -1;
            foreach ([';', ',', "\t"] as $d) {
                $c = substr_count($first, $d);
                if ($c > $best) {
                    $best = $c;
                    $delimiter = $d;
                }
            }
        }
        $fh = fopen('php://temp', 'r+');
        fwrite($fh, implode("\n", $lines));
        rewind($fh);
        $rows = [];
        while (($r = fgetcsv($fh, 0, $delimiter, '"', '')) !== false) {
            if ($r === [null]) {
                $r = [''];
            }
            $rows[] = array_map(fn ($c) => (string) $c, $r);
        }
        fclose($fh);

        return $rows;
    }

    /** @return array<int, array<int, string>> */
    private static function xlsxRows(string $data): array
    {
        $tmp = tempnam(sys_get_temp_dir(), 'mtx');
        file_put_contents($tmp, $data);
        try {
            $reader = IOFactory::createReader('Xlsx');
            $reader->setReadDataOnly(false);
            $sheet = $reader->load($tmp)->getSheet(0);
        } catch (\Throwable) {
            throw new \InvalidArgumentException('El archivo de Excel está dañado o no es un .xlsx');
        } finally {
            @unlink($tmp);
        }
        $rows = [];
        $maxCol = Coordinate::columnIndexFromString($sheet->getHighestDataColumn());
        $maxRow = $sheet->getHighestDataRow();
        for ($r = 1; $r <= $maxRow; $r++) {
            $row = [];
            for ($c = 1; $c <= $maxCol; $c++) {
                $cell = $sheet->getCell([$c, $r]);
                $v = $cell->getCalculatedValue();
                if (is_numeric($v) && XlDate::isDateTime($cell)) {
                    $v = XlDate::excelToDateTimeObject($v)->format('Y-m-d');
                }
                $row[] = self::cellText($v);
            }
            $rows[] = $row;
        }

        return $rows;
    }

    /**
     * Filas de texto de un CSV o de la primera hoja de un Excel. Las filas vacías del final se quitan.
     *
     * @return array<int, array<int, string>>
     * @throws \InvalidArgumentException con un mensaje listo para mostrar
     */
    public static function readRows(string $data, ?string $filename = null): array
    {
        if (strlen($data) > self::MAX_BYTES) {
            throw new \InvalidArgumentException('El archivo pesa más de '.(self::MAX_BYTES / 1048576).' MB');
        }
        if ($filename && str_ends_with(strtolower($filename), '.xls')) {
            throw new \InvalidArgumentException('El formato .xls (Excel viejo) no se puede leer: guárdalo como .xlsx o CSV');
        }
        $rows = self::isXlsx($data, $filename) ? self::xlsxRows($data) : self::csvRows($data);
        while ($rows && ! array_filter($rows[array_key_last($rows)], fn ($c) => trim($c) !== '')) {
            array_pop($rows);
        }

        return $rows;
    }

    /** Texto que Excel tomaría por fórmula se neutraliza con un apóstrofo (igual que en los CSV). */
    private static function safe($v)
    {
        if (is_string($v) && $v !== '' && in_array($v[0], ['=', '+', '-', '@', "\t", "\r"], true) && ! preg_match('/^[+-]?\d+([.,]\d+)?$/', $v)) {
            return "'".$v;
        }

        return $v;
    }

    /** Excel con el encabezado en negrita (blanco sobre azul) y fijo arriba. */
    public static function buildXlsx(array $headers, array $rows, string $title = 'Hoja1', array $widths = []): string
    {
        $wb = new Spreadsheet();
        $sheet = $wb->getActiveSheet();
        $sheet->setTitle(mb_substr(preg_replace('/[\\\\\/\?\*\[\]:]/', ' ', $title), 0, 31) ?: 'Hoja1');
        $all = array_merge([$headers], $rows);
        foreach ($all as $ri => $row) {
            foreach (array_values($row) as $ci => $v) {
                $v = $ri === 0 ? $v : self::safe($v);
                $coord = [$ci + 1, $ri + 1];
                if ($v === null || $v === '') {
                    continue;
                }
                is_int($v) || is_float($v)
                    ? $sheet->setCellValue($coord, $v)
                    : $sheet->setCellValueExplicit($coord, (string) $v, DataType::TYPE_STRING);
            }
        }
        $last = Coordinate::stringFromColumnIndex(max(1, count($headers)));
        $sheet->getStyle("A1:{$last}1")->getFont()->setBold(true)->getColor()->setRGB('FFFFFF');
        $sheet->getStyle("A1:{$last}1")->getFill()->setFillType(Fill::FILL_SOLID)->getStartColor()->setRGB('0A63E2');
        $sheet->freezePane('A2');
        foreach ($headers as $i => $h) {
            $w = $widths[$i] ?? max(12, min(45, mb_strlen((string) $h) + 4));
            $sheet->getColumnDimension(Coordinate::stringFromColumnIndex($i + 1))->setWidth($w);
        }
        $tmp = tempnam(sys_get_temp_dir(), 'mtw');
        IOFactory::createWriter($wb, 'Xlsx')->save($tmp);
        $out = (string) file_get_contents($tmp);
        @unlink($tmp);

        return $out;
    }

    /** CSV con `sep=;` (Excel lo abre en columnas con cualquier configuración regional) y BOM UTF-8. */
    public static function buildCsvSemicolon(array $headers, array $rows): string
    {
        return "\xEF\xBB\xBF"."sep=;\r\n".Csv::line($headers, ';').implode('', array_map(fn ($r) => Csv::line(array_map([self::class, 'safe'], $r), ';'), $rows));
    }

    /** Descarga con el tipo y el nombre correctos. */
    public static function download(string $content, string $filename)
    {
        $type = str_ends_with($filename, '.xlsx') ? self::XLSX_MIME : 'text/csv; charset=utf-8';

        return response($content, 200, ['Content-Type' => $type, 'Content-Disposition' => 'attachment; filename="'.$filename.'"']);
    }
}
