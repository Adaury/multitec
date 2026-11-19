<?php

namespace App\Support;

use App\Models\Client;
use App\Models\NcfSequence;
use Illuminate\Support\Carbon;

class Ncf
{
    /** B01 (crédito fiscal) si el cliente tiene RNC; B02 (consumo) para consumidor final. */
    public static function defaultType(Client $client): string
    {
        return $client->rnc ? 'B01' : 'B02';
    }

    public static function today(): string
    {
        return Carbon::now('America/Santo_Domingo')->toDateString();
    }

    /**
     * Toma el siguiente número de una secuencia activa y vigente del tipo pedido, lo consume y devuelve el NCF.
     * Bloquea la fila: dos facturas a la vez no obtienen el mismo número. Debe llamarse dentro de una transacción.
     */
    public static function assign(string $type): string
    {
        $seq = NcfSequence::where('ncf_type', $type)->where('active', true)
            ->where('expires_at', '>=', self::today())->whereColumn('next_number', '<=', 'range_end')
            ->orderBy('expires_at')->orderBy('id')->lockForUpdate()->first();
        if (! $seq) {
            throw new ApiException(400, "No hay una secuencia NCF activa y vigente para el tipo $type. Registra un nuevo rango autorizado por la DGII en Configuración > NCF.");
        }
        $ncf = $type.str_pad((string) $seq->next_number, 8, '0', STR_PAD_LEFT);
        $seq->update(['next_number' => $seq->next_number + 1]);

        return $ncf;
    }
}
