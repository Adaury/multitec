<?php

namespace App\Support;

/** Fallo al hablar con Gemini: lleva el código HTTP de Google para decidir reintentos, y un mensaje seguro de mostrar. */
class GeminiError extends ApiException
{
    public function __construct(string $message, int $status = 502, public readonly ?int $geminiStatus = null)
    {
        parent::__construct($status, $message);
    }
}
