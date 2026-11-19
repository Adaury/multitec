<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Application Name
    |--------------------------------------------------------------------------
    |
    | This value is the name of your application, which will be used when the
    | framework needs to place the application's name in a notification or
    | other UI elements where an application name needs to be displayed.
    |
    */

    'name' => env('APP_NAME', 'Laravel'),

    /*
    |--------------------------------------------------------------------------
    | Application Environment
    |--------------------------------------------------------------------------
    |
    | This value determines the "environment" your application is currently
    | running in. This may determine how you prefer to configure various
    | services the application utilizes. Set this in your ".env" file.
    |
    */

    'env' => env('APP_ENV', 'production'),

    /*
    |--------------------------------------------------------------------------
    | Application Debug Mode
    |--------------------------------------------------------------------------
    |
    | When your application is in debug mode, detailed error messages with
    | stack traces will be shown on every error that occurs within your
    | application. If disabled, a simple generic error page is shown.
    |
    */

    'debug' => (bool) env('APP_DEBUG', false),

    /*
    |--------------------------------------------------------------------------
    | Application URL
    |--------------------------------------------------------------------------
    |
    | This URL is used by the console to properly generate URLs when using
    | the Artisan command line tool. You should set this to the root of
    | the application so that it's available within Artisan commands.
    |
    */

    'url' => env('APP_URL', 'http://localhost'),

    /*
    |--------------------------------------------------------------------------
    | Application Timezone
    |--------------------------------------------------------------------------
    |
    | Here you may specify the default timezone for your application, which
    | will be used by the PHP date and date-time functions. The timezone
    | is set to "UTC" by default as it is suitable for most use cases.
    |
    */

    'timezone' => 'UTC',

    /*
    |--------------------------------------------------------------------------
    | Application Locale Configuration
    |--------------------------------------------------------------------------
    |
    | The application locale determines the default locale that will be used
    | by Laravel's translation / localization methods. This option can be
    | set to any locale for which you plan to have translation strings.
    |
    */

    'locale' => env('APP_LOCALE', 'en'),

    'fallback_locale' => env('APP_FALLBACK_LOCALE', 'en'),

    'faker_locale' => env('APP_FAKER_LOCALE', 'en_US'),

    /*
    |--------------------------------------------------------------------------
    | Encryption Key
    |--------------------------------------------------------------------------
    |
    | This key is utilized by Laravel's encryption services and should be set
    | to a random, 32 character string to ensure that all encrypted values
    | are secure. You should do this prior to deploying the application.
    |
    */

    'cipher' => 'AES-256-CBC',

    'key' => env('APP_KEY'),

    'jwt_secret' => env('JWT_SECRET', env('APP_KEY')),
    'access_token_minutes' => (int) env('ACCESS_TOKEN_MINUTES', 60),
    'refresh_token_days' => (int) env('REFRESH_TOKEN_DAYS', 30),
    'itbis_rate' => (float) env('ITBIS_RATE', 0.18),
    'quote_stale_days' => (int) env('QUOTE_STALE_DAYS', 7),
    'invoice_due_days' => (int) env('INVOICE_DUE_DAYS', 7),
    'notification_email' => (string) env('NOTIFICATION_EMAIL', ''),
    'geo_country_codes' => (string) env('GEO_COUNTRY_CODES', 'do'),
    'public_signup_enabled' => filter_var(env('PUBLIC_SIGNUP_ENABLED', true), FILTER_VALIDATE_BOOLEAN),
    'platform_trial_days' => (int) env('PLATFORM_TRIAL_DAYS', 45),
    'platform_currency' => (string) env('PLATFORM_CURRENCY', 'USD'),
    'platform_setup_fee' => (float) env('PLATFORM_SETUP_FEE', 160),
    'platform_monthly_fee' => (float) env('PLATFORM_MONTHLY_FEE', 40),
    'platform_payment_info' => (string) env('PLATFORM_PAYMENT_INFO', ''),
    'platform_contact_phone' => (string) env('PLATFORM_CONTACT_PHONE', '829-283-1336,829-477-8613'),
    'support_session_minutes' => (int) env('SUPPORT_SESSION_MINUTES', 60),
    'trusted_proxies' => (string) env('TRUSTED_PROXIES', ''),

    'previous_keys' => [
        ...array_filter(
            explode(',', (string) env('APP_PREVIOUS_KEYS', ''))
        ),
    ],

    /*
    |--------------------------------------------------------------------------
    | Maintenance Mode Driver
    |--------------------------------------------------------------------------
    |
    | These configuration options determine the driver used to determine and
    | manage Laravel's "maintenance mode" status. The "cache" driver will
    | allow maintenance mode to be controlled across multiple machines.
    |
    | Supported drivers: "file", "cache", "array"
    |
    */

    'maintenance' => [
        'driver' => env('APP_MAINTENANCE_DRIVER', 'file'),
        'store' => env('APP_MAINTENANCE_STORE', 'database'),
    ],

];
