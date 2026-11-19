<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('budgets', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->string('code', 20)->index();
            $t->foreignId('project_id')->constrained('projects')->cascadeOnDelete();
            $t->text('notes')->nullable();
            $t->decimal('total', 12, 2)->default(0);
            $t->boolean('ai_generated')->default(false);
            $t->unsignedBigInteger('created_by')->nullable();
            $t->dateTime('created_at')->nullable();
            $t->dateTime('updated_at')->nullable();
            $t->unique(['company_id', 'code'], 'uq_budgets_company_code');
        });

        Schema::create('budget_items', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('budget_id')->constrained('budgets')->cascadeOnDelete();
            $t->unsignedBigInteger('product_id')->nullable()->index();
            $t->string('description', 500);
            $t->decimal('quantity', 12, 2)->default(1);
            $t->decimal('unit_price', 12, 2)->default(0);
            $t->string('note', 500)->nullable();
            $t->foreign('product_id')->references('id')->on('products');
        });

        Schema::create('quotes', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->string('code', 20)->index();
            $t->foreignId('project_id')->constrained('projects')->cascadeOnDelete();
            $t->unsignedBigInteger('source_budget_id')->nullable();
            $t->string('status', 20)->default('pendiente'); // pendiente | aprobada | no_aprobada | archivada
            $t->text('notes')->nullable();
            $t->decimal('subtotal', 12, 2)->default(0);
            $t->decimal('itbis', 12, 2)->default(0);
            $t->decimal('total', 12, 2)->default(0);
            $t->unsignedBigInteger('created_by')->nullable();
            $t->dateTime('created_at')->nullable();
            $t->dateTime('updated_at')->nullable();
            $t->dateTime('decided_at')->nullable();
            $t->boolean('stale_notified')->default(false);
            $t->unique(['company_id', 'code'], 'uq_quotes_company_code');
            $t->foreign('source_budget_id')->references('id')->on('budgets');
        });

        Schema::create('quote_items', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('quote_id')->constrained('quotes')->cascadeOnDelete();
            $t->unsignedBigInteger('product_id')->nullable()->index();
            $t->string('description', 500);
            $t->decimal('quantity', 12, 2)->default(1);
            $t->decimal('unit_price', 12, 2)->default(0);
            $t->decimal('subtotal', 12, 2)->default(0);
            $t->string('note', 500)->nullable();
            $t->foreign('product_id')->references('id')->on('products');
        });

        Schema::create('quote_history', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('quote_id')->constrained('quotes')->cascadeOnDelete();
            $t->string('action', 20);
            $t->text('note')->nullable();
            $t->dateTime('created_at')->nullable();
        });

        // La prefactura nace al aprobar una cotización (la factura con NCF viene en el paso siguiente).
        Schema::create('pre_invoices', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->string('code', 20)->index();
            $t->foreignId('project_id')->constrained('projects')->cascadeOnDelete();
            $t->unsignedBigInteger('source_quote_id')->nullable();
            $t->string('status', 20)->default('pendiente'); // pendiente | facturada
            $t->text('notes')->nullable();
            $t->decimal('subtotal', 12, 2)->default(0);
            $t->decimal('itbis', 12, 2)->default(0);
            $t->decimal('total', 12, 2)->default(0);
            $t->unsignedBigInteger('created_by')->nullable();
            $t->dateTime('created_at')->nullable();
            $t->dateTime('updated_at')->nullable();
            $t->unique(['company_id', 'code'], 'uq_pre_invoices_company_code');
            $t->foreign('source_quote_id')->references('id')->on('quotes');
        });

        Schema::create('pre_invoice_items', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('pre_invoice_id')->constrained('pre_invoices')->cascadeOnDelete();
            $t->unsignedBigInteger('product_id')->nullable();
            $t->string('description', 500);
            $t->decimal('quantity', 12, 2)->default(1);
            $t->decimal('unit_price', 12, 2)->default(0);
            $t->decimal('subtotal', 12, 2)->default(0);
            $t->string('note', 500)->nullable();
            $t->foreign('product_id')->references('id')->on('products');
        });

        // Ahora que existen las cotizaciones, los materiales se enlazan a la cotización que los originó.
        Schema::table('materials', function (Blueprint $t) {
            $t->foreign('source_quote_id')->references('id')->on('quotes');
        });
    }

    public function down(): void
    {
        Schema::table('materials', fn (Blueprint $t) => $t->dropForeign(['source_quote_id']));
        foreach (['pre_invoice_items', 'pre_invoices', 'quote_history', 'quote_items', 'quotes', 'budget_items', 'budgets'] as $t) {
            Schema::dropIfExists($t);
        }
    }
};
