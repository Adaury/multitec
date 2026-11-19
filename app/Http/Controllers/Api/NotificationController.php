<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Notification;
use App\Support\ApiException;
use Illuminate\Http\Request;

class NotificationController extends Controller
{
    public function index(Request $r)
    {
        return Notification::where('user_id', $r->attributes->get('user')->id)->orderByDesc('created_at')->orderByDesc('id')
            ->limit(50)->get()->map(fn ($n) => $n->toOut())->values();
    }

    public function unreadCount(Request $r)
    {
        return ['count' => Notification::where('user_id', $r->attributes->get('user')->id)->where('read', false)->count()];
    }

    public function markRead(Request $r, int $notification_id)
    {
        $n = Notification::find($notification_id);
        if (! $n || $n->user_id !== $r->attributes->get('user')->id) {
            throw new ApiException(404, 'Notificación no encontrada');
        }
        $n->update(['read' => true]);

        return $n->fresh()->toOut();
    }

    public function markAllRead(Request $r)
    {
        Notification::where('user_id', $r->attributes->get('user')->id)->where('read', false)->update(['read' => true]);

        return ['ok' => true];
    }
}
