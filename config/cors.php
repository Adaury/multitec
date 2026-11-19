<?php

/*
 * CORS. La aplicación y su API viven en el MISMO dominio (el navegador nunca cruza de origen), así que por defecto NO se
 * permite ningún otro origen: sin esto, cualquier sitio podría llamar a la API desde el navegador de un usuario con
 * sesión. Si algún día una app móvil o un sitio aparte necesita llamar a la API, se agrega su dirección exacta en
 * CORS_ALLOWED_ORIGINS (separadas por coma), nunca «*».
 */
return [
    'paths' => ['api/*'],
    'allowed_methods' => ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    'allowed_origins' => array_values(array_filter(array_map('trim', explode(',', (string) env('CORS_ALLOWED_ORIGINS', ''))))),
    'allowed_origins_patterns' => [],
    'allowed_headers' => ['Authorization', 'Content-Type', 'Accept'],
    'exposed_headers' => [],
    'max_age' => 600,
    'supports_credentials' => false,
];
