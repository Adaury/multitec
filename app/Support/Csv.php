<?php

namespace App\Support;

/** CSV con BOM UTF-8 (para que Excel en Windows lea bien tildes y ñ) y protección contra «CSV injection». */
class Csv
{
    private const FORMULA_PREFIXES = ['=', '+', '-', '@', "\t", "\r"];

    private static function cell($v): string
    {
        if ($v === null) {
            return '';
        }
        if (is_bool($v)) {
            return $v ? 'True' : 'False';
        }
        if (is_float($v)) {
            $s = (string) $v;
            if (! str_contains($s, '.') && ! str_contains($s, 'E') && ! str_contains($s, 'N') && ! str_contains($s, 'I')) {
                $s .= '.0'; // 5600 -> 5600.0, igual que el CSV de la versión original
            }

            return $s;
        }
        $s = (string) $v;
        // Un texto que empieza como fórmula se neutraliza con un apóstrofo; un número (p. ej. -150.00) no se toca.
        if ($s !== '' && in_array($s[0], self::FORMULA_PREFIXES, true) && ! preg_match('/^[+-]?\d+([.,]\d+)?$/', $s)) {
            $s = "'".$s;
        }

        return $s;
    }

    /** Una línea de CSV con el separador indicado (coma por defecto; «;» para el CSV que Excel abre en columnas). */
    public static function line(array $cells, string $delim = ','): string
    {
        $out = [];
        foreach ($cells as $c) {
            $s = self::cell($c);
            $out[] = preg_match('/["\r\n'.preg_quote($delim, '/').']/', $s) ? '"'.str_replace('"', '""', $s).'"' : $s;
        }

        return implode($delim, $out)."\r\n";
    }

    public static function build(array $headers, array $rows): string
    {
        $buf = "\xEF\xBB\xBF".self::line($headers);
        foreach ($rows as $row) {
            $buf .= self::line($row);
        }

        return $buf;
    }

    public static function response(string $content, string $filename)
    {
        return response($content, 200, ['Content-Type' => 'text/csv; charset=utf-8', 'Content-Disposition' => 'attachment; filename="'.$filename.'"']);
    }
}
