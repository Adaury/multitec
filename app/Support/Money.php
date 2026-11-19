<?php

namespace App\Support;

/**
 * Dinero en centavos enteros: sin errores de coma flotante. Redondeo "medio hacia arriba" (el habitual en
 * facturación). Cantidades y precios llevan 2 decimales, así que cantidad × precio es exacto en diezmilésimas.
 */
class Money
{
    public static function cents($v): int
    {
        return (int) round(((float) $v) * 100);
    }

    public static function fromCents(int $c): float
    {
        return $c / 100;
    }

    /** Subtotal de una línea en centavos: cantidad × precio, redondeado al centavo. */
    public static function line($qty, $price): int
    {
        $x = self::cents($qty) * self::cents($price); // diezmilésimas
        return intdiv($x + ($x >= 0 ? 50 : -50), 100);
    }

    /** ITBIS de un subtotal en centavos (tasa en puntos base: 0.18 → 1800). */
    public static function tax(int $subtotalCents, ?float $rate = null): int
    {
        $bp = (int) round(($rate ?? (float) config('app.itbis_rate', 0.18)) * 10000);
        $x = $subtotalCents * $bp;

        return intdiv($x + ($x >= 0 ? 5000 : -5000), 10000);
    }

    /**
     * @param iterable<array{quantity:mixed,unit_price:mixed}|object> $lines
     * @return array{0:float,1:float,2:float} [subtotal, itbis, total]
     */
    public static function totals(iterable $lines, ?float $rate = null): array
    {
        $sub = 0;
        foreach ($lines as $l) {
            $sub += self::line(is_array($l) ? $l['quantity'] : $l->quantity, is_array($l) ? $l['unit_price'] : $l->unit_price);
        }
        $tax = self::tax($sub, $rate);

        return [self::fromCents($sub), self::fromCents($tax), self::fromCents($sub + $tax)];
    }

    /** Suma de líneas sin impuesto (el presupuesto muestra solo el total). */
    public static function sum(iterable $lines): float
    {
        $sub = 0;
        foreach ($lines as $l) {
            $sub += self::line($l->quantity, $l->unit_price);
        }

        return self::fromCents($sub);
    }
}
