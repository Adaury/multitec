<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Rangos de NCF autorizados por la DGII (B01 crédito fiscal, B02 consumo, B14 regímenes especiales, B15 gubernamental).
        Schema::create('ncf_sequences', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->string('ncf_type', 3);
            $t->string('description', 100);
            $t->integer('range_start');
            $t->integer('range_end');
            $t->integer('next_number');
            $t->date('expires_at');
            $t->boolean('active')->default(true);
            $t->unsignedBigInteger('created_by')->nullable();
            $t->dateTime('created_at')->nullable();
        });

        Schema::create('invoices', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->string('code', 20)->index();
            $t->foreignId('project_id')->constrained('projects');
            $t->unsignedBigInteger('pre_invoice_id')->unique();
            $t->string('ncf', 20)->nullable();
            $t->string('ncf_type', 3)->nullable();
            $t->decimal('subtotal', 12, 2)->default(0);
            $t->decimal('itbis', 12, 2)->default(0);
            $t->decimal('total', 12, 2)->default(0);
            $t->string('payment_method', 20)->nullable();
            $t->decimal('itbis_withheld', 12, 2)->default(0);
            $t->decimal('isr_withheld', 12, 2)->default(0);
            $t->date('retention_date')->nullable();
            $t->date('paid_at')->nullable();
            $t->dateTime('voided_at')->nullable();
            $t->string('void_reason', 2)->nullable();
            $t->unsignedBigInteger('voided_by')->nullable();
            $t->unsignedBigInteger('created_by')->nullable();
            $t->dateTime('created_at')->nullable();
            $t->unique(['company_id', 'code'], 'uq_invoices_company_code');
            // Un NCF no se repite dentro de una empresa (los NULL no chocan entre sí).
            $t->unique(['company_id', 'ncf'], 'uq_invoices_company_ncf');
            $t->foreign('pre_invoice_id')->references('id')->on('pre_invoices');
        });

        Schema::create('invoice_items', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('invoice_id')->constrained('invoices')->cascadeOnDelete();
            $t->unsignedBigInteger('product_id')->nullable();
            $t->string('description', 500);
            $t->decimal('quantity', 12, 2)->default(1);
            $t->decimal('unit_price', 12, 2)->default(0);
            $t->decimal('subtotal', 12, 2)->default(0);
            $t->string('note', 500)->nullable();
            $t->foreign('product_id')->references('id')->on('products');
        });

        Schema::create('invoice_history', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('invoice_id')->constrained('invoices')->cascadeOnDelete();
            $t->string('action', 20);
            $t->text('note')->nullable();
            $t->dateTime('created_at')->nullable();
        });

        // Facturas de proveedores: insumo del reporte 606 (compras) de la DGII.
        Schema::create('purchase_invoices', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('supplier_id')->constrained('suppliers');
            $t->unsignedBigInteger('project_id')->nullable()->index();
            $t->string('ncf', 19);
            $t->string('ncf_modified', 19)->nullable();
            $t->date('invoice_date');
            $t->date('payment_date')->nullable();
            $t->string('expense_type', 2)->default('09');
            $t->string('payment_type', 2)->default('04');
            $t->decimal('services_amount', 12, 2)->default(0);
            $t->decimal('goods_amount', 12, 2)->default(0);
            $t->decimal('itbis_invoiced', 12, 2)->default(0);
            $t->decimal('itbis_withheld', 12, 2)->default(0);
            $t->decimal('isr_withheld', 12, 2)->default(0);
            $t->string('isr_retention_type', 2)->nullable();
            $t->text('notes')->nullable();
            $t->unsignedBigInteger('created_by')->nullable();
            $t->dateTime('created_at')->nullable();
            $t->dateTime('updated_at')->nullable();
            $t->foreign('project_id')->references('id')->on('projects');
        });
    }

    public function down(): void
    {
        foreach (['purchase_invoices', 'invoice_history', 'invoice_items', 'invoices', 'ncf_sequences'] as $t) {
            Schema::dropIfExists($t);
        }
    }
};
