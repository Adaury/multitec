<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Planes que se venden en la página pública y en el registro. No son «de empresa»: los ve todo el mundo.
        Schema::create('platform_plans', function (Blueprint $t) {
            $t->id();
            $t->string('name', 60);
            $t->string('description', 200)->nullable();
            $t->decimal('monthly_price', 12, 2);
            $t->decimal('setup_price', 12, 2);
            $t->unsignedInteger('max_users')->nullable();
            $t->json('features')->nullable();
            $t->boolean('highlighted')->default(false);
            $t->boolean('active')->default(true);
            $t->integer('sort')->default(0);
            $t->dateTime('created_at')->nullable();
        });

        Schema::create('testimonials', function (Blueprint $t) {
            $t->id();
            $t->string('author', 120);
            $t->string('role', 120)->nullable();
            $t->string('company', 120)->nullable();
            $t->text('quote');
            $t->integer('rating')->default(5);
            $t->boolean('published')->default(false);
            $t->boolean('is_example')->default(false);
            $t->string('source', 20)->default('panel'); // panel | cliente
            $t->string('contact', 160)->nullable();      // nunca se muestra en la página
            $t->integer('sort')->default(0);
            $t->dateTime('created_at')->nullable();
        });

        Schema::create('site_partners', function (Blueprint $t) {
            $t->id();
            $t->string('name', 120);
            $t->string('description', 200)->nullable();
            $t->string('url', 300)->nullable();
            $t->string('logo_url', 300)->nullable();
            $t->boolean('published')->default(true);
            $t->integer('sort')->default(0);
            $t->dateTime('created_at')->nullable();
        });

        // Pagos de una empresa a la plataforma (instalación o mensualidad), anotados a mano por el dueño.
        Schema::create('company_payments', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->string('kind', 20);   // instalacion | mensualidad
            $t->decimal('amount', 12, 2);
            $t->integer('months')->default(0);
            $t->string('method', 20); // transferencia | deposito | efectivo | tarjeta | otro
            $t->string('reference', 120)->nullable();
            $t->text('notes')->nullable();
            $t->date('paid_at');
            $t->dateTime('paid_until_after')->nullable();
            $t->unsignedBigInteger('recorded_by')->nullable();
            $t->dateTime('created_at')->nullable();
        });

        Schema::table('companies', function (Blueprint $t) {
            $t->foreign('plan_id')->references('id')->on('platform_plans');
        });
    }

    public function down(): void
    {
        Schema::table('companies', fn (Blueprint $t) => $t->dropForeign(['plan_id']));
        foreach (['company_payments', 'site_partners', 'testimonials', 'platform_plans'] as $t) {
            Schema::dropIfExists($t);
        }
    }
};
