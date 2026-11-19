<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Corrección: las etapas de ejecución se crearon con nombres equivocados; las reales son estas 5, en este orden.
        // En dos fases: un nombre nuevo («instalacion») choca con uno viejo mientras ese no se haya cambiado.
        $names = ['inicio', 'instalacion', 'configuracion', 'pruebas', 'entrega'];
        foreach ($names as $order => $name) {
            DB::table('project_stages')->where('order', $order)->update(['name' => 'tmp_'.$order]);
        }
        foreach ($names as $order => $name) {
            DB::table('project_stages')->where('order', $order)->update(['name' => $name]);
        }

        Schema::create('log_entries', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('project_id')->constrained('projects')->cascadeOnDelete();
            $t->unsignedBigInteger('responsible_id')->nullable();
            $t->text('comment');
            $t->date('entry_date');
            $t->dateTime('created_at')->nullable();
            $t->dateTime('updated_at')->nullable();
            $t->foreign('responsible_id')->references('id')->on('users');
        });

        Schema::create('log_entry_assets', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('log_entry_id')->constrained('log_entries')->cascadeOnDelete();
            $t->string('file_path', 500);
            $t->string('description', 255)->nullable();
            $t->dateTime('created_at')->nullable();
        });

        Schema::create('extensions', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->string('code', 20)->index();
            $t->foreignId('project_id')->constrained('projects')->cascadeOnDelete();
            $t->unsignedBigInteger('quote_id')->nullable()->index();
            $t->string('title', 255);
            $t->text('description')->nullable();
            $t->string('status', 20)->default('pendiente'); // pendiente | aprobada | rechazada
            $t->date('date');
            $t->unsignedBigInteger('created_by')->nullable();
            $t->dateTime('created_at')->nullable();
            $t->dateTime('updated_at')->nullable();
            $t->unique(['company_id', 'code'], 'uq_extensions_company_code');
            $t->foreign('quote_id')->references('id')->on('quotes');
        });

        // Equipos instalados en casa o local de un cliente: base para garantías y mantenimientos.
        Schema::create('client_assets', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('client_id')->constrained('clients')->cascadeOnDelete();
            $t->unsignedBigInteger('project_id')->nullable()->index();
            $t->string('kind', 40)->default('otro');
            $t->string('name', 120);
            $t->string('brand', 60)->nullable();
            $t->string('model', 60)->nullable();
            $t->string('serial', 80)->nullable()->index();
            $t->string('mac', 17)->nullable()->index();
            $t->string('ip_address', 45)->nullable();
            $t->string('location', 160)->nullable();
            $t->date('installed_on')->nullable();
            $t->date('warranty_until')->nullable()->index();
            $t->text('notes')->nullable();
            $t->unsignedBigInteger('created_by')->nullable();
            $t->dateTime('created_at')->nullable();
            $t->dateTime('updated_at')->nullable();
            $t->foreign('project_id')->references('id')->on('projects');
        });
    }

    public function down(): void
    {
        foreach (['client_assets', 'extensions', 'log_entry_assets', 'log_entries'] as $t) {
            Schema::dropIfExists($t);
        }
    }
};
