<?php

namespace App\Models;

use App\Models\Concerns\BelongsToCompany;
use Illuminate\Database\Eloquent\Model;

class CompanyProfile extends Model
{
    use BelongsToCompany;

    protected $table = 'company_profile';
    public $timestamps = false;
    protected $guarded = ['id', 'company_id'];

    public const FIELDS = [
        'name' => 120, 'tagline' => 160, 'representative' => 120, 'rnc' => 30, 'cedula' => 30, 'address' => 255,
        'phone' => 60, 'email' => 120, 'website' => 120, 'bank_info' => 1000, 'invoice_notes' => 1000,
    ];
}
