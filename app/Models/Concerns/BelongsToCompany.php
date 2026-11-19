<?php

namespace App\Models\Concerns;

use Illuminate\Database\Eloquent\Builder;

/** Aislamiento por empresa: nadie ve ni escribe datos de otra (equivale a TenantMixin de la API original). */
trait BelongsToCompany
{
    protected static function bootBelongsToCompany(): void
    {
        static::addGlobalScope('company', function (Builder $q) {
            $id = app()->bound('company_id') ? app('company_id') : null;
            if ($id !== null) {
                $q->where($q->getModel()->getTable().'.company_id', $id);
            }
        });
        static::creating(function ($m) {
            if ($m->company_id === null && app()->bound('company_id')) {
                $m->company_id = app('company_id');
            }
        });
    }
}
