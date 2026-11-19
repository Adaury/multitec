<?php

namespace App\Support;

use Illuminate\Support\Facades\DB;

class Codes
{
    /**
     * Próximo correlativo por empresa y prefijo (PRY-000001). Bloquea la fila durante la transacción para que dos
     * peticiones simultáneas no obtengan el mismo número. Debe llamarse dentro de DB::transaction.
     */
    public static function next(string $prefix, int $padding = 6): string
    {
        $company = app('company_id');
        $row = DB::table('code_sequences')->where('company_id', $company)->where('prefix', $prefix)->lockForUpdate()->first();
        if (! $row) {
            DB::table('code_sequences')->insert(['company_id' => $company, 'prefix' => $prefix, 'last_value' => 0]);
            $value = 1;
        } else {
            $value = $row->last_value + 1;
        }
        DB::table('code_sequences')->where('company_id', $company)->where('prefix', $prefix)->update(['last_value' => $value]);

        return $prefix.'-'.str_pad((string) $value, $padding, '0', STR_PAD_LEFT);
    }
}
