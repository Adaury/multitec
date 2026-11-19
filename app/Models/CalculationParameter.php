<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;

class CalculationParameter extends Model
{
    use BelongsToCompany;

    /** Parámetros conocidos de los cálculos (con su valor por defecto), igual que KNOWN_PARAMETERS de Python. */
    public const KNOWN = [
        'cable_waste_margin_pct' => ['default' => 0.05, 'description' => 'Margen de desperdicio aplicado al metraje de cable detectado (0.05 = 5%).'],
        'labor_hourly_rate' => ['default' => 200.0, 'description' => 'Costo de mano de obra por hora de instalación, por técnico (RD$/hora).'],
        'labor_max_hours_per_technician' => ['default' => 40.0, 'description' => 'Horas de instalación que se le asignan a un solo técnico antes de sumar otro (ej. 40 = una semana laboral).'],
        'storage_gb_per_megapixel_per_day' => ['default' => 15.0, 'description' => 'Estimación de espacio en disco por megapixel de resolución de cámara, por día de grabación continua (GB/MP/día) — aproximación de planeación, no un cálculo exacto de bitrate/codec.'],
        'storage_retention_days' => ['default' => 30.0, 'description' => 'Días de retención de grabación que debe soportar el almacenamiento.'],
    ];

    protected $guarded = ['id', 'company_id'];
    protected $casts = ['value' => 'float', 'created_at' => 'datetime', 'updated_at' => 'datetime'];
}
