<?php

use App\Http\Controllers\Api\AuditController;
use App\Http\Controllers\Api\AuthController;
use App\Http\Controllers\Api\CompanyController;
use App\Http\Controllers\Api\BudgetController;
use App\Http\Controllers\Api\CalculationParameterController;
use App\Http\Controllers\Api\InvoiceController;
use App\Http\Controllers\Api\NcfController;
use App\Http\Controllers\Api\PurchaseInvoiceController;
use App\Http\Controllers\Api\ReportController;
use App\Http\Controllers\Api\QuoteController;
use App\Http\Controllers\Api\CatalogController;
use App\Http\Controllers\Api\CategoryController;
use App\Http\Controllers\Api\InventoryController;
use App\Http\Controllers\Api\MaterialController;
use App\Http\Controllers\Api\ProjectController;
use App\Http\Controllers\Api\SupplierController;
use App\Http\Controllers\Api\SurveyController;
use App\Http\Controllers\Api\UserController;
use App\Http\Controllers\Api\VisitController;
use App\Http\Controllers\Api\ClientController;
use Illuminate\Support\Facades\Route;

// Mismas rutas que la API FastAPI original (prefijo /api ya lo pone Laravel).
Route::prefix('auth')->group(function () {
    Route::post('login', [AuthController::class, 'login'])->middleware('throttle:login');
    Route::post('refresh', [AuthController::class, 'refresh'])->middleware('throttle:refresh');
    Route::post('logout', [AuthController::class, 'logout']);
});

// ---- Públicas (sin sesión): página web, registro de empresas y portal del cliente ----
Route::get('health', fn () => response()->json(['status' => 'ok']));
Route::get('site', [\App\Http\Controllers\Api\SiteController::class, 'publicSite']);
Route::post('site/experiences', [\App\Http\Controllers\Api\SiteController::class, 'sendExperience'])->middleware('throttle:experience');
Route::get('signup/info', [\App\Http\Controllers\Api\SignupController::class, 'info']);
Route::get('signup/check-email', [\App\Http\Controllers\Api\SignupController::class, 'emailAvailable'])->middleware('throttle:signup-check');
Route::post('signup', [\App\Http\Controllers\Api\SignupController::class, 'signup'])->middleware('throttle:signup');
Route::prefix('public/projects/{token}')->middleware('throttle:portal')->group(function () {
    $p = \App\Http\Controllers\Api\PortalController::class;
    Route::get('/', [$p, 'show']);
    Route::post('quotes/{quote_id}/approve', [$p, 'approve'])->whereNumber('quote_id');
    Route::post('quotes/{quote_id}/reject', [$p, 'reject'])->whereNumber('quote_id');
    Route::get('quotes/{quote_id}/pdf', [$p, 'quotePdf'])->whereNumber('quote_id');
    Route::get('invoices/{invoice_id}/pdf', [$p, 'invoicePdf'])->whereNumber('invoice_id');
});

// Errores de arranque que reporta el navegador: público a propósito, con límite por IP.
Route::post('client-errors', [\App\Http\Controllers\Api\ClientErrorController::class, 'report'])->middleware('throttle:client-errors');

Route::middleware('jwt')->group(function () {
    Route::prefix('auth')->group(function () {
        Route::get('me', [AuthController::class, 'me']);
        Route::put('me', [AuthController::class, 'updateMe']);
        Route::post('change-password', [AuthController::class, 'changePassword'])->middleware('throttle:change-password');
        Route::get('sessions', [AuthController::class, 'sessions']);
        Route::post('logout-all', [AuthController::class, 'logoutAll']);
    });

    Route::get('audit', [AuditController::class, 'index'])->middleware('role:admin');

    // «Mi suscripción» del administrador y enlace del portal del cliente
    Route::get('subscription', [\App\Http\Controllers\Api\SignupController::class, 'mySubscription'])->middleware('role:admin');
    Route::middleware('role:admin,oficina')->group(function () {
        Route::post('projects/{project_id}/public-link', [\App\Http\Controllers\Api\PortalController::class, 'createLink'])->whereNumber('project_id');
        Route::delete('projects/{project_id}/public-link', [\App\Http\Controllers\Api\PortalController::class, 'revokeLink'])->whereNumber('project_id');
    });

    // Panel de la plataforma (solo el dueño: is_platform_admin)
    Route::prefix('platform')->middleware('platform')->group(function () {
        $pl = \App\Http\Controllers\Api\PlatformController::class;
        $s = \App\Http\Controllers\Api\SiteController::class;
        Route::get('summary', [$pl, 'summary']);
        Route::get('companies', [$pl, 'companies']);
        Route::post('companies', [$pl, 'create']);
        Route::post('demos', [$pl, 'demo']);
        Route::prefix('companies/{company_id}')->whereNumber('company_id')->group(function () use ($pl) {
            Route::get('/', [$pl, 'show']);
            Route::put('/', [$pl, 'update']);
            Route::post('suspend', [$pl, 'suspend']);
            Route::post('activate', [$pl, 'activate']);
            Route::post('reset-admin-password', [$pl, 'resetAdminPassword']);
            Route::post('users/{user_id}/password', [$pl, 'setUserPassword'])->whereNumber('user_id');
            Route::post('reviewed', [$pl, 'reviewed']);
            Route::post('payments', [$pl, 'addPayment']);
            Route::post('support-session', [$pl, 'supportSession']);
        });
        Route::get('site', [$s, 'platformSite']);
        Route::post('site/plans', [$s, 'createPlan']);
        Route::put('site/plans/{plan_id}', [$s, 'updatePlan'])->whereNumber('plan_id');
        Route::delete('site/plans/{plan_id}', [$s, 'deletePlan'])->whereNumber('plan_id');
        Route::post('site/testimonials', [$s, 'createTestimonial']);
        Route::put('site/testimonials/{testimonial_id}', [$s, 'updateTestimonial'])->whereNumber('testimonial_id');
        Route::delete('site/testimonials/{testimonial_id}', [$s, 'deleteTestimonial'])->whereNumber('testimonial_id');
        Route::post('site/partners', [$s, 'createPartner']);
        Route::put('site/partners/{partner_id}', [$s, 'updatePartner'])->whereNumber('partner_id');
        Route::delete('site/partners/{partner_id}', [$s, 'deletePartner'])->whereNumber('partner_id');
    });

    // Notificaciones (cualquier usuario con sesión: son las suyas)
    Route::prefix('notifications')->group(function () {
        Route::get('/', [\App\Http\Controllers\Api\NotificationController::class, 'index']);
        Route::get('unread-count', [\App\Http\Controllers\Api\NotificationController::class, 'unreadCount']);
        Route::post('read-all', [\App\Http\Controllers\Api\NotificationController::class, 'markAllRead']);
        Route::put('{notification_id}/read', [\App\Http\Controllers\Api\NotificationController::class, 'markRead'])->whereNumber('notification_id');
    });

    // Tickets de soporte
    Route::middleware('role:admin,oficina,tecnico')->group(function () {
        $t = \App\Http\Controllers\Api\TicketController::class;
        Route::get('tickets', [$t, 'index']);
        Route::get('projects/{project_id}/tickets', [$t, 'indexByProject'])->whereNumber('project_id');
        Route::post('projects/{project_id}/tickets', [$t, 'store'])->whereNumber('project_id');
        Route::put('tickets/{ticket_id}', [$t, 'update'])->whereNumber('ticket_id');
        Route::get('tickets/{ticket_id}/history', [$t, 'history'])->whereNumber('ticket_id');
        Route::post('tickets/{ticket_id}/photos', [$t, 'uploadPhoto'])->whereNumber('ticket_id');
        Route::delete('tickets/{ticket_id}/photos/{asset_id}', [$t, 'deletePhoto'])->whereNumber(['ticket_id', 'asset_id']);
        Route::get('search', [\App\Http\Controllers\Api\DashboardController::class, 'search']);
    });

    // Panel, seguimientos de cobro
    Route::middleware('role:admin,oficina')->group(function () {
        Route::get('reports/dashboard', [\App\Http\Controllers\Api\DashboardController::class, 'summary']);
        Route::get('reports/dashboard/export', [\App\Http\Controllers\Api\DashboardController::class, 'export']);
        Route::get('reports/timesheet', [\App\Http\Controllers\Api\TimesheetController::class, 'show']);
        Route::get('reports/timesheet/export', [\App\Http\Controllers\Api\TimesheetController::class, 'export']);
        Route::get('followups', [\App\Http\Controllers\Api\DashboardController::class, 'followups']);
    });
    Route::get('system/status', [\App\Http\Controllers\Api\SystemController::class, 'status'])->middleware('role:admin,oficina,tecnico');

    Route::prefix('company')->group(function () {
        Route::get('/', [CompanyController::class, 'show'])->middleware('role:admin,oficina');
        Route::get('logo', [CompanyController::class, 'logo'])->middleware('role:admin,oficina');
        Route::put('/', [CompanyController::class, 'update'])->middleware('role:admin');
        Route::post('logo', [CompanyController::class, 'uploadLogo'])->middleware('role:admin');
        Route::delete('logo', [CompanyController::class, 'deleteLogo'])->middleware('role:admin');
    });

    Route::prefix('users')->group(function () {
        Route::get('technicians', [UserController::class, 'technicians'])->middleware('role:admin,oficina,tecnico');
        Route::get('workload', [UserController::class, 'teamWorkload'])->middleware('role:admin,oficina');
        Route::get('{id}/workload', [UserController::class, 'userWorkload'])->whereNumber('id')->middleware('role:admin,oficina');
        Route::middleware('role:admin')->group(function () {
            Route::get('/', [UserController::class, 'index']);
            Route::post('/', [UserController::class, 'store']);
            Route::put('{id}', [UserController::class, 'update'])->whereNumber('id');
            Route::post('{id}/reset-password', [UserController::class, 'resetPassword'])->whereNumber('id');
            Route::get('{id}/sessions', [UserController::class, 'sessions'])->whereNumber('id');
            Route::delete('{id}/sessions/{sessionId}', [UserController::class, 'revokeSession'])->whereNumber(['id', 'sessionId']);
            Route::post('{id}/sessions/revoke-all', [UserController::class, 'revokeAllSessions'])->whereNumber('id');
        });
    });

    Route::prefix('clients')->group(function () {
        Route::middleware('role:admin,oficina,tecnico')->group(function () {
            Route::get('/', [ClientController::class, 'index']);
            Route::post('/', [ClientController::class, 'store']);
            Route::get('{client_id}', [ClientController::class, 'show'])->whereNumber('client_id');
        });
        Route::middleware('role:admin,oficina')->group(function () {
            Route::get('export', [ClientController::class, 'export']);
            Route::put('{client_id}', [ClientController::class, 'update'])->whereNumber('client_id');
        });
    });

    // Proyectos: el técnico los ve y los crea (levantamiento rápido en campo); editarlos es de oficina/admin
    // (al técnico solo se le deja guardar ubicación y tipo de levantamiento: lo valida el controlador).
    Route::prefix('projects')->middleware('role:admin,oficina,tecnico')->group(function () {
        Route::get('/', [ProjectController::class, 'index']);
        Route::post('/', [ProjectController::class, 'store']);
        Route::get('export', [ProjectController::class, 'export'])->middleware('role:admin,oficina');
        Route::get('{project_id}', [ProjectController::class, 'show'])->whereNumber('project_id');
        Route::put('{project_id}', [ProjectController::class, 'update'])->whereNumber('project_id');

        $f = \App\Http\Controllers\Api\FieldController::class;
        Route::get('{project_id}/engineering', [$f, 'engineering'])->whereNumber('project_id');
        Route::put('{project_id}/engineering', [$f, 'updateEngineering'])->whereNumber('project_id');
        Route::get('{project_id}/execution', [$f, 'execution'])->whereNumber('project_id');
        Route::post('{project_id}/execution/advance', [$f, 'advance'])->whereNumber('project_id');
        Route::post('{project_id}/execution/undo', [$f, 'undo'])->whereNumber('project_id');
        Route::post('{project_id}/engineering/ai-draft', [\App\Http\Controllers\Api\AiController::class, 'engineeringDraft'])->whereNumber('project_id')->middleware('throttle:ai');
        Route::post('{project_id}/budget-suggestions', [\App\Http\Controllers\Api\AiController::class, 'budgetSuggestions'])->whereNumber('project_id')->middleware('throttle:ai');
        Route::post('{project_id}/generate-from-survey', [\App\Http\Controllers\Api\AiController::class, 'generate'])->whereNumber('project_id')->middleware('throttle:ai');
        Route::post('{project_id}/generate-from-survey/start', [\App\Http\Controllers\Api\AiController::class, 'startGeneration'])->whereNumber('project_id')->middleware('throttle:ai');
        Route::get('{project_id}/generate-from-survey/status', [\App\Http\Controllers\Api\AiController::class, 'generationStatus'])->whereNumber('project_id');
        // Cotizaciones ajenas: solo admin y oficina (son precios).
        Route::middleware('role:admin,oficina')->prefix('{project_id}/comparisons')->whereNumber('project_id')->group(function () {
            Route::get('/', [\App\Http\Controllers\Api\ComparisonController::class, 'index']);
            Route::post('/', [\App\Http\Controllers\Api\ComparisonController::class, 'store'])->middleware('throttle:ai');
            Route::get('{comparison_id}', [\App\Http\Controllers\Api\ComparisonController::class, 'show'])->whereNumber('comparison_id');
            Route::put('{comparison_id}', [\App\Http\Controllers\Api\ComparisonController::class, 'update'])->whereNumber('comparison_id');
            Route::delete('{comparison_id}', [\App\Http\Controllers\Api\ComparisonController::class, 'destroy'])->whereNumber('comparison_id');
        });
        Route::get('{project_id}/logbook', [$f, 'logbook'])->whereNumber('project_id');
        Route::post('{project_id}/logbook', [$f, 'createLogEntry'])->whereNumber('project_id');

        Route::prefix('{project_id}/survey')->whereNumber('project_id')->group(function () {
            Route::get('/', [SurveyController::class, 'show']);
            Route::put('/', [SurveyController::class, 'update']);
            Route::post('assets', [SurveyController::class, 'uploadAsset']);
            Route::put('assets/{asset_id}/markers', [SurveyController::class, 'updateMarkers'])->whereNumber('asset_id');
            Route::delete('assets/{asset_id}', [SurveyController::class, 'deleteAsset'])->whereNumber('asset_id');
            // IA (Gemini): admin, oficina y técnico; 30 llamadas por minuto y usuario.
            Route::post('ai-summarize', [\App\Http\Controllers\Api\AiController::class, 'summarizeSurvey'])->middleware('throttle:ai');
            Route::post('assets/{asset_id}/transcribe', [\App\Http\Controllers\Api\AiController::class, 'transcribe'])->whereNumber('asset_id')->middleware('throttle:ai');
            Route::post('voice-feedback', [\App\Http\Controllers\Api\AiController::class, 'voiceFeedback']);
        });
    });

    // ---- Administración: borrar datos de prueba (solo admin) ----
    Route::prefix('admin/test-data')->middleware('role:admin')->group(function () {
        Route::get('/', [\App\Http\Controllers\Api\TestDataController::class, 'index']);
        Route::post('preview', [\App\Http\Controllers\Api\TestDataController::class, 'preview']);
        Route::post('delete', [\App\Http\Controllers\Api\TestDataController::class, 'destroy']);
    });

    // ---- Aprendizaje de la IA: solo lectura y vacío (ver LearningController) ----
    Route::prefix('ai-feedback-events')->group(function () {
        Route::get('/', [\App\Http\Controllers\Api\LearningController::class, 'events'])->middleware('role:admin,oficina');
        Route::get('voice-examples', [\App\Http\Controllers\Api\LearningController::class, 'voiceExamples'])->middleware('role:admin,oficina');
        Route::post('analyze', [\App\Http\Controllers\Api\LearningController::class, 'analyze'])->middleware('role:admin');
    });

    // ---- IA general (Gemini): alta rápida y preguntas sobre proyectos ----
    Route::middleware('role:admin,oficina,tecnico')->group(function () {
        Route::post('ai/intake-parse', [\App\Http\Controllers\Api\AiController::class, 'intakeParse'])->middleware('throttle:ai');
        Route::post('ai/ask', [\App\Http\Controllers\Api\AiController::class, 'ask'])->middleware('throttle:ai');
        Route::get('ai/generation-jobs', [\App\Http\Controllers\Api\AiController::class, 'myGenerationJobs']);
        Route::get('assistant/today', [\App\Http\Controllers\Api\AssistantController::class, 'today']);
        Route::post('assistant/talk', [\App\Http\Controllers\Api\AssistantController::class, 'talk'])->middleware('throttle:ai');
        Route::post('assistant/listen', [\App\Http\Controllers\Api\AssistantController::class, 'listen'])->middleware('throttle:ai');
        Route::post('ai/warmup', fn () => response()->json(['started' => false], 202));
    });

    // ---- Catálogo, categorías, inventario, proveedores, materiales, parámetros de cálculo ----
    Route::get('categories', [CategoryController::class, 'index'])->middleware('role:admin,oficina,tecnico');
    Route::middleware('role:admin')->group(function () {
        Route::post('categories', [CategoryController::class, 'store']);
        Route::put('categories/{category_id}', [CategoryController::class, 'update'])->whereNumber('category_id');
        Route::delete('categories/{category_id}', [CategoryController::class, 'destroy'])->whereNumber('category_id');
    });

    Route::prefix('catalog')->group(function () {
        Route::middleware('role:admin,oficina')->group(function () {
            Route::get('/', [CatalogController::class, 'index']);
            Route::get('import-template', [\App\Http\Controllers\Api\SheetsController::class, 'importTemplate']);
            Route::get('base-kits', [\App\Http\Controllers\Api\SheetsController::class, 'baseKits']);
            Route::get('export', [\App\Http\Controllers\Api\SheetsController::class, 'export']);
            Route::get('{product_id}/rules', [CatalogController::class, 'listRules'])->whereNumber('product_id');
            Route::get('{product_id}/technical-rules', [CatalogController::class, 'listTechnicalRules'])->whereNumber('product_id');
            Route::get('{product_id}/relations', [CatalogController::class, 'listRelations'])->whereNumber('product_id');
        });
        Route::middleware('role:admin')->group(function () {
            Route::post('/', [CatalogController::class, 'store']);
            Route::post('base-catalog', [\App\Http\Controllers\Api\SheetsController::class, 'baseCatalog']);
            Route::post('import', [\App\Http\Controllers\Api\SheetsController::class, 'import']);
            Route::put('bulk-prices', [CatalogController::class, 'bulkPrices']);
            Route::put('{product_id}', [CatalogController::class, 'update'])->whereNumber('product_id');
            Route::post('{product_id}/rules', [CatalogController::class, 'createRule'])->whereNumber('product_id');
            Route::put('rules/{rule_id}', [CatalogController::class, 'updateRule'])->whereNumber('rule_id');
            Route::delete('rules/{rule_id}', [CatalogController::class, 'deleteRule'])->whereNumber('rule_id');
            Route::post('{product_id}/technical-rules', [CatalogController::class, 'createTechnicalRule'])->whereNumber('product_id');
            Route::put('technical-rules/{rule_id}', [CatalogController::class, 'updateTechnicalRule'])->whereNumber('rule_id');
            Route::delete('technical-rules/{rule_id}', [CatalogController::class, 'deleteTechnicalRule'])->whereNumber('rule_id');
            Route::post('{product_id}/relations', [CatalogController::class, 'createRelation'])->whereNumber('product_id');
            Route::put('relations/{relation_id}', [CatalogController::class, 'updateRelation'])->whereNumber('relation_id');
            Route::delete('relations/{relation_id}', [CatalogController::class, 'deleteRelation'])->whereNumber('relation_id');
        });
    });

    Route::middleware('role:admin,oficina')->group(function () {
        Route::get('products/{product_id}/stock-movements', [InventoryController::class, 'index'])->whereNumber('product_id');
        Route::post('products/{product_id}/stock-movements', [InventoryController::class, 'store'])->whereNumber('product_id');

        Route::get('suppliers', [SupplierController::class, 'index']);
        Route::post('suppliers', [SupplierController::class, 'store']);
        Route::get('suppliers/{supplier_id}', [SupplierController::class, 'show'])->whereNumber('supplier_id');
        Route::put('suppliers/{supplier_id}', [SupplierController::class, 'update'])->whereNumber('supplier_id');
        Route::get('suppliers/{supplier_id}/materials', [SupplierController::class, 'purchases'])->whereNumber('supplier_id');

        Route::get('projects/{project_id}/materials', [MaterialController::class, 'index'])->whereNumber('project_id');
        Route::get('projects/{project_id}/materials/purchase-list', [MaterialController::class, 'purchaseList'])->whereNumber('project_id');
        Route::post('projects/{project_id}/materials', [MaterialController::class, 'store'])->whereNumber('project_id');
        Route::put('materials/{material_id}/status', [MaterialController::class, 'updateStatus'])->whereNumber('material_id');

        Route::get('calculation-parameters', [CalculationParameterController::class, 'index']);
    });
    Route::put('calculation-parameters/{key}', [CalculationParameterController::class, 'upsert'])->middleware('role:admin');

    // ---- Presupuestos y cotizaciones (admin y oficina) ----
    Route::middleware('role:admin,oficina')->group(function () {
        Route::get('projects/{project_id}/budgets', [BudgetController::class, 'indexByProject'])->whereNumber('project_id');
        Route::post('projects/{project_id}/budgets', [BudgetController::class, 'store'])->whereNumber('project_id');
        Route::get('budgets', [BudgetController::class, 'index']);
        Route::get('budgets/{budget_id}', [BudgetController::class, 'show'])->whereNumber('budget_id');
        Route::put('budgets/{budget_id}', [BudgetController::class, 'update'])->whereNumber('budget_id');
        Route::post('budgets/{budget_id}/convert-to-quote', [BudgetController::class, 'convertToQuote'])->whereNumber('budget_id');
        Route::get('budgets/{budget_id}/pdf', [BudgetController::class, 'pdf'])->whereNumber('budget_id');

        Route::get('projects/{project_id}/quotes', [QuoteController::class, 'indexByProject'])->whereNumber('project_id');
        Route::post('projects/{project_id}/quotes', [QuoteController::class, 'store'])->whereNumber('project_id');
        Route::get('quotes', [QuoteController::class, 'index']);
        Route::prefix('quotes/{quote_id}')->whereNumber('quote_id')->group(function () {
            Route::get('/', [QuoteController::class, 'show']);
            Route::put('/', [QuoteController::class, 'update']);
            Route::get('history', [QuoteController::class, 'history']);
            Route::get('purchase-list-preview', [QuoteController::class, 'purchaseListPreview']);
            Route::post('approve', [QuoteController::class, 'approve']);
            Route::post('reject', [QuoteController::class, 'reject']);
            Route::post('archive', [QuoteController::class, 'archive']);
            Route::post('reactivate', [QuoteController::class, 'reactivate']);
            Route::get('reprice-preview', [QuoteController::class, 'repricePreview']);
            Route::post('reprice', [QuoteController::class, 'reprice']);
            Route::post('new-version', [QuoteController::class, 'newVersion']);
            Route::get('pdf', [QuoteController::class, 'pdf']);
            Route::post('send-email', [\App\Http\Controllers\Api\SheetsController::class, 'sendQuoteEmail']);
            Route::get('items-file', [\App\Http\Controllers\Api\SheetsController::class, 'quoteItemsFile']);
        });
        Route::get('line-items/template', [\App\Http\Controllers\Api\SheetsController::class, 'lineItemsTemplate']);
        Route::post('line-items/parse', [\App\Http\Controllers\Api\SheetsController::class, 'lineItemsParse']);
    });
    Route::get('quotes/{quote_id}/margin', [QuoteController::class, 'margin'])->whereNumber('quote_id')->middleware('role:admin');
    Route::get('projects/{project_id}/margin', [ProjectController::class, 'margin'])->whereNumber('project_id')->middleware('role:admin');
    Route::get('reports/margin', [\App\Http\Controllers\Api\DashboardController::class, 'companyMargin'])->middleware('role:admin');

    // ---- Prefacturas, facturas con NCF, compras y reportes DGII ----
    Route::middleware('role:admin,oficina')->group(function () {
        Route::get('projects/{project_id}/pre-invoices', [InvoiceController::class, 'listPre'])->whereNumber('project_id');
        Route::post('projects/{project_id}/pre-invoices', [InvoiceController::class, 'storePre'])->whereNumber('project_id');
        Route::post('quotes/{quote_id}/generate-pre-invoice', [InvoiceController::class, 'generatePre'])->whereNumber('quote_id');
        Route::get('pre-invoices/{pre_invoice_id}', [InvoiceController::class, 'showPre'])->whereNumber('pre_invoice_id');

        Route::get('projects/{project_id}/invoices', [InvoiceController::class, 'listByProject'])->whereNumber('project_id');
        Route::get('invoices/export', [InvoiceController::class, 'export']);
        Route::prefix('invoices/{invoice_id}')->whereNumber('invoice_id')->group(function () {
            Route::get('/', [InvoiceController::class, 'show']);
            Route::get('history', [InvoiceController::class, 'history']);
            Route::put('payment', [InvoiceController::class, 'payment']);
            Route::put('paid', [InvoiceController::class, 'paid']);
            Route::get('pdf', [InvoiceController::class, 'pdf']);
        });

        Route::get('purchase-invoices', [PurchaseInvoiceController::class, 'index']);
        Route::post('purchase-invoices', [PurchaseInvoiceController::class, 'store']);
        Route::get('purchase-invoices/{invoice_id}', [PurchaseInvoiceController::class, 'show'])->whereNumber('invoice_id');
        Route::put('purchase-invoices/{invoice_id}', [PurchaseInvoiceController::class, 'update'])->whereNumber('invoice_id');

        Route::get('reports/dgii-606', [ReportController::class, 'dgii606']);
        Route::get('reports/dgii-607', [ReportController::class, 'dgii607']);
        Route::get('reports/dgii-607/consumo-resumen', [ReportController::class, 'consumptionSummary']);
        Route::get('reports/dgii-608', [ReportController::class, 'dgii608']);
    });
    Route::middleware('role:admin')->group(function () {
        Route::post('pre-invoices/{pre_invoice_id}/convert-to-invoice', [InvoiceController::class, 'convert'])->whereNumber('pre_invoice_id');
        Route::post('invoices/{invoice_id}/void', [InvoiceController::class, 'void'])->whereNumber('invoice_id');
        Route::get('invoices/{invoice_id}/margin', [InvoiceController::class, 'margin'])->whereNumber('invoice_id');
        Route::delete('purchase-invoices/{invoice_id}', [PurchaseInvoiceController::class, 'destroy'])->whereNumber('invoice_id');

        Route::get('ncf-sequences', [NcfController::class, 'index']);
        Route::post('ncf-sequences', [NcfController::class, 'store']);
        Route::put('ncf-sequences/{sequence_id}', [NcfController::class, 'update'])->whereNumber('sequence_id');
    });

    // ---- Bitácora (fotos), equipos del cliente, mapa; ampliaciones (admin y oficina) ----
    Route::middleware('role:admin,oficina,tecnico')->group(function () {
        $c = \App\Http\Controllers\Api\ClientAssetController::class;
        Route::post('logbook/{entry_id}/photos', [\App\Http\Controllers\Api\FieldController::class, 'uploadLogPhoto'])->whereNumber('entry_id');
        Route::get('clients/{client_id}/assets', [$c, 'index'])->whereNumber('client_id');
        Route::post('clients/{client_id}/assets', [$c, 'store'])->whereNumber('client_id');
        Route::put('client-assets/{client_asset_id}', [$c, 'update'])->whereNumber('client_asset_id');
        Route::get('geo/search', [\App\Http\Controllers\Api\GeoController::class, 'search'])->middleware('throttle:geo');
    });
    Route::delete('client-assets/{client_asset_id}', [\App\Http\Controllers\Api\ClientAssetController::class, 'destroy'])
        ->whereNumber('client_asset_id')->middleware('role:admin,oficina');
    Route::middleware('role:admin,oficina')->group(function () {
        $f = \App\Http\Controllers\Api\FieldController::class;
        Route::get('projects/{project_id}/extensions', [$f, 'extensions'])->whereNumber('project_id');
        Route::post('projects/{project_id}/extensions', [$f, 'createExtension'])->whereNumber('project_id');
        Route::put('extensions/{extension_id}/status', [$f, 'extensionStatus'])->whereNumber('extension_id');
    });

    Route::prefix('visits')->middleware('role:admin,oficina,tecnico')->group(function () {
        Route::get('/', [VisitController::class, 'index']);
        Route::post('/', [VisitController::class, 'store']);
        Route::put('{visit_id}', [VisitController::class, 'update'])->whereNumber('visit_id');
        Route::post('{visit_id}/checkin', [VisitController::class, 'checkin'])->whereNumber('visit_id');
        Route::post('{visit_id}/checkout', [VisitController::class, 'checkout'])->whereNumber('visit_id');
    });
});
