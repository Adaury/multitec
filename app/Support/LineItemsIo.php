<?php

namespace App\Support;

use App\Models\Product;
use App\Models\Quote;

/**
 * Partidas de cotización / presupuesto desde y hacia una hoja de cálculo. Descargar: las líneas con las mismas columnas
 * que se aceptan al subir (se baja, se corrige en Excel y se vuelve a cargar). Subir: uno o varios archivos con Código,
 * Descripción, Cantidad, Precio y Nota; cada línea se busca en el catálogo por código o nombre y, si se encuentra, queda
 * enlazada al producto (y toma su precio cuando el archivo no lo trae).
 */
class LineItemsIo
{
    public const HEADERS = ['Codigo', 'Descripcion', 'Cantidad', 'Unidad', 'Precio', 'Subtotal', 'Nota'];
    public const WIDTHS = [14, 46, 10, 10, 14, 14, 30];
    public const MAX_LINES = 500;
    private const ALIASES = [
        'code' => ['codigo', 'code', 'sku', 'cod'],
        'description' => ['descripcion', 'producto', 'nombre', 'articulo', 'item', 'material', 'detalle', 'concepto'],
        'quantity' => ['cantidad', 'cant', 'qty', 'unidades', 'cantidad_requerida'],
        'unit_price' => ['precio', 'precio_unitario', 'precio_unit', 'p_unit', 'costo_unitario', 'valor_unitario', 'price'],
        'note' => ['nota', 'notas', 'observacion', 'observaciones', 'comentario'],
    ];

    private static function key(string $s): string
    {
        return trim(preg_replace('/[^a-z0-9]+/', '_', CatalogImport::fold($s)), '_');
    }

    /** @return array{0:string,1:string} [contenido, nombre] */
    public static function export(Quote $q, string $fmt): array
    {
        $q->loadMissing('items');
        $ids = $q->items->pluck('product_id')->filter()->all();
        $products = $ids ? Product::whereIn('id', $ids)->get()->keyBy('id') : collect();
        $rows = [];
        foreach ($q->items as $it) {
            $p = $products[$it->product_id] ?? null;
            $rows[] = [$p?->code ?? '', $it->description, (float) $it->quantity, $p?->unit ?? '', (float) $it->unit_price, (float) $it->subtotal, $it->note ?: ''];
        }
        $rows[] = [];
        $rows[] = ['', 'Subtotal', '', '', '', (float) $q->subtotal, ''];
        $rows[] = ['', 'ITBIS (18%)', '', '', '', (float) $q->itbis, ''];
        $rows[] = ['', 'TOTAL', '', '', '', (float) $q->total, ''];
        $name = $q->code.'-partidas';

        return $fmt === 'xlsx'
            ? [Spreadsheets::buildXlsx(self::HEADERS, $rows, $q->code, self::WIDTHS), "$name.xlsx"]
            : [Spreadsheets::buildCsvSemicolon(self::HEADERS, $rows), "$name.csv"];
    }

    /** @return array{0:string,1:string} */
    public static function template(string $fmt): array
    {
        $rows = [
            ['', 'Cámara IP 4MP domo', 4, 'unidad', '', '', 'Una por esquina'],
            ['', 'Sensor de movimiento PIR', 3, 'unidad', '', '', ''],
            ['', 'Taco plástico 1/4" (bolsa 100)', 1, 'bolsa', '', '', ''],
        ];

        return $fmt === 'xlsx'
            ? [Spreadsheets::buildXlsx(self::HEADERS, $rows, 'Partidas', self::WIDTHS), 'plantilla_partidas.xlsx']
            : [Spreadsheets::buildCsvSemicolon(self::HEADERS, $rows), 'plantilla_partidas.csv'];
    }

    /**
     * Lee las partidas de los archivos. No guarda nada: la pantalla las agrega a la cotización que se edita.
     *
     * @param array<int, array{0:string,1:string}> $files [nombre, contenido]
     * @throws \InvalidArgumentException
     */
    public static function parse(array $files): array
    {
        $byCode = [];
        $byName = [];
        foreach (Product::all() as $p) {
            $byCode[strtoupper($p->code)] = $p;
            $byName[CatalogImport::fold($p->name)] ??= $p;
            foreach ($p->synonyms ?: [] as $syn) {
                $byName[CatalogImport::fold((string) $syn)] ??= $p;
            }
        }
        $items = [];
        $warnings = [];
        foreach ($files as [$filename, $data]) {
            try {
                $rows = Spreadsheets::readRows($data, $filename);
            } catch (\InvalidArgumentException $e) {
                throw new \InvalidArgumentException("$filename: ".$e->getMessage());
            }
            $headerAt = null;
            foreach ($rows as $i => $r) {
                if (array_filter($r, fn ($c) => trim($c) !== '')) {
                    $headerAt = $i;
                    break;
                }
            }
            if ($headerAt === null) {
                $warnings[] = "$filename: está vacío";
                continue;
            }
            $columns = [];
            foreach ($rows[$headerAt] as $i => $title) {
                foreach (self::ALIASES as $field => $names) {
                    if (in_array(self::key($title), $names, true)) {
                        if (! in_array($field, $columns, true)) {
                            $columns[$i] = $field;
                        }
                        break;
                    }
                }
            }
            if (! in_array('description', $columns, true) && ! in_array('code', $columns, true)) {
                throw new \InvalidArgumentException("$filename: falta la columna 'Descripcion' (o 'Codigo'). Usa la plantilla de partidas.");
            }
            foreach (array_slice($rows, $headerAt + 1, null, true) as $idx => $raw) {
                $number = $idx + 1;
                $v = [];
                foreach ($columns as $i => $field) {
                    if (isset($raw[$i]) && trim($raw[$i]) !== '') {
                        $v[$field] = trim($raw[$i]);
                    }
                }
                if (! $v) {
                    continue;
                }
                $description = $v['description'] ?? '';
                // Las filas de totales de un archivo descargado (Subtotal, ITBIS, TOTAL) no son partidas.
                $folded = CatalogImport::fold($description);
                if (empty($v['code']) && (str_starts_with($folded, 'subtotal') || str_starts_with($folded, 'itbis') || str_starts_with($folded, 'total'))) {
                    continue;
                }
                $product = ! empty($v['code']) ? ($byCode[strtoupper($v['code'])] ?? null) : null;
                if (! $product && $description !== '') {
                    $product = $byName[CatalogImport::fold($description)] ?? null;
                }
                if ($description === '' && ! $product) {
                    $warnings[] = "$filename, fila $number: no existe el código ".($v['code'] ?? '');
                    continue;
                }
                try {
                    $qty = isset($v['quantity']) ? CatalogImport::parseNumber($v['quantity']) : 1.0;
                    $price = isset($v['unit_price']) ? CatalogImport::parseNumber($v['unit_price']) : null;
                } catch (\InvalidArgumentException $e) {
                    $warnings[] = "$filename, fila $number: ".$e->getMessage();
                    continue;
                }
                if ($qty <= 0) {
                    $warnings[] = "$filename, fila $number: cantidad 0 o negativa, se omitió";
                    continue;
                }
                if ($price === null) {
                    $price = $product ? (float) $product->price : 0.0;
                    if (! $product) {
                        $warnings[] = "$filename, fila $number: «{$description}» no está en el catálogo ni trae precio";
                    }
                }
                $items[] = ['product_id' => $product?->id, 'description' => $description !== '' ? $description : $product->name,
                    'quantity' => $qty, 'unit_price' => round($price, 2), 'note' => $v['note'] ?? null];
                if (count($items) > self::MAX_LINES) {
                    throw new \InvalidArgumentException('Hay más de '.self::MAX_LINES.' partidas; divide los archivos');
                }
            }
        }

        return ['items' => $items, 'warnings' => $warnings, 'matched' => count(array_filter($items, fn ($i) => $i['product_id']))];
    }
}
