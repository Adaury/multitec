<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Una cotización ajena (de un competidor o proveedor) que se subió para compararla con el levantamiento y con la propia.
        // El resultado de la comparación NO se guarda: se calcula cada vez con los datos de ese momento.
        Schema::create('quote_comparisons', function (Blueprint $t) {
            $t->id();
            $t->foreignId('company_id')->constrained('companies');
            $t->foreignId('project_id')->constrained('projects')->cascadeOnDelete();
            $t->foreignId('quote_id')->nullable()->constrained('quotes')->nullOnDelete();
            $t->string('label', 120);
            $t->string('filename', 255)->nullable();
            $t->string('file_path', 500)->nullable();
            $t->mediumText('source_text')->nullable();
            $t->json('items');
            $t->decimal('total', 12, 2)->nullable();
            $t->foreignId('created_by')->nullable()->constrained('users')->nullOnDelete();
            $t->dateTime('created_at')->nullable();
            $t->index(['company_id', 'project_id']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('quote_comparisons');
    }
};
