<?php

namespace App\Support;

/** Validaciones pequeñas con mensajes 422 al estilo de la API original. */
class V
{
    public static function text($v, int $max, string $field, bool $required = false): ?string
    {
        if ($v === null || (is_string($v) && trim($v) === '' && ! $required)) {
            if ($required) {
                throw new ApiException(422, "El campo $field es obligatorio");
            }

            return $v === null ? null : (string) $v;
        }
        if (! is_scalar($v)) {
            throw new ApiException(422, "El campo $field no es válido");
        }
        $v = (string) $v;
        if ($required && trim($v) === '') {
            throw new ApiException(422, "El campo $field es obligatorio");
        }
        if (mb_strlen($v) > $max) {
            throw new ApiException(422, "El campo $field excede $max caracteres");
        }

        return $v;
    }

    /** Número decimal. $gt: debe ser mayor que; $ge: mayor o igual. */
    public static function num($v, string $field, ?float $ge = null, ?float $gt = null): ?float
    {
        if ($v === null || $v === '') {
            return null;
        }
        if (! is_numeric($v)) {
            throw new ApiException(422, "El campo $field debe ser un número");
        }
        $v = (float) $v;
        if ($ge !== null && $v < $ge) {
            throw new ApiException(422, "El campo $field debe ser mayor o igual a $ge");
        }
        if ($gt !== null && $v <= $gt) {
            throw new ApiException(422, "El campo $field debe ser mayor que $gt");
        }

        return $v;
    }

    public static function int($v, string $field, ?int $gt = null): ?int
    {
        if ($v === null || $v === '') {
            return null;
        }
        if (! is_numeric($v) || (float) $v != (int) $v) {
            throw new ApiException(422, "El campo $field debe ser un número entero");
        }
        if ($gt !== null && (int) $v <= $gt) {
            throw new ApiException(422, "El campo $field debe ser mayor que $gt");
        }

        return (int) $v;
    }

    /** Lista de textos (tags, sinónimos). */
    public static function strings($v, string $field): array
    {
        if ($v === null) {
            return [];
        }
        if (! is_array($v)) {
            throw new ApiException(422, "El campo $field debe ser una lista");
        }
        foreach ($v as $item) {
            if (! is_string($item)) {
                throw new ApiException(422, "El campo $field debe contener solo textos");
            }
        }

        return array_values($v);
    }

    /** Cantidad sin ceros sobrantes (como {x:g} de Python): 5.00 -> 5, 2.50 -> 2.5 */
    public static function g(float $n): string
    {
        return rtrim(rtrim(number_format($n, 2, '.', ''), '0'), '.');
    }
}
