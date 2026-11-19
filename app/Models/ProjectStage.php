<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;

class ProjectStage extends Model
{
    use BelongsToCompany;

    public $timestamps = false;
    protected $guarded = ['id', 'company_id'];
    protected $casts = ['completed' => 'boolean', 'completed_at' => 'datetime'];

    /** Las 5 etapas fijas de ejecución (orden secuencial). */
    public const NAMES = ['inicio', 'instalacion', 'configuracion', 'pruebas', 'entrega'];
}
