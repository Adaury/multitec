<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('audit_log', function (Blueprint $t) {
            $t->id();
            $t->unsignedBigInteger('company_id')->nullable()->index();
            $t->dateTime('created_at')->nullable()->index();
            $t->unsignedBigInteger('user_id')->nullable()->index();
            $t->string('user_email', 255)->nullable();
            $t->string('action', 60)->index();
            $t->string('entity', 40)->nullable();
            $t->unsignedBigInteger('entity_id')->nullable();
            $t->text('detail')->nullable();
            $t->string('ip', 64)->nullable();
        });

        Schema::create('company_profile', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->unique()->constrained('companies');
            $t->string('name', 120)->nullable();
            $t->string('tagline', 160)->nullable();
            $t->string('representative', 120)->nullable();
            $t->string('rnc', 30)->nullable();
            $t->string('cedula', 30)->nullable();
            $t->string('address', 255)->nullable();
            $t->string('phone', 60)->nullable();
            $t->string('email', 120)->nullable();
            $t->string('website', 120)->nullable();
            $t->text('bank_info')->nullable();
            $t->text('invoice_notes')->nullable();
            $t->string('logo_path', 255)->nullable();
            $t->dateTime('updated_at')->nullable();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('company_profile');
        Schema::dropIfExists('audit_log');
    }
};
