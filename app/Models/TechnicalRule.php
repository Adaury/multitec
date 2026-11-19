<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;

class TechnicalRule extends Model
{
    use BelongsToCompany;

    public const ADD_ACCESSORY = 'add_accessory';
    public const SET_PARAMETER = 'set_calculation_parameter';
    public const FLAG_NOTE = 'flag_engineering_note';

    public $timestamps = false;
    protected $guarded = ['id', 'company_id'];
    protected $casts = ['action_params' => 'array', 'created_at' => 'datetime'];

    /** Misma forma plana que TechnicalRuleOut de la API original. */
    public function toOut(): array
    {
        $p = $this->action_params ?? [];
        $acc = $this->action_type === self::ADD_ACCESSORY;
        $par = $this->action_type === self::SET_PARAMETER;

        return [
            'id' => $this->id, 'source_product_id' => $this->source_product_id, 'action_type' => $this->action_type,
            'target_tag' => $acc ? ($p['target_tag'] ?? null) : null,
            'per_source_units' => $acc ? ($p['per_source_units'] ?? null) : null,
            'quantity' => $acc ? (float) ($p['quantity'] ?? 1) : 1.0,
            'parameter_key' => $par ? ($p['parameter_key'] ?? null) : null,
            'value' => $par ? ($p['value'] ?? null) : null,
            'engineering_note' => $this->action_type === self::FLAG_NOTE ? ($p['engineering_note'] ?? null) : null,
            'notes' => $this->notes, 'created_at' => $this->created_at,
        ];
    }
}
