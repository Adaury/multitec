<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('notifications', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('user_id')->constrained('users')->cascadeOnDelete();
            $t->string('title', 200);
            $t->text('body');
            $t->string('link', 255)->nullable();
            $t->boolean('read')->default(false);
            $t->dateTime('created_at')->nullable();
            $t->index(['user_id', 'read']);
        });

        Schema::create('tickets', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->string('code', 20)->index();
            $t->foreignId('project_id')->constrained('projects')->cascadeOnDelete();
            $t->unsignedBigInteger('technician_id')->nullable()->index();
            $t->text('problem');
            $t->text('solution')->nullable();
            $t->string('status', 20)->default('abierto'); // abierto | en_proceso | resuelto | cerrado
            $t->unsignedBigInteger('created_by')->nullable();
            $t->dateTime('created_at')->nullable();
            $t->dateTime('updated_at')->nullable();
            $t->dateTime('resolved_at')->nullable();
            $t->unique(['company_id', 'code'], 'uq_tickets_company_code');
            $t->foreign('technician_id')->references('id')->on('users');
        });

        Schema::create('ticket_history', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('ticket_id')->constrained('tickets')->cascadeOnDelete();
            $t->string('action', 20);
            $t->text('note')->nullable();
            $t->dateTime('created_at')->nullable();
        });

        Schema::create('ticket_assets', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('ticket_id')->constrained('tickets')->cascadeOnDelete();
            $t->string('file_path', 500);
            $t->string('description', 255)->nullable();
            $t->dateTime('created_at')->nullable();
        });
    }

    public function down(): void
    {
        foreach (['ticket_assets', 'ticket_history', 'tickets', 'notifications'] as $t) {
            Schema::dropIfExists($t);
        }
    }
};
