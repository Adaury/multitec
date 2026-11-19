<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Support\ApiException;
use App\Support\Audit;
use App\Support\DataCleanup;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

/** Administración → Borrar datos de prueba. Solo administradores (la ruta lleva role:admin). */
class TestDataController extends Controller
{
    /** @return array{0:array<int,int>,1:array<int,int>} */
    private function selection(Request $r): array
    {
        $ids = function (string $k) use ($r): array {
            $v = $r->input($k, []);
            if (! is_array($v) || count($v) > DataCleanup::MAX_PER_REQUEST || array_filter($v, fn ($x) => ! is_int($x) && ! (is_string($x) && ctype_digit($x)))) {
                throw new ApiException(422, "$k debe ser una lista de ids (máximo ".DataCleanup::MAX_PER_REQUEST.')');
            }

            return array_values(array_unique(array_map('intval', $v)));
        };

        return [$ids('client_ids'), $ids('product_ids')];
    }

    private function plan(Request $r): array
    {
        [$c, $p] = $this->selection($r);
        try {
            return DataCleanup::buildPlan($c, $p);
        } catch (\InvalidArgumentException $e) {
            throw new ApiException(400, $e->getMessage());
        }
    }

    public function index()
    {
        return DataCleanup::candidates();
    }

    public function preview(Request $r)
    {
        return DataCleanup::describe($this->plan($r));
    }

    public function destroy(Request $r)
    {
        $user = $r->attributes->get('user');
        if (strtoupper(trim((string) $r->input('confirm', ''))) !== DataCleanup::CONFIRM_WORD) {
            throw new ApiException(400, 'Escribe '.DataCleanup::CONFIRM_WORD.' para confirmar');
        }
        $built = $this->plan($r);
        if ($built['clients']->isEmpty() && $built['products']->isEmpty()) {
            throw new ApiException(400, 'No elegiste nada para borrar');
        }
        $summary = DataCleanup::describe($built);
        try {
            $backup = DataCleanup::backup($built['plan']); // sin copia no se borra nada
        } catch (\RuntimeException $e) {
            throw new ApiException(500, $e->getMessage());
        }
        $files = DB::transaction(function () use ($built, $user, $summary, $backup, $r) {
            $files = DataCleanup::execute($built['plan']);
            Audit::log('test_data.delete', $user, entity: 'test_data', request: $r, detail: [
                'clientes' => array_slice($summary['clients'], 0, 100), 'productos' => array_slice($summary['products'], 0, 100),
                'cantidades' => array_column($summary['counts'], 'count', 'label'),
                'facturas_con_ncf' => array_column($summary['fiscal_invoices'], 'ncf'), 'copia' => $backup,
            ]);

            return $files;
        });

        return $summary + ['backup' => $backup, 'files_removed' => DataCleanup::removeFiles($files)];
    }
}
