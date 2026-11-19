<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Company;
use App\Models\Notification;
use App\Models\PlatformPlan;
use App\Models\SitePartner;
use App\Models\Testimonial;
use App\Models\User;
use App\Support\ApiException;
use App\Support\Audit;
use App\Support\SiteDefaults;
use App\Support\Subscriptions;
use App\Support\V;
use Illuminate\Http\Request;

/**
 * Página pública de Multitec (/web) y su editor en el panel de plataforma: planes con precios, testimonios y aliados.
 * GET /api/site es público: planes activos, testimonios PUBLICADOS, teléfonos y días de prueba (sin datos de ninguna empresa).
 */
class SiteController extends Controller
{
    private function int($v, string $f, int $min, int $max): int
    {
        $n = V::int($v, $f);
        if ($n === null || $n < $min || $n > $max) {
            throw new ApiException(422, "$f debe estar entre $min y $max");
        }

        return $n;
    }

    private function price($v, string $f): float
    {
        $n = V::num($v, $f, 0.0);
        if ($n === null || $n > 1_000_000) {
            throw new ApiException(422, "$f debe estar entre 0 y 1000000");
        }

        return $n;
    }

    // ---- público -----------------------------------------------------------------------------

    public function publicSite()
    {
        SiteDefaults::ensure();

        return [
            'currency' => (string) config('app.platform_currency'), 'trial_days' => (int) config('app.platform_trial_days'),
            'signup_enabled' => (bool) config('app.public_signup_enabled'), 'phones' => Subscriptions::contactPhones(),
            'plans' => PlatformPlan::where('active', true)->orderBy('sort')->orderBy('id')->get()->map(fn ($p) => $p->toOut())->values(),
            'partners' => SitePartner::where('published', true)->orderBy('sort')->orderBy('id')->get()->map(fn ($p) => $p->toOut())->values(),
            'testimonials' => Testimonial::where('published', true)->where('is_example', false)->orderBy('sort')->orderBy('id')->get()
                ->map(fn ($t) => $t->toOut(false))->values(),
        ];
    }

    /** Un cliente cuenta su experiencia. Queda como borrador «enviado por cliente» y le llega el aviso al dueño. */
    public function sendExperience(Request $r)
    {
        if ($r->input('website')) { // robot
            throw new ApiException(400, 'No se pudo enviar');
        }
        if (! filter_var($r->input('consent', false), FILTER_VALIDATE_BOOLEAN)) {
            throw new ApiException(400, 'Necesitamos tu permiso para poder publicar tu opinión');
        }
        $author = trim((string) V::text($r->input('author'), 120, 'author', true));
        $quote = trim((string) V::text($r->input('quote'), 600, 'quote', true));
        $contact = trim((string) V::text($r->input('contact'), 160, 'contact', true));
        if (mb_strlen($author) < 2 || mb_strlen($quote) < 15 || mb_strlen($contact) < 5) {
            throw new ApiException(422, 'Completa tu nombre, tu opinión (mínimo 15 caracteres) y un contacto');
        }
        $rating = $r->has('rating') ? $this->int($r->input('rating'), 'rating', 1, 5) : 5;
        $company = V::text($r->input('company'), 120, 'company') ?: null;
        $t = Testimonial::create([
            'author' => $author, 'company' => $company, 'role' => V::text($r->input('role'), 120, 'role') ?: null, 'quote' => $quote,
            'rating' => $rating, 'contact' => $contact, 'source' => 'cliente', 'published' => false, 'is_example' => false, 'sort' => 50,
            'created_at' => now(),
        ]);
        foreach (User::where('is_platform_admin', true)->where('is_active', true)->get() as $admin) {
            (new Notification)->forceFill([
                'company_id' => $admin->company_id, 'user_id' => $admin->id, 'title' => "Nueva experiencia de $author",
                'body' => "{$rating}★ · ".($company ?: 'sin empresa')." · {$contact}. Revísala y publícala si quieres.",
                'link' => '/plataforma/sitio', 'read' => false, 'created_at' => now(),
            ])->save();
        }

        return response()->json(['ok' => true], 201);
    }

    // ---- editor de la plataforma ---------------------------------------------------------------------

    public function platformSite()
    {
        SiteDefaults::ensure();

        return [
            'currency' => (string) config('app.platform_currency'),
            'plans' => PlatformPlan::orderBy('sort')->orderBy('id')->get()->map(fn ($p) => $p->toOut())->values(),
            'testimonials' => Testimonial::orderBy('sort')->orderBy('id')->get()->map(fn ($t) => $t->toOut())->values(),
            'partners' => SitePartner::orderBy('sort')->orderBy('id')->get()->map(fn ($p) => $p->toOut())->values(),
        ];
    }

    private function log(Request $r, string $action, array $detail): void
    {
        $u = $r->attributes->get('user');
        Audit::log($action, $u, entity: 'site', detail: $detail, request: $r, companyId: $u->company_id);
    }

    // planes
    private function planData(Request $r): array
    {
        $name = trim((string) V::text($r->input('name'), 60, 'name', true));
        if (mb_strlen($name) < 2) {
            throw new ApiException(422, 'El nombre debe tener al menos 2 caracteres');
        }
        $features = $r->input('features', []);
        if (! is_array($features) || count($features) > 20) {
            throw new ApiException(422, 'features debe ser una lista de hasta 20 textos');
        }
        $features = array_values(array_filter(array_map(fn ($f) => is_string($f) ? mb_substr(trim($f), 0, 120) : '', $features), fn ($f) => $f !== ''));
        $max = $r->input('max_users');

        return [
            'name' => $name, 'description' => V::text($r->input('description'), 200, 'description'),
            'monthly_price' => $this->price($r->input('monthly_price'), 'monthly_price'), 'setup_price' => $this->price($r->input('setup_price'), 'setup_price'),
            'max_users' => $max === null || $max === '' ? null : $this->int($max, 'max_users', 1, 10000), 'features' => $features,
            'highlighted' => filter_var($r->input('highlighted', false), FILTER_VALIDATE_BOOLEAN),
            'active' => filter_var($r->input('active', true), FILTER_VALIDATE_BOOLEAN), 'sort' => $this->int($r->input('sort', 0), 'sort', 0, 1000),
        ];
    }

    public function createPlan(Request $r)
    {
        $d = $this->planData($r);
        $p = PlatformPlan::create($d + ['created_at' => now()]);
        $this->log($r, 'site_plan_created', ['plan' => $d['name']]);

        return response()->json($p->fresh()->toOut(), 201);
    }

    public function updatePlan(Request $r, int $plan_id)
    {
        $p = PlatformPlan::find($plan_id);
        if (! $p) {
            throw new ApiException(404, 'Plan no encontrado');
        }
        $d = $this->planData($r);
        $p->update($d);
        $this->log($r, 'site_plan_edited', ['plan' => $p->name, 'mensual' => $d['monthly_price']]);

        return $p->fresh()->toOut();
    }

    /** Un plan que alguna empresa tiene contratado no se borra: se oculta (deja de ofrecerse). */
    public function deletePlan(Request $r, int $plan_id)
    {
        $p = PlatformPlan::find($plan_id);
        if (! $p) {
            throw new ApiException(404, 'Plan no encontrado');
        }
        if (Company::where('plan_id', $plan_id)->exists()) {
            $p->update(['active' => false]);
        } else {
            $p->delete();
        }
        $this->log($r, 'site_plan_deleted', ['plan' => $p->name]);

        return response()->noContent();
    }

    // testimonios
    private function testimonialData(Request $r): array
    {
        $author = trim((string) V::text($r->input('author'), 120, 'author', true));
        $quote = trim((string) V::text($r->input('quote'), 600, 'quote', true));
        if (mb_strlen($author) < 2 || mb_strlen($quote) < 10) {
            throw new ApiException(422, 'Autor (mínimo 2) y opinión (mínimo 10 caracteres) son obligatorios');
        }

        return [
            'author' => $author, 'role' => V::text($r->input('role'), 120, 'role'), 'company' => V::text($r->input('company'), 120, 'company'),
            'quote' => $quote, 'rating' => $this->int($r->input('rating', 5), 'rating', 1, 5),
            'published' => filter_var($r->input('published', false), FILTER_VALIDATE_BOOLEAN), 'sort' => $this->int($r->input('sort', 0), 'sort', 0, 1000),
        ];
    }

    public function createTestimonial(Request $r)
    {
        $d = $this->testimonialData($r);
        if ($d['published'] && str_contains(mb_strtoupper($d['quote']), 'EJEMPLO')) {
            throw new ApiException(400, 'Reemplaza el texto de ejemplo por la opinión real antes de publicarlo');
        }
        $t = Testimonial::create($d + ['is_example' => false, 'created_at' => now()]);
        $this->log($r, 'site_testimonial_created', ['autor' => $d['author'], 'publicado' => $d['published']]);

        return response()->json($t->fresh()->toOut(), 201);
    }

    public function updateTestimonial(Request $r, int $testimonial_id)
    {
        $t = Testimonial::find($testimonial_id);
        if (! $t) {
            throw new ApiException(404, 'Testimonio no encontrado');
        }
        $d = $this->testimonialData($r);
        // Al editarlo deja de ser «el ejemplo del sistema»: ahora es una opinión que el dueño escribió.
        if ($d['published'] && str_contains(mb_strtoupper($d['quote']), 'EJEMPLO')) {
            throw new ApiException(400, 'Reemplaza el texto de ejemplo por la opinión real antes de publicarlo');
        }
        $t->update($d + ['is_example' => false]);
        $this->log($r, 'site_testimonial_edited', ['autor' => $t->author, 'publicado' => $t->published]);

        return $t->fresh()->toOut();
    }

    public function deleteTestimonial(Request $r, int $testimonial_id)
    {
        $t = Testimonial::find($testimonial_id);
        if (! $t) {
            throw new ApiException(404, 'Testimonio no encontrado');
        }
        $t->delete();
        $this->log($r, 'site_testimonial_deleted', ['autor' => $t->author]);

        return response()->noContent();
    }

    // aliados
    private function partnerData(Request $r): array
    {
        $name = trim((string) V::text($r->input('name'), 120, 'name', true));
        if (mb_strlen($name) < 2) {
            throw new ApiException(422, 'El nombre debe tener al menos 2 caracteres');
        }
        $url = trim((string) V::text($r->input('url'), 300, 'url'));
        if ($url !== '' && ! str_starts_with($url, 'https://') && ! str_starts_with($url, 'http://')) {
            $url = 'https://'.$url;
        }
        $logo = trim((string) V::text($r->input('logo_url'), 300, 'logo_url'));
        // Solo imágenes servidas por la propia web: no se enlazan logos de otros sitios.
        if ($logo !== '' && (! str_starts_with($logo, '/') || str_starts_with($logo, '//'))) {
            throw new ApiException(422, 'El logo debe ser una imagen de esta web (por ejemplo /brand/aliado.png)');
        }

        return [
            'name' => $name, 'description' => V::text($r->input('description'), 200, 'description'), 'url' => $url ?: null, 'logo_url' => $logo ?: null,
            'published' => filter_var($r->input('published', true), FILTER_VALIDATE_BOOLEAN), 'sort' => $this->int($r->input('sort', 0), 'sort', 0, 1000),
        ];
    }

    public function createPartner(Request $r)
    {
        $d = $this->partnerData($r);
        $p = SitePartner::create($d + ['created_at' => now()]);
        $this->log($r, 'site_partner_created', ['aliado' => $d['name']]);

        return response()->json($p->fresh()->toOut(), 201);
    }

    public function updatePartner(Request $r, int $partner_id)
    {
        $p = SitePartner::find($partner_id);
        if (! $p) {
            throw new ApiException(404, 'Aliado no encontrado');
        }
        $p->update($this->partnerData($r));
        $this->log($r, 'site_partner_edited', ['aliado' => $p->name]);

        return $p->fresh()->toOut();
    }

    public function deletePartner(Request $r, int $partner_id)
    {
        $p = SitePartner::find($partner_id);
        if (! $p) {
            throw new ApiException(404, 'Aliado no encontrado');
        }
        $p->delete();
        $this->log($r, 'site_partner_deleted', ['aliado' => $p->name]);

        return response()->noContent();
    }
}
