# Arquitectura del AI Engine

> **Estado: diseño propuesto sobre una base ya construida.** Este documento no parte de
> cero: Multitec ya tiene un pipeline de IA funcionando (levantamiento → presupuesto →
> cotización, con reglas de catálogo y embeddings). Lo que sigue reorganiza ese trabajo
> bajo un módulo único (`AI Engine`) y cierra los huecos frente a la visión de 7 motores,
> sin romper lo que ya opera en producción.

## Principio rector

El ERP dejó de ser "un sistema con algo de IA" para ser **un motor de IA con un ERP
alrededor**. La regla de diseño que se deriva de esto: ningún dato técnico o comercial se
vuelve a capturar a mano si ya existe en el expediente del proyecto. Todo lo que hoy hace
un humano por segunda vez (repetir cantidades, redactar ingeniería desde cero, copiar
líneas de un documento a otro) es, por definición, un defecto de diseño a corregir.

Dos principios ya presentes en el código actual se mantienen como no negociables en todo
el diseño:

- **Determinismo donde hay aritmética.** El LLM interpreta lenguaje; nunca calcula
  cantidades por reglas ("1 NVR por cada 8 cámaras"). Eso lo resuelve código determinista
  contra datos de catálogo. Ya es así en `expand_with_rules`; el diseño lo generaliza, no
  lo cambia.
- **Aprobación humana en decisiones de negocio.** La IA genera borradores y propuestas;
  aprobar una cotización o facturar sigue siendo un acto humano. El AI Engine amplía qué
  se automatiza (redactar, calcular, poblar) pero no mueve esta frontera.

## Estado actual — qué motor cubre cada pieza ya construida

| Pieza ya construida | Motor al que corresponde |
|---|---|
| `Survey` (notas, medidas, observaciones, fotos/audio) + Web Speech API en el frontend | Entrada de Motor 1 |
| `ai_engine/nlu.py::interpret_survey_items` → `ai_engine/catalog_matching.py::match_entities_to_catalog` (dos llamadas al modelo, Fase 1) | Motor 1 y Motor 2 (separados) |
| `Product.tags` / `Product.synonyms` (JSON) | Motor 3 (embrionario) |
| `CatalogRule` + `TechnicalRule` + `expand_with_rules` (accesorio por cantidad, fijo o proporcional) | Motor 4 (implementado — Fase 2) |
| `totals.py` + `ai_engine/calculation.py::apply_cable_waste_margin` + `calculation_parameters` | Motor 5 (solo cable — Fase 3) |
| `generate_from_survey`, `build_budget`, `build_quote_from_budget`, `build_pre_invoice_from_quote`, `mark_quote_approved`, `purchase-list-preview`, `pdf.py` variante `ejecutiva` | Motor 6 (implementado — Fase 4) |
| `embeddings.py` (embedding por proyecto + búsqueda semántica) | Soporte transversal para `ai/ask` |
| `ai_feedback_events` + `ai_engine/learning.py` (captura pasiva) | Motor 7 (solo captura — Fase 5; sin análisis periódico) |

Esto importa porque el trabajo real no es "construir 7 motores nuevos": es **separar
responsabilidades que hoy viven mezcladas en `ai_client.py`** y **rellenar los huecos**
(reglas generales, cálculos técnicos, aprendizaje) sin tocar el pipeline que ya corre.

## Arquitectura general

Se propone un paquete nuevo `backend/app/ai_engine/`, hermano de `services/`, que agrupa
los 7 motores como módulos independientes detrás de un orquestador. Los routers HTTP
(`ai.py`, `budgets.py`, `invoices.py`) dejan de llamar directamente a `ai_client.py` y
pasan a llamar al orquestador; siguen siendo controladores delgados.

```
app/ai_engine/
├── orchestrator.py        # coordina la tubería completa (equivalente a generate_from_survey hoy)
├── contracts.py           # tipos compartidos entre motores (Pydantic, sin lógica)
├── nlu/                   # Motor 1 — interpretación del lenguaje
├── catalog/                # Motor 2 — catálogo inteligente
├── tagging/                 # Motor 3 — sistema de etiquetas
├── rules/                   # Motor 4 — reglas técnicas
├── calculation/              # Motor 5 — cálculos
├── documents/                 # Motor 6 — generación documental
└── learning/                   # Motor 7 — aprendizaje
```

Cada motor expone **una** interfaz pública (una clase o función de entrada) y no conoce
los detalles internos de los demás — solo los contratos en `contracts.py`. Esto es lo que
permite ampliar a nuevas áreas técnicas (incendio, intrusión, domótica) agregando
implementaciones nuevas dentro de cada motor, sin tocar los otros seis.

**Por qué no es un rediseño de infraestructura:** sigue siendo FastAPI + SQLAlchemy +
Ollama local, el mismo stack ya validado. El cambio es de organización del código y del
modelo de datos, no de tecnología.

### Contratos compartidos (`contracts.py`)

Estos son los tipos que cruzan las fronteras entre motores — el "idioma común" del AI
Engine. Todos son estructuras de datos (Pydantic), no lógica:

- `RawSurveyInput` — texto, transcripción de voz, rutas de fotos, medidas sueltas. Entrada
  del pipeline completo.
- `DetectedEntity` — `{tipo, valor, cantidad, unidad, texto_original, confianza}`. Salida
  de Motor 1, antes de resolverse contra el catálogo real.
- `CatalogMatch` — `DetectedEntity` ya resuelta a un `product_id` (o `None` si no hay
  match, ej. mano de obra o servicios). Salida de Motor 2.
- `RuleEffect` — un ítem agregado o una advertencia generada por Motor 4/5, con la regla
  que lo originó (trazabilidad: "esto se agregó porque existe la regla X").
- `DocumentSet` — el resultado de una corrida de Motor 6: qué documentos se crearon,
  cuáles ya existían (idempotencia), cuáles quedaron pendientes de aprobación humana.

## Motor 1 — Interpretación del lenguaje (NLU)

**Responsabilidad:** convertir texto/voz en entidades estructuradas, sin resolverlas
todavía contra el catálogo. Hoy esto está fusionado con Motor 2 dentro de
`suggest_budget_items` (un solo prompt que interpreta *y* matchea contra la lista de
productos disponible). Separarlo importa por dos razones: (1) permite reusar la
interpretación para otras áreas técnicas que no comparten el mismo catálogo, y (2) permite
guardar la entidad "cruda" detectada aunque no exista producto — dato valioso para Motor 7
(aprendizaje) y para detectar catálogo incompleto.

**Entrada:** `RawSurveyInput` (texto de notas/observaciones, transcripción de audio si
existe, descripciones generadas por el modelo de visión sobre las fotos).

**Salida:** `list[DetectedEntity]` — productos, cantidades, medidas, distancias, marcas,
modelos, colores, ubicaciones, materiales, equipos, accesorios mencionados, cada uno con
el texto original que lo originó (auditable, y necesario para reintentar si el matching de
Motor 2 falla).

**Interfaz:**
```
interpretar(input: RawSurveyInput) -> list[DetectedEntity]
```

**Diseño respecto a lo actual:** la conversión de números en palabras ("ocho cámaras" →
8) y el reconocimiento de sinónimos/contexto que hoy vive como instrucciones dentro del
prompt de `suggest_budget_items` se mantiene como técnica (few-shot sobre el modelo local
vía Ollama, JSON estructurado) pero se separa en un prompt propio de Motor 1 que **no**
recibe el catálogo — solo extrae entidades. Motor 2 las resuelve después. Esto también
resuelve un problema latente: hoy, si un producto no está en el catálogo, la IA lo pierde
silenciosamente (la instrucción actual es "usa solo productos del catálogo"); con Motor 1
separado, la entidad detectada pero no resuelta se conserva y se expone en el borrador
como "no encontrado en catálogo" en vez de desaparecer.

**Modelo de datos nuevo:** ninguno obligatorio; opcionalmente una tabla
`survey_detected_entities` (efímera, por corrida) si se quiere mostrarle al técnico qué
detectó la IA antes de que Motor 2 la resuelva — útil para depuración y para Motor 7.

## Motor 2 — Catálogo inteligente

> **Estado: los dos huecos de datos quedaron cerrados; matching sigue siendo el mismo de
> Fase 1.** `Product` tiene `cost`, `install_minutes`, `labor_role` y `priority` (migración
> `bc52912f5a4c`) — el insumo que le faltaba a Motor 5 para poder construir
> `LaborCalculator` más adelante. `product_relations` también existe (migración
> `21847344e44d`), con CRUD en `/api/catalog/{product_id}/relations` y
> `/api/catalog/relations/{relation_id}`. El matching en sí
> (`catalog_matching.match_entities_to_catalog`) no cambió: sigue resolviendo por
> nombre/categoría/tags/sinónimos — ninguno de estos campos nuevos participa en esa
> decisión, son datos informativos/de apoyo, no señales de matching.

**Responsabilidad:** resolver cada `DetectedEntity` contra un producto real del catálogo,
usando nombre, categoría, tags y sinónimos (Motor 3). Ya existe como concepto
(`_build_catalog_dicts`, matching embebido en el prompt); el diseño lo separa en su propio
motor y completa los campos de producto que pide el objetivo pero que hoy no están en el
modelo:

| Campo pedido | Estado en `Product` |
|---|---|
| Código, clasificación/subclasificación, nombre comercial/técnico, descripción, unidad, marca, modelo, precio | Ya existían (`code`, `category` jerárquica, `name`, `commercial_description`/`technical_description`, `unit`, `brand`, `model`, `price`) |
| Costo | ✅ Implementado — `cost`, distinto de `price` (venta) |
| Etiquetas, sinónimos | Ya existían (`tags`, `synonyms`, JSON) |
| Compatibilidades, productos relacionados | ✅ Implementado — `product_relations` |
| Reglas técnicas | Ya existe como `CatalogRule`/`TechnicalRule` (ver Motor 4) |
| Tiempo de instalación, mano de obra asociada | ✅ Implementado — `install_minutes`, `labor_role` |
| Nivel de prioridad | ✅ Implementado — `priority` (entero, sin escala fija: nada la define todavía) |

**Interfaz:**
```
resolver(entidades: list[DetectedEntity], catalogo: list[Product]) -> list[CatalogMatch]
perfil_instalacion(product_id) -> InstallationProfile  # tiempo, mano de obra, prioridad
```

**Modelo de datos:**
- ✅ `Product` extendido con `cost: Numeric`, `install_minutes: Numeric | None`,
  `labor_role: str | None` (qué tipo de técnico lo instala), `priority: int | None`. Todos
  nullable o con default — ningún producto existente quedó sin valor válido.
- ✅ `product_relations`: `product_id`, `related_product_id`, `relation_type`
  (`compatible_con` | `alternativa_de` | `requiere`), `notes`. Se guarda una sola fila
  dirigida por relación (no una por cada sentido); `GET /api/catalog/{id}/relations`
  consulta ambos lados y normaliza la dirección (`outgoing`/`incoming`) más el nombre del
  otro producto, para que verla desde cualquiera de los dos productos involucrados
  muestre lo mismo sin duplicar filas. Deliberadamente separada de
  `CatalogRule`/`TechnicalRule`: una relación de compatibilidad es informativa (para quien
  arma el presupuesto a mano), una regla técnica es prescriptiva (agrega algo
  automáticamente). Mezclarlas obligaría a que toda relación dispare una acción, lo cual
  no es cierto.

## Motor 3 — Sistema de etiquetas

**Responsabilidad:** que "cable de red", "utp", "cat6" y "ethernet" resuelvan al mismo
producto. Ya existe como columna JSON en `Product` (`tags`, `synonyms`); el gap no es el
almacenamiento sino que **el matching de tags está hoy hardcodeado dentro del texto del
prompt** de `suggest_budget_items` (`_format_catalog_line`), en vez de ser un servicio
reusable.

**Diseño propuesto:** un servicio `TagIndex` (no una tabla nueva, para no romper lo que ya
funciona) que centraliza:
- Normalización de texto en español (minúsculas, sin tildes) para comparar de forma
  consistente en todos los puntos que hoy hacen matching de tags (Motor 2, buscador de
  catálogo, futuro Motor 1 cuando valide si una entidad detectada tiene análogo en
  catálogo).
- Expansión de sinónimos antes de pasarle el catálogo al LLM, y también como filtro
  determinista de respaldo si el modelo local falla en matchear (búsqueda por substring
  sobre tags normalizados).

**Cuándo pasar a una tabla de taxonomía propia:** si en el futuro los tags empiezan a
duplicarse o a escribirse de forma inconsistente entre productos (ej. "cat6" en uno,
"categoría 6" en otro, sin relación declarada), ahí se justifica una tabla `tags` con
alias canónicos. Hoy, con JSON libre por producto, no hay evidencia de ese problema — no
construirlo por adelantado.

## Motor 4 — Motor de reglas técnicas

> **Estado: implementado (Fase 2).** `TechnicalRule` ya existe (tabla `technical_rules`,
> migración `99fe2962bc29`), con CRUD en `/api/catalog/{product_id}/technical-rules` y
> `/api/catalog/technical-rules/{rule_id}`. `CatalogRule` no se tocó ni se migró — ambas
> fuentes conviven y se combinan en `build_accessory_rule_dicts`
> (`app/ai_engine/rules.py`) antes de llamar a `expand_with_rules`, así que una regla
> creada por cualquiera de los dos mecanismos tiene el mismo efecto en la generación de
> presupuesto. El resto de esta sección describe el diseño tal como quedó, para orientar
> el siguiente tipo de acción que se agregue.

**Responsabilidad:** codificar conocimiento técnico como reglas configurables desde el
ERP, sin tocar código. `CatalogRule` modela **un solo tipo** de regla: "si el catálogo
incluye N unidades de un producto fuente, agregar M unidades de un accesorio identificado
por tag". El objetivo pide reglas más generales ("si existe fibra → agregar pigtails",
"si existe rack → agregar organizadores"), que de hecho ya caben en el modelo actual
(fibra y rack son "productos fuente" como cualquier cámara). El gap real no era
expresividad de condición — era que **la única acción posible era "agregar accesorio con
cantidad"**.

**Diseño:** `TechnicalRule` generaliza `CatalogRule` con condición y acción tipadas,
donde el tipo de acción actual (`add_accessory`) es una de varias posibles a futuro:

- `condition`: `source_product_id` (igual que `CatalogRule`) — no hizo falta un lenguaje
  de condiciones más rico; todas las reglas del objetivo son "si existe producto X".
- `action_type`: hoy solo `add_accessory` tiene manejador implementado (mismo
  comportamiento que `CatalogRule`, vía `expand_with_rules`). El diseño deja espacio para
  `set_calculation_parameter` (ej. "si existe fibra, el margen de desperdicio de cable
  sube a 8%", Motor 5) y `flag_engineering_note` (ej. "verificar distancia máxima de
  fibra monomodo", Motor 6) — ninguno de los dos se implementó todavía porque los
  sistemas que consumirían esa señal (`calculation_parameters`, borrador de ingeniería
  guiado por reglas) tampoco existen aún; declarar esos tipos ahora sin un consumidor real
  habría sido un action_type muerto.
- `action_params` (JSON) guarda los parámetros propios de cada `action_type` en vez de
  columnas por tipo — agregar una acción nueva no pide migración, solo un manejador nuevo
  en `app/ai_engine/rules.py` (ver `_technical_rule_to_dict`) y una variante nueva en el
  esquema de creación (`TechnicalRuleCreate`, hoy fijo a `Literal["add_accessory"]`).
- La tabla `catalog_rules` existente se mantiene tal cual (no se migró, no se rompió).

**Interfaz (implementada):**
```
build_accessory_rule_dicts(catalog_rules, technical_rules) -> list[dict]   # ai_engine/rules.py
expand_with_rules(items, catalog, rules) -> list[dict]                     # sin cambios
```

**Por qué no un motor de reglas genérico (tipo Drools):** el objetivo pide "configurable
desde el ERP", no "Turing-completo". Un editor de condición/acción tipado (dropdowns:
producto fuente, tipo de acción, parámetros) es administrable por una persona de oficina
sin conocer programación; un lenguaje de reglas libre no lo es, y añade una superficie de
seguridad (ejecutar reglas arbitrarias) que no hace falta.

## Motor 5 — Motor de cálculos

> **Estado: dos de cuatro calculadoras implementadas.** `CableCalculator`
> (`apply_cable_waste_margin`, Fase 3) y `LaborCalculator` (`calculate_labor` +
> `build_labor_budget_item`) corren dentro de `ai_budget_suggestions` y
> `generate_from_survey`, después de `expand_with_rules`. `calculation_parameters` tiene
> tres claves conocidas: `cable_waste_margin_pct` (default 5%), `labor_hourly_rate`
> (default RD$200/hora) y `labor_max_hours_per_technician` (default 40h — una semana
> laboral). `StorageCalculator` y `CapacityCalculator` siguen sin implementar — esperan
> datos que todavía no existen (resolución de cámara, capacidad de canal de NVR/switch).

**Responsabilidad:** toda la aritmética técnica y comercial que hoy falta. `totals.py` ya
cubre lo financiero genérico (subtotal/ITBIS/total); `expand_with_rules` ya cubre
cantidad-por-accesorio. Lo que sigue sin existir: canalización, conectores, capacidad de
NVR/DVR, capacidad de disco, cantidad de switches.

**Diseño:** un `CalculationEngine` que despacha a **calculadoras** independientes por tipo
de cálculo, cada una una función pura `(items_resueltos, parámetros) -> ajustes`:

- ✅ `CableCalculator` (`apply_cable_waste_margin`) — aumenta la cantidad de los ítems ya
  resueltos cuyo producto tiene el tag `cable`, aplicando el margen de desperdicio
  configurado. Ajusta la cantidad de la misma línea (es más del mismo producto, no un
  producto nuevo) — a diferencia de `expand_with_rules`, que sí agrega líneas nuevas.
- ✅ `LaborCalculator` (`calculate_labor` + `build_labor_budget_item`) — suma
  `install_minutes × cantidad` de cada ítem resuelto (Motor 2) para estimar horas
  totales, agrega una línea de "Mano de obra de instalación" al presupuesto
  (`product_id=None`, igual que un servicio mencionado a mano) con `quantity=horas` y
  `unit_price=labor_hourly_rate`, y calcula `cantidad de técnicos` como
  `ceil(horas / labor_max_hours_per_technician)`. El costo de mano de obra es horas
  totales × tarifa, sin dividir entre técnicos (se paga por hora-persona trabajada, no
  por técnico en paralelo). `labor_role` se usa para desglosar las horas por tipo de
  técnico en la descripción de la línea (transparencia), no para aplicar una tarifa
  distinta por rol — eso requeriría una tarifa configurable por rol, que no existe
  todavía y no se construyó por no tener un caso de uso real que la pidiera. Si nada en
  el presupuesto tiene `install_minutes` cargado, no agrega ninguna línea (en vez de un
  "RD$0 de mano de obra" que no aporta nada).
- `StorageCalculator` — capacidad de disco requerida, a partir de cámaras × resolución ×
  días de retención (parámetros configurables, no hardcodeados). Pendiente.
- `CapacityCalculator` — canales de NVR/puertos de switch necesarios vs. disponibles en el
  producto elegido; genera una `RuleEffect` de tipo advertencia si no alcanza. Pendiente.

Cada calculadora es un módulo independiente y **agregable**: sumar una nueva área técnica
(ej. detección de incendios) puede requerir una calculadora nueva (ej. cobertura de
detectores por metro cuadrado) sin tocar las demás.

**Modelo de datos (implementado):** `calculation_parameters` (`key` único, `value`
numérico, `description`). Sin fila para una clave conocida = se usa el default de código
en `KNOWN_PARAMETERS`, así que el cálculo funciona desde el primer día sin que un admin
tenga que configurar nada — solo lo hace si quiere cambiar el valor por defecto. Agregar
una clave nueva (ej. para `StorageCalculator`) es: registrarla en `KNOWN_PARAMETERS` +
que la calculadora correspondiente la lea con `get_calculation_parameter`.

**Interfaz (implementada, para `CableCalculator`):**
```
get_calculation_parameter(db, key) -> float                                    # ai_engine/calculation.py
apply_cable_waste_margin(items, catalog, waste_margin_pct) -> list[dict]       # ai_engine/calculation.py
```

## Motor 6 — Motor de generación documental

> **Estado: los dos huecos de la Fase 4 quedaron cerrados.** `GET
> /api/quotes/{id}/purchase-list-preview` expone la lista de compras preliminar (solo
> lectura) y `GET /api/quotes/{id}/pdf?variant=ejecutiva` genera la cotización ejecutiva
> como una plantilla distinta sobre el mismo `Quote`. El orquestador general
> (`generar_desde_levantamiento` → `DocumentSet`) descrito más abajo sigue sin
> construirse — `generate_from_survey` sigue siendo la función concreta que hace ese
> trabajo, no una interfaz genérica; generalizarla queda para cuando haga falta un
> segundo flujo de generación que la necesite.

**Responsabilidad:** producir todos los documentos del proyecto sin recapturar
información. Este es el motor más maduro: `generate_from_survey` ya encadena
`suggest_budget_items` → `expand_with_rules` → `apply_cable_waste_margin` →
`build_budget` → `build_quote_from_budget` → borrador de ingeniería (best-effort), y
`mark_quote_approved` ya genera Materiales (lista de compras) y Prefactura
automáticamente al aprobar la cotización.

- **Lista de Compras preliminar (implementado).** `Material` se sigue generando recién al
  aprobar la cotización — correcto como comportamiento de negocio (no tiene sentido
  comprar algo no aprobado). Lo nuevo es una vista de solo lectura,
  `GET /api/quotes/{quote_id}/purchase-list-preview`, que muestra exactamente lo que
  `mark_quote_approved` generaría como `Material` si esa cotización se aprobara ahora,
  sin crear ninguna fila. Ambos caminos leen de la misma función
  (`quote_approval.build_material_rows_from_quote`) para que la vista previa no pueda
  divergir de lo que realmente se crea al aprobar.
- **Cotización Ejecutiva vs. Detallada (implementado).** No se duplicó el registro
  financiero: `ejecutiva` es una plantilla de renderizado distinta
  (`GET /api/quotes/{quote_id}/pdf?variant=ejecutiva`) sobre el mismo `Quote` — agrupa las
  líneas por categoría de catálogo (o "Mano de obra y servicios" para líneas sin
  producto) y muestra subtotal/ITBIS/total, sin desglose línea por línea. Mismo `pdf.py`
  que ya generaba la cotización detallada y la factura (con su propia variante `global`).

**Interfaz (orquestador, generaliza `generate_from_survey` — no construida todavía):**
```
generar_desde_levantamiento(survey) -> DocumentSet
```
donde `DocumentSet` reportaría qué se creó, qué ya existía (idempotencia — patrón ya
usado en `build_pre_invoice_from_quote`), y qué queda pendiente de aprobación humana.

**No cambia:** la frontera de aprobación humana antes de Prefactura→Factura, ni el
patrón "best-effort" para el borrador de ingeniería (si falla, no debe tumbar la
generación de presupuesto/cotización que sí funcionó).

## Motor 7 — Aprendizaje

> **Estado: captura pasiva implementada (Fase 5); el análisis periódico sigue sin
> construirse, como marcaba el plan.** `ai_feedback_events` existe y se escribe sola en
> `PUT /api/budgets/{id}` y `PUT /api/projects/{id}/engineering` cuando el registro
> editado todavía tenía `ai_generated=True` (ver `app/ai_engine/learning.py`). Hay un
> endpoint de solo lectura, `GET /api/ai-feedback-events`, para poder ver lo capturado —
> pero nada agrega patrones ni propone reglas todavía; eso espera a tener volumen real de
> proyectos, tal como se decidió al planear esta fase.

**Responsabilidad:** que el sistema mejore sus sugerencias a partir de las correcciones
que oficina/ingeniería hacen sobre lo que la IA propuso. Antes de esta fase no existía
ningún registro de esto — cuando alguien editaba un `Budget` generado por IA (cambiaba un
producto, quitaba un accesorio sugerido, ajustaba una cantidad), esa señal se perdía.

**Diseño (implementado) — captura pasiva, sin cambiar el flujo de trabajo del usuario:**

- Tabla `ai_feedback_events`: `project_id`, `entity_type` (`budget_item` | `engineering`),
  `origin` (`human_added` | `human_removed` | `human_modified` — `ai_suggested` queda
  declarado en el dominio del campo pero nada lo escribe todavía, ver más abajo),
  `product_id | None`, `field_changed | None`, `old_value`, `new_value`, `created_at`.
- `Budget` y `Engineering` ganaron `ai_generated: bool`. Se pone en `True` únicamente
  cuando `generate_from_survey` los crea/rellena; una creación manual nunca lo activa.
- Se registra automáticamente en los puntos donde ya existe edición humana sobre algo
  generado por IA (`update_budget`, `update_engineering`): mientras `ai_generated` siga en
  `True`, el contenido actual en la base de datos ES por definición lo que la IA sugirió
  (nada lo tocó todavía) — así que no hizo falta una tabla de "snapshot" aparte, solo
  comparar ese estado contra el payload entrante antes de aplicarlo. Tras registrar el
  diff, `ai_generated` pasa a `False`, para que una segunda edición humana no se compare
  contra la sugerencia original (ya no hay una "sugerencia de IA" con la cual contrastar).

**Uso de la señal — deliberadamente no automático:** Motor 7 no reescribe `CatalogRule`
ni `Product.tags` por su cuenta, y esta fase no construyó el job que sí lo haría. Cuando
exista, sería un **análisis periódico** (job, no tiempo real) que agrega patrones ("en el
80% de los proyectos con fibra, se agregó manualmente `Organizador de rack` aunque no está
sugerido") y los presenta como **propuesta de nueva regla** a un administrador, igual que
una cotización pendiente espera aprobación. Esto respeta el principio de aprobación
humana ya establecido en el resto del sistema y evita que un patrón espurio (ej. un solo
proyecto atípico) contamine el catálogo de reglas para todos. Construirlo ahora, sin
datos reales que analizar, habría sido especular sobre qué forma deben tener los
patrones — mejor esperar al volumen real de proyectos que ya está capturando esta fase.

## Modelo de datos consolidado

| Tabla | Estado | Motor |
|---|---|---|
| `products` | ✅ Extendido: `cost`, `install_minutes`, `labor_role`, `priority` (implementado) | 2 |
| `product_relations` | ✅ Nueva (implementada) | 2 |
| `catalog_rules` | Sin cambios (se mantiene) | 4 |
| `technical_rules` | Nueva (generalización hacia adelante de `catalog_rules`) | 4 |
| `calculation_parameters` | Nueva | 5 |
| `ai_feedback_events` | ✅ Nueva (implementada — Fase 5) | 7 |
| `budgets` / `engineering` | ✅ Extendidas: `ai_generated: bool` (implementado — Fase 5) | 6, 7 |

Todas las tablas nuevas siguen el patrón ya usado en el proyecto (SQLAlchemy 2 + Alembic,
columnas JSON para listas en vez de arrays nativos, para compatibilidad SQLite/Postgres
como ya hace `Product.tags` y `ProjectEmbedding.embedding`).

## Flujo end-to-end (con el AI Engine ya integrado)

```
Levantamiento (voz/foto/texto/medidas)
        │
        ▼
Motor 1 — interpretar()  →  entidades detectadas (con o sin match a catálogo)
        │
        ▼
Motor 2 + 3 — resolver()  →  entidades resueltas a productos reales
        │
        ▼
Motor 4 — evaluar()  →  accesorios/ajustes por regla técnica
        │
        ▼
Motor 5 — calcular()  →  metraje, capacidad, mano de obra, advertencias
        │
        ▼
Motor 6 — generar_desde_levantamiento()
        │
        ├─ Presupuesto (automático)
        ├─ Cotización Ejecutiva + Detallada (automático, estado "pendiente")
        ├─ Ingeniería (borrador best-effort)
        └─ Lista de Compras preliminar (solo lectura)
        │
        ▼
   [APROBACIÓN HUMANA — frontera que no se automatiza]
        │
        ▼
Materiales (lista de compras real) + Prefactura (automático al aprobar)
        │
        ▼
   [CONVERSIÓN A FACTURA — manual, solo admin, NCF real]
        │
        ▼
Factura
        │
        ▼
Motor 7 — captura pasiva de toda edición humana sobre lo generado por IA
        →  análisis periódico → propuestas de nuevas reglas/tags → aprobación admin
```

## Extensibilidad a nuevas áreas técnicas

El diseño soporta agregar una nueva área (detección de incendios, control de acceso,
intrusión, domótica) sin modificar el núcleo de ningún motor, porque cada motor recibe la
especialización como **datos**, no como código nuevo:

- **Motor 2/3:** productos y tags nuevos se agregan al catálogo existente; la jerarquía de
  `Category` ya es genérica (una categoría raíz "Detección de Incendios" con sus
  subcategorías cuelga del mismo árbol que "CCTV").
- **Motor 4:** reglas nuevas ("si existe panel de incendio → agregar batería de respaldo")
  se crean como filas de `technical_rules`, no como código.
- **Motor 5:** si el área nueva requiere un cálculo sin precedente (ej. cobertura de
  detectores de humo por metro cuadrado), ahí sí hace falta una `Calculator` nueva — es el
  único punto de extensión que requiere código, y es aditivo (una clase nueva, no tocar
  las existentes).
- **Motor 1:** el prompt de interpretación no está atado a CCTV/redes por diseño (ya dice
  "seguridad electrónica" en general); una entidad de un dominio nuevo se detecta igual.
- **Motor 6:** el pipeline de generación documental es agnóstico al área técnica — genera
  presupuesto/cotización a partir de lo que Motor 2-5 resolvieron, sin importar el dominio.

## Plan de evolución incremental

No se propone una reescritura. Orden sugerido, cada fase entregable sin dejar el sistema
en un estado roto:

1. ✅ **Reorganizar sin cambiar comportamiento:** mover `ai_client.py`/`quote_rules.py` a
   la estructura `ai_engine/`, separando NLU (Motor 1) de matching de catálogo (Motor 2)
   en dos llamadas al modelo en vez de una — esto ya destraba guardar entidades sin match.
2. ✅ **Generalizar `CatalogRule` → `TechnicalRule`** sin migrar datos existentes (tabla
   nueva en paralelo; `expand_with_rules` sigue funcionando igual para lo ya configurado).
3. ✅ **Motor 5 (parcial):** agregada `calculation_parameters` + `CableCalculator` (la de
   mayor impacto/menor riesgo, primero) y después `LaborCalculator` (una vez que Motor 2
   tuvo `install_minutes`/`labor_role`). `StorageCalculator` y `CapacityCalculator` siguen
   esperando datos que no existen (capacidad de canal, resolución de cámara).
4. ✅ **Motor 6:** cerrado el hueco de "lista de compras preliminar" y "cotización
   ejecutiva" como vista, sin nuevas tablas financieras.
5. ✅ **Motor 7 (parcial):** instrumentada la captura pasiva de ediciones
   (`ai_feedback_events`). El análisis periódico que convierte esos eventos en propuestas
   de reglas queda pendiente — espera a tener volumen suficiente de proyectos para que los
   patrones sean confiables.

Cada fase es útil por sí sola y ninguna depende de que las siguientes existan — se puede
pausar el plan en cualquier punto sin dejar deuda a medias.

Con las 5 fases del plan original completas (algunas parciales por diseño, esperando
datos reales o campos de otro motor), lo que sigue no es una fase numerada más sino
trabajo dirigido por lo que el uso real revele: qué calculadoras de Motor 5 hacen falta
primero, cuándo hay volumen suficiente para el análisis de Motor 7, o si aparece una
segunda área técnica que ponga a prueba la extensibilidad del diseño.

**Extensiones posteriores:**
- **Motor 2 completo:** `Product` ganó `cost`, `install_minutes`, `labor_role` y
  `priority` (migración `bc52912f5a4c`); después, `product_relations` (migración
  `21847344e44d`) cerró el último hueco de datos de Motor 2 — compatibilidades y
  productos relacionados, con CRUD en `/api/catalog/{product_id}/relations`. Con esto,
  todos los campos que el objetivo original pedía para el catálogo inteligente están
  implementados.
- **Motor 5 — `LaborCalculator`:** construido una vez que Motor 2 tuvo los datos que
  necesitaba. `StorageCalculator`/`CapacityCalculator` siguen siendo los huecos abiertos
  de Motor 5.
