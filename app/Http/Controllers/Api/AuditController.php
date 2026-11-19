<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\AuditLog;
use Illuminate\Http\Request;

class AuditController extends Controller
{
    /** Solo el admin ve la bitácora de SU empresa. Los más recientes primero. */
    public function index(Request $r)
    {
        $q = AuditLog::where('company_id', app('company_id'));
        if ($r->filled('action')) {
            $q->where('action', $r->query('action'));
        }
        if ($r->filled('user_id')) {
            $q->where('user_id', (int) $r->query('user_id'));
        }
        if ($r->filled('before_id')) {
            $q->where('id', '<', (int) $r->query('before_id'));
        }
        $limit = max(1, min(500, (int) $r->query('limit', 100)));

        return $q->orderByDesc('id')->limit($limit)->get();
    }
}
