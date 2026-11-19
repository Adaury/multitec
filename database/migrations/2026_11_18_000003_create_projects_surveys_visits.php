<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Correlativos por empresa y prefijo (PRY, COT, FAC...).
        Schema::create('code_sequences', function (Blueprint $t) {
            $t->unsignedBigInteger('company_id');
            $t->string('prefix', 10);
            $t->unsignedInteger('last_value')->default(0);
            $t->primary(['company_id', 'prefix']);
            $t->foreign('company_id')->references('id')->on('companies');
        });

        Schema::create('projects', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->string('code', 20)->index();
            $t->foreignId('client_id')->constrained('clients');
            $t->unsignedBigInteger('responsible_id')->nullable()->index();
            $t->date('date');
            $t->string('status', 30)->default('levantamiento');
            $t->text('description')->nullable();
            $t->text('address')->nullable();
            $t->string('location_url', 2048)->nullable();
            $t->string('survey_type', 60)->nullable();
            $t->string('public_token', 64)->nullable()->unique();
            $t->dateTime('portal_first_viewed_at')->nullable();
            $t->dateTime('portal_last_viewed_at')->nullable();
            $t->unsignedBigInteger('created_by')->nullable();
            $t->dateTime('created_at')->nullable();
            $t->dateTime('updated_at')->nullable();
            $t->unique(['company_id', 'code'], 'uq_projects_company_code');
        });

        Schema::create('engineering', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('project_id')->unique()->constrained('projects')->cascadeOnDelete();
            $t->text('recommended_equipment')->nullable();
            $t->text('distribution')->nullable();
            $t->text('conduits')->nullable();
            $t->text('wiring')->nullable();
            $t->text('technical_design')->nullable();
            $t->text('observations')->nullable();
            $t->boolean('ai_generated')->default(false);
            $t->unsignedBigInteger('created_by')->nullable();
            $t->dateTime('created_at')->nullable();
            $t->dateTime('updated_at')->nullable();
        });

        Schema::create('project_stages', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('project_id')->constrained('projects')->cascadeOnDelete();
            $t->string('name', 20);
            $t->integer('order');
            $t->boolean('completed')->default(false);
            $t->dateTime('completed_at')->nullable();
            $t->unique(['project_id', 'name'], 'uq_project_stage');
        });

        Schema::create('surveys', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('project_id')->unique()->constrained('projects')->cascadeOnDelete();
            $t->text('notes')->nullable();
            $t->text('measurements')->nullable();
            $t->text('observations')->nullable();
            $t->text('ai_summary')->nullable();
            $t->unsignedBigInteger('created_by')->nullable();
            $t->dateTime('created_at')->nullable();
            $t->dateTime('updated_at')->nullable();
        });

        Schema::create('survey_assets', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('survey_id')->constrained('surveys')->cascadeOnDelete();
            $t->string('kind', 10); // photo | audio
            $t->string('file_path', 500);
            $t->string('description', 255)->nullable();
            $t->dateTime('created_at')->nullable();
        });

        Schema::create('survey_markers', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('asset_id')->constrained('survey_assets')->cascadeOnDelete();
            $t->integer('number');
            $t->string('label', 80)->nullable();
            $t->string('kind', 30)->nullable();
            $t->double('x');
            $t->double('y');
            $t->dateTime('created_at')->nullable();
        });

        Schema::create('visits', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('project_id')->constrained('projects')->cascadeOnDelete();
            $t->unsignedBigInteger('technician_id')->nullable()->index();
            $t->date('scheduled_date')->index();
            $t->time('scheduled_time')->nullable();
            $t->text('notes')->nullable();
            $t->string('status', 20)->default('programada');
            $t->integer('duration_min')->nullable();
            $t->dateTime('checkin_at')->nullable();
            $t->double('checkin_lat')->nullable();
            $t->double('checkin_lng')->nullable();
            $t->dateTime('checkout_at')->nullable();
            $t->double('checkout_lat')->nullable();
            $t->double('checkout_lng')->nullable();
            $t->unsignedBigInteger('created_by')->nullable();
            $t->dateTime('created_at')->nullable();
            $t->dateTime('updated_at')->nullable();
        });
    }

    public function down(): void
    {
        foreach (['visits', 'survey_markers', 'survey_assets', 'surveys', 'project_stages', 'engineering', 'projects', 'code_sequences'] as $t) {
            Schema::dropIfExists($t);
        }
    }
};
