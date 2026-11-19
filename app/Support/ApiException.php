<?php

namespace App\Support;

use RuntimeException;

/** Error con el mismo formato que FastAPI: {"detail": "..."} */
class ApiException extends RuntimeException
{
    public function __construct(public int $status, string $detail, public array $headers = [])
    {
        parent::__construct($detail);
    }
}
