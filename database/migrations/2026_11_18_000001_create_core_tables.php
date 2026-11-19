<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('companies', function (Blueprint $t) {
            $t->id();
            $t->string('name', 120);
            $t->string('slug', 60)->unique();
            $t->boolean('is_active')->default(true);
            $t->text('notes')->nullable();
            $t->dateTime('trial_ends_at')->nullable();
            $t->unsignedInteger('max_users')->nullable();
            $t->boolean('is_demo')->default(false);
            $t->dateTime('created_at')->nullable();
            $t->string('source', 20)->default('panel');
            $t->string('contact_name', 120)->nullable();
            $t->string('contact_email', 255)->nullable();
            $t->string('contact_phone', 30)->nullable();
            $t->decimal('setup_fee', 12, 2)->nullable();
            $t->decimal('monthly_fee', 12, 2)->nullable();
            $t->dateTime('setup_paid_at')->nullable();
            $t->dateTime('paid_until')->nullable();
            $t->dateTime('reviewed_at')->nullable();
            $t->unsignedBigInteger('plan_id')->nullable();
        });

        Schema::create('users', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->string('name', 120);
            $t->string('email', 255)->unique();
            $t->string('hashed_password', 255);
            $t->string('role', 20)->default('oficina'); // admin | oficina | tecnico
            $t->boolean('is_active')->default(true);
            $t->boolean('must_change_password')->default(false);
            $t->boolean('is_platform_admin')->default(false);
            $t->string('assistant_alias', 60)->nullable();
            $t->string('phone', 30)->nullable();
            $t->string('zone', 80)->nullable();
            $t->string('skills', 255)->nullable();
            $t->string('vehicle', 80)->nullable();
            $t->dateTime('last_login_at')->nullable();
            $t->unsignedBigInteger('created_by')->nullable();
            $t->dateTime('created_at')->nullable();
        });

        Schema::create('refresh_tokens', function (Blueprint $t) {
            $t->id();
            $t->foreignId('user_id')->constrained('users')->cascadeOnDelete();
            $t->string('token_hash', 64)->unique();
            $t->dateTime('expires_at');
            $t->boolean('revoked')->default(false);
            $t->dateTime('created_at')->nullable();
            $t->string('user_agent', 255)->nullable();
            $t->string('ip', 64)->nullable();
            $t->dateTime('last_used_at')->nullable();
        });

        Schema::create('clients', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->string('name', 150);
            $t->string('company', 150)->nullable();
            $t->string('rnc', 30)->nullable();
            $t->string('phone', 30)->nullable();
            $t->string('email', 255)->nullable();
            $t->text('address')->nullable();
            $t->string('location_url', 2048)->nullable();
            $t->text('notes')->nullable();
            $t->unsignedBigInteger('created_by')->nullable();
            $t->dateTime('created_at')->nullable();
            $t->dateTime('updated_at')->nullable();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('clients');
        Schema::dropIfExists('refresh_tokens');
        Schema::dropIfExists('users');
        Schema::dropIfExists('companies');
    }
};
