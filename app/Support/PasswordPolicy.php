<?php

namespace App\Support;

/** Misma política que la API original: largo mínimo 10, sin claves comunes, máximo 72 bytes (bcrypt). */
class PasswordPolicy
{
    public const MIN = 10;

    private const COMMON = [
        '1234567890', '0123456789', '12345678910', '1q2w3e4r5t', 'qwertyuiop', 'asdfghjkl', 'password1', 'password12',
        'password123', 'passw0rd123', 'contrasena', 'contrasena1', 'contrasena12', 'contrasena123', 'contraseña',
        'contraseña1', 'contraseña123', 'admin12345', 'administrador', 'administrator1', 'multitec123', 'multitec1234',
        'multitec2026', 'multitec2025', 'change-this-password', 'cambiar123', 'iloveyou12', 'letmein123',
        'welcome123', 'welcome1234', 'bienvenido1', 'bienvenido123', 'abc1234567', 'abcd123456', 'qwerty1234',
        'qwerty12345', 'qwerty123456', '123456789a', 'a123456789', '1234567890a', 'santodomingo',
        'republicadominicana', 'dominicana1', 'dominicana123',
    ];

    /** Lanza ApiException 422 si no cumple. */
    public static function enforce(string $password): string
    {
        if (strlen($password) > 72) {
            throw new ApiException(422, 'La contraseña no puede superar los 72 bytes');
        }
        if (mb_strlen($password) < self::MIN) {
            throw new ApiException(422, 'La contraseña debe tener al menos '.self::MIN.' caracteres');
        }
        if (in_array(mb_strtolower($password), self::COMMON, true) || ctype_digit($password) || count(array_unique(mb_str_split($password))) === 1) {
            throw new ApiException(422, 'Esa contraseña es demasiado común. Elige una que no sea fácil de adivinar');
        }

        return $password;
    }
}
