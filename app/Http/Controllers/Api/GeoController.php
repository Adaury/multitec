<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Support\ApiException;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class GeoController extends Controller
{
    private const URL = 'https://nominatim.openstreetmap.org/search';
    private const USER_AGENT = 'Multitec-ERP/1.0 (+https://github.com/Adaury/multitec)'; // Nominatim exige identificar la aplicación
    private const FOUND_TTL = 30 * 24 * 3600;
    private const MISSING_TTL = 6 * 3600;

    /**
     * Convierte una dirección escrita en coordenadas para mostrar el mapa del proyecto, con OpenStreetMap (gratis, sin
     * clave). Solo sale la dirección, sin nombres ni más datos, acotada a los países configurados (GEO_COUNTRY_CODES, por
     * defecto República Dominicana): un mapa equivocado es peor que ninguno. Lo ya buscado se guarda para no repetir
     * consultas (Nominatim pide máximo 1 por segundo).
     */
    public function search(Request $r)
    {
        $q = trim((string) $r->query('q', ''));
        if (mb_strlen($q) < 5 || mb_strlen($q) > 300) {
            throw new ApiException(422, 'La dirección debe tener entre 5 y 300 caracteres');
        }
        $key = 'geo:'.sha1(implode(' ', preg_split('/\s+/', mb_strtolower($q))));
        $hit = Cache::get($key);
        if ($hit !== null) {
            if ($hit === false) {
                throw new ApiException(404, 'No se encontró esa dirección en el mapa');
            }

            return $hit;
        }

        try {
            // A lo sumo una consulta por segundo hacia Nominatim.
            Cache::lock('geo:nominatim', 10)->block(8, function () {
                $wait = 1.0 - (microtime(true) - (float) Cache::get('geo:last', 0));
                if ($wait > 0) {
                    usleep((int) ($wait * 1_000_000));
                }
                Cache::put('geo:last', microtime(true), 60);
            });
            $params = ['q' => implode(' ', preg_split('/\s+/', mb_strtolower($q))), 'format' => 'jsonv2', 'limit' => 1];
            $countries = implode(',', array_filter(array_map(fn ($c) => strtolower(trim($c)), explode(',', (string) config('app.geo_country_codes')))));
            if ($countries !== '') {
                $params['countrycodes'] = $countries;
            }
            $res = Http::withHeaders(['User-Agent' => self::USER_AGENT])->timeout(6)->get(self::URL, $params)->throw()->json();
        } catch (\Throwable $e) {
            Log::warning('No se pudo consultar Nominatim para una dirección: '.$e->getMessage());
            throw new ApiException(503, 'El mapa no está disponible ahora. Usa «Cómo llegar».');
        }

        if (empty($res)) {
            Cache::put($key, false, self::MISSING_TTL);
            throw new ApiException(404, 'No se encontró esa dirección en el mapa');
        }
        $found = ['lat' => (float) $res[0]['lat'], 'lng' => (float) $res[0]['lon'], 'display_name' => $res[0]['display_name'] ?? ''];
        Cache::put($key, $found, self::FOUND_TTL);

        return $found;
    }
}
