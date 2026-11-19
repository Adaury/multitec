<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('categories', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->string('name', 120);
            $t->string('slug', 120)->index();
            $t->string('code_prefix', 10)->nullable();
            $t->unsignedBigInteger('parent_id')->nullable();
            $t->dateTime('created_at')->nullable();
            $t->unique(['company_id', 'slug'], 'uq_categories_company_slug');
            $t->foreign('parent_id')->references('id')->on('categories');
        });

        Schema::create('suppliers', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->string('name', 150);
            $t->string('rnc', 30)->nullable();
            $t->string('phone', 30)->nullable();
            $t->string('email', 255)->nullable();
            $t->text('address')->nullable();
            $t->text('notes')->nullable();
            $t->unsignedBigInteger('created_by')->nullable();
            $t->dateTime('created_at')->nullable();
            $t->dateTime('updated_at')->nullable();
        });

        Schema::create('products', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->string('code', 20)->index();
            $t->unsignedBigInteger('category_id')->nullable()->index();
            $t->string('name', 255);
            $t->string('unit', 30)->default('unidad');
            $t->decimal('price', 12, 2)->default(0);
            $t->boolean('price_estimated')->default(false);
            $t->decimal('cost', 12, 2)->nullable();
            $t->decimal('stock_quantity', 12, 2)->default(0);
            $t->text('notes')->nullable();
            $t->string('brand', 80)->nullable();
            $t->string('model', 80)->nullable();
            $t->text('commercial_description')->nullable();
            $t->text('technical_description')->nullable();
            $t->decimal('install_minutes', 10, 2)->nullable();
            $t->string('labor_role', 80)->nullable();
            $t->integer('priority')->nullable();
            $t->decimal('resolution_mp', 6, 2)->nullable();
            $t->decimal('storage_capacity_gb', 10, 2)->nullable();
            $t->integer('channel_capacity')->nullable();
            $t->integer('pack_size')->nullable();
            $t->json('tags')->nullable();
            $t->json('synonyms')->nullable();
            $t->unsignedBigInteger('created_by')->nullable();
            $t->dateTime('created_at')->nullable();
            $t->dateTime('updated_at')->nullable();
            $t->unique(['company_id', 'code'], 'uq_products_company_code');
            $t->foreign('category_id')->references('id')->on('categories');
        });

        Schema::create('stock_movements', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('product_id')->constrained('products')->cascadeOnDelete();
            $t->string('movement_type', 10); // entrada | salida
            $t->decimal('quantity', 12, 2);
            $t->text('reason')->nullable();
            $t->unsignedBigInteger('created_by')->nullable();
            $t->dateTime('created_at')->nullable();
        });

        Schema::create('materials', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('project_id')->constrained('projects')->cascadeOnDelete();
            $t->unsignedBigInteger('product_id')->nullable()->index();
            $t->unsignedBigInteger('source_quote_id')->nullable();
            $t->string('description', 500);
            $t->decimal('quantity', 12, 2)->default(1);
            $t->string('status', 20)->default('pendiente_compra');
            $t->text('notes')->nullable();
            $t->unsignedBigInteger('supplier_id')->nullable()->index();
            $t->decimal('purchase_price', 12, 2)->nullable();
            $t->unsignedBigInteger('created_by')->nullable();
            $t->dateTime('created_at')->nullable();
            $t->dateTime('updated_at')->nullable();
            $t->foreign('product_id')->references('id')->on('products');
            $t->foreign('supplier_id')->references('id')->on('suppliers');
        });

        Schema::create('catalog_rules', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('source_product_id')->constrained('products')->cascadeOnDelete();
            $t->string('target_tag', 60);
            $t->decimal('per_source_units', 12, 2)->nullable();
            $t->decimal('quantity', 12, 2)->default(1);
            $t->string('notes', 200)->nullable();
            $t->dateTime('created_at')->nullable();
        });

        Schema::create('technical_rules', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('source_product_id')->constrained('products')->cascadeOnDelete();
            $t->string('action_type', 40);
            $t->json('action_params');
            $t->string('notes', 200)->nullable();
            $t->dateTime('created_at')->nullable();
        });

        Schema::create('product_relations', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('product_id')->constrained('products')->cascadeOnDelete();
            $t->foreignId('related_product_id')->constrained('products')->cascadeOnDelete();
            $t->string('relation_type', 20);
            $t->string('notes', 200)->nullable();
            $t->dateTime('created_at')->nullable();
        });

        Schema::create('calculation_parameters', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->string('key', 60)->index();
            $t->decimal('value', 12, 4);
            $t->string('description', 200)->nullable();
            $t->dateTime('created_at')->nullable();
            $t->dateTime('updated_at')->nullable();
            $t->unique(['company_id', 'key'], 'uq_calculation_parameters_company_key');
        });
    }

    public function down(): void
    {
        foreach (['calculation_parameters', 'product_relations', 'technical_rules', 'catalog_rules', 'materials', 'stock_movements', 'products', 'suppliers', 'categories'] as $t) {
            Schema::dropIfExists($t);
        }
    }
};
