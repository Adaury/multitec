<?php

namespace App\Support;

use App\Models\Category;
use App\Models\Product;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

/**
 * Importación masiva de productos del catálogo desde uno o varios archivos CSV o Excel (.xlsx). Reglas, a propósito
 * conservadoras (las mismas del sistema original):
 *  - Una celda vacía NUNCA borra un dato que el producto ya tiene: solo se actualiza lo que viene lleno.
 *  - Un producto existente se reconoce por su `codigo` o, si no viene, por su nombre (sin importar mayúsculas ni tildes);
 *    si existe se actualiza, si no se crea.
 *  - Un producto nuevo necesita categoría («Cámaras IP» o la ruta «CCTV > Cámaras IP»).
 *  - Las filas con error no frenan al resto: se informan una por una.
 *  - dry_run calcula y devuelve el mismo resumen sin tocar la base de datos.
 *  - Con create_categories, una categoría que no existe se crea (con su ruta, «Alarmas > Sirenas»).
 *  - Varios archivos se procesan como uno solo: un producto del primero ya «existe» para el segundo.
 */
class CatalogImport
{
    public const MAX_ROWS = 2000;
    public const EXAMPLE_PREFIX = 'ejemplo';
    public const HEADERS = ['Nombre', 'Categoria', 'Unidad', 'Precio', 'Costo', 'Marca', 'Modelo', 'Descripcion', 'Etiquetas', 'Sinonimos', 'Codigo'];
    public const WIDTHS = [42, 34, 10, 12, 12, 14, 14, 40, 30, 26, 14];
    private const EXAMPLES = [
        ['EJEMPLO Camara IP 4MP bala', 'Camaras Bullet', 'unidad', '3500', '2400', 'Hikvision', 'DS-2CD1043', 'Camara IP 4MP exterior', 'camara;ip;4mp', 'camara bala;camara exterior', ''],
        ['EJEMPLO Caja de cable UTP Cat6 305m', 'UTP Categoria 6', 'caja', '6800', '5200', '', '', '', 'cable;utp;caja de cable', 'caja de utp', ''],
    ];

    /** Encabezado normalizado -> campo interno. */
    private const ALIASES = [
        'name' => ['nombre', 'producto', 'articulo', 'item', 'name'],
        'category' => ['categoria', 'category', 'grupo', 'linea'],
        'unit' => ['unidad', 'unit', 'und', 'unidad_de_venta'],
        'price' => ['precio', 'precio_venta', 'precio_de_venta', 'price', 'pvp'],
        'cost' => ['costo', 'cost', 'costo_unitario', 'precio_costo'],
        'brand' => ['marca', 'brand'],
        'model' => ['modelo', 'model'],
        'commercial_description' => ['descripcion', 'descripcion_comercial', 'description'],
        'technical_description' => ['descripcion_tecnica', 'ficha_tecnica', 'especificaciones'],
        'notes' => ['notas', 'nota', 'observaciones'],
        'tags' => ['etiquetas', 'tags', 'palabras_clave'],
        'synonyms' => ['sinonimos', 'synonyms', 'tambien_conocido_como'],
        'install_minutes' => ['minutos_instalacion', 'minutos_de_instalacion', 'install_minutes', 'minutos'],
        'labor_role' => ['rol_mano_obra', 'rol', 'labor_role', 'rol_de_mano_de_obra'],
        'resolution_mp' => ['resolucion_mp', 'megapixeles', 'mp', 'resolucion'],
        'storage_capacity_gb' => ['almacenamiento_gb', 'capacidad_gb', 'storage_capacity_gb'],
        'channel_capacity' => ['canales', 'puertos', 'capacidad_canales', 'channel_capacity'],
        'pack_size' => ['unidades_por_paquete', 'unidades_por_bolsa', 'unidades_por_caja', 'pack_size', 'paquete_de'],
        'priority' => ['prioridad', 'priority'],
        'code' => ['codigo', 'code', 'sku'],
    ];
    private const NUMERIC = ['price', 'cost', 'install_minutes', 'resolution_mp', 'storage_capacity_gb'];
    private const INTEGER = ['channel_capacity', 'priority', 'pack_size'];
    private const LISTS = ['tags', 'synonyms'];
    /** Largo máximo de los textos (los mismos topes de ProductCreate / ProductUpdate). */
    private const MAXLEN = ['name' => 255, 'unit' => 30, 'notes' => 2000, 'brand' => 80, 'model' => 80, 'commercial_description' => 2000,
        'technical_description' => 2000, 'labor_role' => 80];

    // ---- utilidades ---------------------------------------------------------------------------

    public static function fold(string $s): string
    {
        return trim(preg_replace('/\s+/u', ' ', mb_strtolower(Str::ascii($s))));
    }

    private static function headerKey(string $s): string
    {
        return trim(preg_replace('/[^a-z0-9]+/', '_', self::fold($s)), '_');
    }

    /** Acepta "1250", "1,250.50", "1.250,50", "RD$ 3,500" y "3500,5". */
    public static function parseNumber(string $raw): float
    {
        $t = preg_replace('/[^\d,.\-]/', '', trim($raw));
        if ($t === '' || strpbrk($t, '0123456789') === false) {
            throw new \InvalidArgumentException("'$raw' no es un número");
        }
        if (str_contains($t, ',') && str_contains($t, '.')) {
            // El último separador es el decimal; el otro es de miles.
            $t = strrpos($t, ',') > strrpos($t, '.') ? str_replace(',', '.', str_replace('.', '', $t)) : str_replace(',', '', $t);
        } elseif (str_contains($t, ',')) {
            // "3500,5" -> decimal; "3,500" -> miles.
            $t = preg_match('/,\d{1,2}$/', $t) ? str_replace(',', '.', $t) : str_replace(',', '', $t);
        }
        if (! is_numeric($t)) {
            throw new \InvalidArgumentException("'$raw' no es un número");
        }

        return (float) $t;
    }

    private static function splitList(string $raw): array
    {
        $seen = [];
        foreach (preg_split('/[;|,]/', $raw) as $p) {
            $v = trim($p);
            if ($v !== '' && ! in_array(mb_strtolower($v), array_map('mb_strtolower', $seen), true)) {
                $seen[] = $v;
            }
        }

        return $seen;
    }

    // ---- plantillas y exportación -----------------------------------------------------------------

    private static function kits(): array
    {
        static $k;

        return $k ??= json_decode((string) file_get_contents(database_path('data/kits.json')), true) ?: ['order' => [], 'kits' => []];
    }

    public static function kitSummary(): array
    {
        $k = self::kits();

        return array_map(fn ($kind) => ['kind' => $kind, 'label' => $k['kits'][$kind]['label'], 'file' => $k['kits'][$kind]['file'], 'items' => count($k['kits'][$kind]['rows'])], $k['order']);
    }

    public static function kitKinds(): array
    {
        return self::kits()['order'];
    }

    public static function kitRows(string $kind): array
    {
        return self::kits()['kits'][$kind]['rows'];
    }

    public static function allKitRows(): array
    {
        $rows = [];
        foreach (self::kitKinds() as $k) {
            $rows = array_merge($rows, self::kitRows($k));
        }

        return $rows;
    }

    /** Plantilla por tipo («general» o un tipo de lista) en CSV o Excel. @return array{0:string,1:string} [contenido, nombre] */
    public static function templateFile(string $kind, string $fmt): array
    {
        if ($kind === 'general') {
            $name = 'plantilla_catalogo';
            $rows = self::EXAMPLES;
        } elseif (in_array($kind, self::kitKinds(), true)) {
            $name = self::kits()['kits'][$kind]['file'];
            $rows = self::kitRows($kind);
        } else {
            throw new \InvalidArgumentException('Tipo de plantilla desconocido');
        }
        if ($fmt === 'xlsx') {
            return [Spreadsheets::buildXlsx(self::HEADERS, $rows, 'Productos', self::WIDTHS), "$name.xlsx"];
        }

        return [Spreadsheets::buildCsvSemicolon(self::HEADERS, $rows), "$name.csv"];
    }

    /** Todo el catálogo con las mismas columnas de la plantilla: se edita en Excel y se vuelve a subir (el código actualiza). */
    public static function export(string $fmt): array
    {
        $cats = Category::all()->keyBy('id');
        $path = function (?int $id) use ($cats) {
            $parts = [];
            for ($n = $id ? ($cats[$id] ?? null) : null, $i = 0; $n && $i < 50; $n = $n->parent_id ? ($cats[$n->parent_id] ?? null) : null, $i++) {
                $parts[] = $n->name;
            }

            return implode(' > ', array_reverse($parts));
        };
        $rows = [];
        foreach (Product::orderBy('code')->get() as $p) {
            $rows[] = [$p->name, $path($p->category_id), $p->unit, (float) $p->price, $p->cost !== null ? (float) $p->cost : '', $p->brand ?: '',
                $p->model ?: '', $p->commercial_description ?: '', implode(';', $p->tags ?: []), implode(';', $p->synonyms ?: []), $p->code];
        }
        if ($fmt === 'xlsx') {
            return [Spreadsheets::buildXlsx(self::HEADERS, $rows, 'Catálogo', self::WIDTHS), 'catalogo.xlsx'];
        }

        return [Spreadsheets::buildCsvSemicolon(self::HEADERS, $rows), 'catalogo.csv'];
    }

    // ---- categorías (por nombre o ruta) ----------------------------------------------------------------

    /** Índice de categorías para buscar por ruta («CCTV > Cámaras IP») o por nombre suelto; puede crear las que falten. */
    private static function categoryIndex(): array
    {
        $all = Category::all();
        $byId = $all->keyBy('id');
        $byPath = [];
        $byName = [];
        foreach ($all as $c) {
            $parts = [];
            for ($n = $c, $i = 0; $n && $i < 50; $n = $byId[$n->parent_id] ?? null, $i++) {
                array_unshift($parts, $n->name);
            }
            $byPath[self::fold(implode(' > ', $parts))] = $c;
            $byName[self::fold($c->name)][] = $c;
        }

        return [&$byPath, &$byName];
    }

    /** @return array{0:?Category,1:?string} [categoría, problema] */
    private static function findCategory(string $raw, array $byPath, array $byName): array
    {
        $key = self::fold(preg_replace('/\s*[>\/]\s*/', ' > ', $raw));
        if (isset($byPath[$key])) {
            return [$byPath[$key], null];
        }
        $m = $byName[$key] ?? [];
        if (count($m) === 1) {
            return [$m[0], null];
        }
        if (count($m) > 1) {
            return [null, "La categoría '$raw' existe en varias ramas; escribe la ruta completa (p. ej. 'Cableado > Otros')"];
        }

        return [null, "La categoría '$raw' no existe"];
    }

    private static function uniqueSlug(string $name, array &$taken): string
    {
        $base = Str::slug($name) ?: 'categoria';
        $slug = $base;
        for ($n = 2; isset($taken[$slug]) || Category::where('slug', $slug)->exists(); $n++) {
            $slug = $base.'-'.$n;
        }
        $taken[$slug] = true;

        return $slug;
    }

    /** @return array{0:?Category,1:?string,2:array<int,string>} [categoría, problema, rutas creadas] */
    private static function findOrCreateCategory(string $raw, array &$byPath, array &$byName, array &$slugs, bool $dry): array
    {
        [$found, $problem] = self::findCategory($raw, $byPath, $byName);
        if ($found || ($problem && str_contains($problem, 'varias ramas'))) {
            return [$found, $problem, []];
        }
        $parts = array_values(array_filter(array_map('trim', preg_split('/\s*[>\/]\s*/', $raw))));
        if (! $parts) {
            return [null, 'Falta la categoría', []];
        }
        $created = [];
        $parent = null;
        foreach ($parts as $d => $_) {
            $key = self::fold(implode(' > ', array_slice($parts, 0, $d + 1)));
            $node = $byPath[$key] ?? null;
            if (! $node && $d === 0) {
                // Un primer nivel escrito solo («Alarmas») puede ser una categoría que ya existe en otra rama.
                $m = array_values(array_filter($byName[self::fold($parts[0])] ?? [], fn ($c) => $c->parent_id === null));
                $node = count($m) === 1 ? $m[0] : null;
            }
            if (! $node) {
                $attrs = ['name' => mb_substr($parts[$d], 0, 120), 'slug' => self::uniqueSlug($parts[$d], $slugs), 'parent_id' => $parent?->id, 'created_at' => now()];
                $node = $dry ? (new Category($attrs))->forceFill(['id' => 0]) : Category::create($attrs);
                $created[] = implode(' > ', array_slice($parts, 0, $d + 1));
                $byPath[$key] = $node;
                $byName[self::fold($parts[$d])][] = $node;
            }
            $parent = $node;
        }

        return [$parent, null, $created];
    }

    // ---- importación ---------------------------------------------------------------------------------

    /** Valida lo que viene de una fila contra los mismos topes que ProductCreate/ProductUpdate. @return string|null mensaje de error */
    private static function validate(array $f): ?string
    {
        $errors = [];
        foreach (self::MAXLEN as $k => $max) {
            if (isset($f[$k]) && mb_strlen((string) $f[$k]) > $max) {
                $errors[] = "$k: máximo $max caracteres";
            }
        }
        foreach (['storage_capacity_gb', 'pack_size'] as $k) {
            if (isset($f[$k]) && $f[$k] <= 0) {
                $errors[] = "$k: debe ser mayor que 0";
            }
        }

        return $errors ? implode('; ', $errors) : null;
    }

    /**
     * @param array<int, array{0:string,1:string}> $files [nombre, contenido]
     * @return array<string,mixed>
     * @throws \InvalidArgumentException con un mensaje listo para mostrar
     */
    public static function import(array $files, ?int $userId, bool $dry, bool $createCategories = false, bool $onlyCreate = false): array
    {
        if (! $files) {
            throw new \InvalidArgumentException('No llegó ningún archivo');
        }
        $multi = count($files) > 1;
        $ignored = [];
        $parsed = [];
        foreach ($files as [$filename, $data]) {
            try {
                $rows = Spreadsheets::readRows($data, $filename);
            } catch (\InvalidArgumentException $e) {
                throw new \InvalidArgumentException("$filename: ".$e->getMessage());
            }
            if (! array_filter($rows, fn ($r) => array_filter($r, fn ($c) => trim($c) !== ''))) {
                throw new \InvalidArgumentException("$filename: el archivo está vacío");
            }
            $headerAt = 0;
            foreach ($rows as $i => $r) {
                if (array_filter($r, fn ($c) => trim($c) !== '')) {
                    $headerAt = $i;
                    break;
                }
            }
            $columns = [];
            foreach ($rows[$headerAt] as $i => $title) {
                $field = null;
                foreach (self::ALIASES as $f => $names) {
                    if (in_array(self::headerKey($title), $names, true)) {
                        $field = $f;
                        break;
                    }
                }
                if ($field && ! in_array($field, $columns, true)) {
                    $columns[$i] = $field;
                } elseif (trim($title) !== '' && ! in_array(trim($title), $ignored, true)) {
                    $ignored[] = trim($title);
                }
            }
            if (! in_array('name', $columns, true)) {
                throw new \InvalidArgumentException(($multi ? "$filename: " : '')."Falta la columna 'Nombre' (o 'Producto'). Usa la plantilla para empezar.");
            }
            $dataRows = array_slice($rows, $headerAt + 1);
            if (count($dataRows) > self::MAX_ROWS) {
                throw new \InvalidArgumentException("$filename: tiene más de ".self::MAX_ROWS.' filas; divídelo en partes');
            }
            $parsed[] = [$filename, $columns, $dataRows];
        }

        [$byPath, $byName] = self::categoryIndex();
        $slugs = [];
        $byCode = [];
        $byProdName = [];
        foreach (Product::all() as $p) {
            $byCode[strtoupper($p->code)] = $p;
            $byProdName[self::fold($p->name)] = $p;
        }
        $results = [];
        $counts = ['created' => 0, 'updated' => 0, 'skipped' => 0, 'errors' => 0];
        $newCategories = [];
        $current = '';
        $add = function (string $action, int $row, string $name, string $msg = '') use (&$counts, &$results, &$current, $multi) {
            $counts[['create' => 'created', 'update' => 'updated', 'skip' => 'skipped', 'error' => 'errors'][$action]]++;
            $r = ['row' => $row, 'action' => $action, 'name' => $name, 'message' => $msg];
            if ($multi) {
                $r['file'] = $current;
            }
            $results[] = $r;
        };

        $run = function () use ($parsed, &$byPath, &$byName, &$slugs, &$byCode, &$byProdName, &$newCategories, &$current, $add, $dry, $createCategories, $onlyCreate, $userId) {
            foreach ($parsed as [$filename, $columns, $dataRows]) {
                $current = $filename;
                foreach ($dataRows as $idx => $raw) {
                    $rowNumber = $idx + 2;
                    if (! array_filter($raw, fn ($c) => trim($c) !== '')) {
                        continue;
                    }
                    $values = [];
                    foreach ($columns as $i => $field) {
                        if (isset($raw[$i]) && trim($raw[$i]) !== '') {
                            $values[$field] = trim($raw[$i]);
                        }
                    }
                    $name = $values['name'] ?? '';
                    if ($name === '') {
                        $add('error', $rowNumber, '', 'Falta el nombre');
                        continue;
                    }
                    if (str_starts_with(self::fold($name), self::EXAMPLE_PREFIX)) {
                        $add('skip', $rowNumber, $name, 'Fila de ejemplo de la plantilla');
                        continue;
                    }
                    $fields = [];
                    try {
                        foreach ($values as $f => $rawv) {
                            if (in_array($f, ['name', 'category', 'code'], true)) {
                                continue;
                            }
                            if (in_array($f, self::NUMERIC, true)) {
                                $fields[$f] = self::parseNumber($rawv);
                            } elseif (in_array($f, self::INTEGER, true)) {
                                $fields[$f] = (int) round(self::parseNumber($rawv));
                            } elseif (in_array($f, self::LISTS, true)) {
                                $fields[$f] = self::splitList($rawv);
                            } else {
                                $fields[$f] = $rawv;
                            }
                        }
                    } catch (\InvalidArgumentException $e) {
                        $add('error', $rowNumber, $name, $e->getMessage());
                        continue;
                    }

                    $category = null;
                    if (isset($values['category'])) {
                        if ($createCategories) {
                            [$category, $problem, $made] = self::findOrCreateCategory($values['category'], $byPath, $byName, $slugs, $dry);
                            foreach ($made as $m) {
                                if (! in_array($m, $newCategories, true)) {
                                    $newCategories[] = $m;
                                }
                            }
                        } else {
                            [$category, $problem] = self::findCategory($values['category'], $byPath, $byName);
                        }
                        if ($problem) {
                            $add('error', $rowNumber, $name, $problem);
                            continue;
                        }
                    }

                    $existing = null;
                    if (isset($values['code'])) {
                        $existing = $byCode[strtoupper($values['code'])] ?? null;
                        if (! $existing) {
                            $add('error', $rowNumber, $name, "No existe un producto con el código {$values['code']}");
                            continue;
                        }
                    }
                    $existing ??= $byProdName[self::fold($name)] ?? null;
                    if ($existing && $onlyCreate) {
                        $add('skip', $rowNumber, $name, "Ya está en tu catálogo ({$existing->code})");
                        continue;
                    }

                    $check = $fields + (isset($values['code']) ? ['name' => $name] : (! $existing ? ['name' => $name] : []));
                    if ($msg = self::validate($check)) {
                        $add('error', $rowNumber, $name, $msg);
                        continue;
                    }
                    if ($existing) {
                        if (! $dry) {
                            $upd = $fields;
                            if ($category) {
                                $upd['category_id'] = $category->id;
                            }
                            if (isset($values['code'])) {
                                $upd['name'] = $name;
                            }
                            $existing->update($upd + ['updated_at' => now()]);
                        }
                        $add('update', $rowNumber, $existing->name, 'Actualiza '.$existing->code);
                    } else {
                        if (! $category) {
                            $add('error', $rowNumber, $name, 'Falta la categoría (producto nuevo)');
                            continue;
                        }
                        $noPrice = ! array_key_exists('price', $fields);
                        if (! $dry) {
                            $p = new Product($fields + ['name' => $name]);
                            $p->code = Codes::next(Product::resolvePrefix($category->loadMissing('parent')));
                            $p->category_id = $category->id;
                            $p->created_by = $userId;
                            $p->created_at = now();
                            $p->price = $fields['price'] ?? 0;
                            if ($noPrice) {
                                $p->price_estimated = true;
                            }
                            $p->save();
                            $byProdName[self::fold($name)] = $p;
                            $byCode[strtoupper($p->code)] = $p;
                        } else {
                            // Dos filas con el mismo nombre en el archivo: la segunda actualiza a la primera.
                            $byProdName[self::fold($name)] = (new Product(['name' => $name]))->forceFill(['code' => '(nuevo)']);
                        }
                        $add('create', $rowNumber, $name, "Nuevo en {$category->name}".($noPrice ? ' · sin precio: complétalo' : ''));
                    }
                }
            }
        };
        $dry ? $run() : DB::transaction($run); // todo o nada: una falla a medias no deja medio catálogo cargado

        return $counts + [
            'dry_run' => $dry, 'ignored_columns' => $ignored, 'new_categories' => $newCategories,
            'files' => array_map(fn ($f) => $f[0], $files), 'rows' => array_slice($results, 0, 500),
        ];
    }

    /** Primeros niveles nuevos (Alarmas, Cerco Eléctrico…) con su prefijo de código; devuelve los nombres creados. */
    public static function ensureRoots(): array
    {
        $roots = [];
        foreach (Category::whereNull('parent_id')->get() as $c) {
            $roots[self::fold($c->name)] = $c;
        }
        $created = [];
        foreach (self::kits()['roots'] ?? [] as $name => $prefix) {
            $found = $roots[self::fold($name)] ?? null;
            if (! $found) {
                $taken = [];
                Category::create(['name' => $name, 'slug' => self::uniqueSlug($name, $taken), 'code_prefix' => $prefix, 'created_at' => now()]);
                $created[] = $name;
            } elseif (! $found->code_prefix) {
                $found->update(['code_prefix' => $prefix]);
            }
        }

        return $created;
    }
}
