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
| `ai_client.summarize_survey`, `suggest_budget_items` (prompt con catálogo embebido) | Motor 1 + Motor 2 (mezclados) |
| `Product.tags` / `Product.synonyms` (JSON) | Motor 3 (embrionario) |
| `CatalogRule` + `expand_with_rules` (accesorio por cantidad, fijo o proporcional) | Motor 4 (un solo tipo de regla) |
| `totals.py` (subtotal/ITBIS/total) | Motor 5 (solo financiero, no técnico) |
| `generate_from_survey`, `build_budget`, `build_quote_from_budget`, `build_pre_invoice_from_quote`, `mark_quote_approved` (auto-genera Materiales y Prefactura al aprobar) | Motor 6 (pipeline ya funcionando, sin "lista de compras" ni "cotización ejecutiva" como artefactos propios) |
| `embeddings.py` (embedding por proyecto + búsqueda semántica) | Soporte transversal para `ai/ask` |
| — | Motor 7 no existe todavía |

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

**Responsabilidad:** resolver cada `DetectedEntity` contra un producto real del catálogo,
usando nombre, categoría, tags y sinónimos (Motor 3). Ya existe como concepto
(`_build_catalog_dicts`, matching embebido en el prompt); el diseño lo separa en su propio
motor y completa los campos de producto que pide el objetivo pero que hoy no están en el
modelo:

| Campo pedido | Estado en `Product` hoy |
|---|---|
| Código, clasificación/subclasificación, nombre comercial/técnico, descripción, unidad, marca, modelo, precio | Ya existen (`code`, `category` jerárquica, `name`, `commercial_description`/`technical_description`, `unit`, `brand`, `model`, `price`) |
| Costo | **Falta** — hoy solo hay `price` (venta), no `cost` |
| Etiquetas, sinónimos | Ya existen (`tags`, `synonyms`, JSON) |
| Compatibilidades, productos relacionados | **Falta** — no hay tabla de relación producto↔producto |
| Reglas técnicas | Ya existe como `CatalogRule`, pero acoplada a un solo tipo de regla (ver Motor 4) |
| Tiempo de instalación, mano de obra asociada | **Falta** |
| Nivel de prioridad | **Falta** |

**Interfaz:**
```
resolver(entidades: list[DetectedEntity], catalogo: list[Product]) -> list[CatalogMatch]
perfil_instalacion(product_id) -> InstallationProfile  # tiempo, mano de obra, prioridad
```

**Modelo de datos nuevo:**
- Extender `Product` con `cost: Numeric`, `install_minutes: Numeric | None`,
  `labor_role: str | None` (qué tipo de técnico lo instala), `priority: int | None`.
- `product_relations` (tabla nueva): `product_id`, `related_product_id`, `relation_type`
  (`compatible_con` | `alternativa_de` | `requiere`). Deliberadamente separada de
  `CatalogRule`: una relación de compatibilidad es informativa (para quien arma el
  presupuesto a mano), una `CatalogRule` es prescriptiva (agrega algo automáticamente).
  Mezclarlas obligaría a que toda relación dispare una acción, lo cual no es cierto.

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

**Responsabilidad:** codificar conocimiento técnico como reglas configurables desde el
ERP, sin tocar código. Ya existe `CatalogRule`, pero modela **un solo tipo** de regla:
"si el catálogo incluye N unidades de un producto fuente, agregar M unidades de un
accesorio identificado por tag". El objetivo pide reglas más generales ("si existe fibra
→ agregar pigtails", "si existe rack → agregar organizadores"), que de hecho ya caben en
el modelo actual (fibra y rack son "productos fuente" como cualquier cámara). El gap real
no es expresividad de condición — es que **la única acción posible hoy es "agregar
accesorio con cantidad"**.

**Diseño propuesto:** generalizar `CatalogRule` a una entidad `TechnicalRule` con
condición y acción tipadas, donde el tipo de acción actual (`add_accessory`) es una de
varias:

- `condition`: `{source_product_id}` (igual que hoy) — no hace falta un lenguaje de
  condiciones más rico todavía; todas las reglas del objetivo son "si existe producto X".
- `action_type`: `add_accessory` (comportamiento actual, sin cambios) | `set_calculation_parameter`
  (ej. "si existe fibra, el margen de desperdicio de cable sube a 8%") | `flag_engineering_note`
  (agrega una observación sugerida al borrador de ingeniería, ej. "verificar distancia
  máxima de fibra monomodo").
- La tabla `catalog_rules` existente se mantiene tal cual (no se migra, no se rompe);
  `TechnicalRule` es la generalización hacia adelante, y `expand_with_rules` pasa a ser
  el manejador del `action_type = add_accessory`, uno más entre varios que el orquestador
  de Motor 4 despacha.

**Interfaz:**
```
evaluar(items_resueltos: list[CatalogMatch], reglas: list[TechnicalRule]) -> list[RuleEffect]
```

**Por qué no un motor de reglas genérico (tipo Drools):** el objetivo pide "configurable
desde el ERP", no "Turing-completo". Un editor de condición/acción tipado (dropdowns:
producto fuente, tipo de acción, parámetros) es administrable por una persona de oficina
sin conocer programación; un lenguaje de reglas libre no lo es, y añade una superficie de
seguridad (ejecutar reglas arbitrarias) que no hace falta.

## Motor 5 — Motor de cálculos

**Responsabilidad:** toda la aritmética técnica y comercial que hoy falta. `totals.py` ya
cubre lo financiero genérico (subtotal/ITBIS/total); `expand_with_rules` ya cubre
cantidad-por-accesorio. Lo que no existe: metraje de cable con margen de desperdicio,
canalización, conectores, capacidad de NVR/DVR, capacidad de disco, cantidad de switches,
tiempo de instalación, cantidad de técnicos, costo de mano de obra.

**Diseño propuesto:** un `CalculationEngine` que despacha a **calculadoras** independientes
por tipo de cálculo, cada una una función pura `(items_resueltos, parámetros) -> ajustes`:

- `CableCalculator` — metros de cable necesarios + margen de desperdicio configurable.
- `StorageCalculator` — capacidad de disco requerida, a partir de cámaras × resolución ×
  días de retención (parámetros configurables, no hardcodeados).
- `CapacityCalculator` — canales de NVR/puertos de switch necesarios vs. disponibles en el
  producto elegido; genera una `RuleEffect` de tipo advertencia si no alcanza.
- `LaborCalculator` — usa `install_minutes` y `labor_role` de Motor 2 para estimar horas,
  cantidad de técnicos y costo de mano de obra.

Cada calculadora es un módulo independiente y **agregable**: sumar una nueva área técnica
(ej. detección de incendios) puede requerir una calculadora nueva (ej. cobertura de
detectores por metro cuadrado) sin tocar las demás.

**Modelo de datos nuevo:** `calculation_parameters` — tabla clave/valor administrable
desde el ERP (`key`, `value`, `description`), para que "margen de desperdicio de cable",
"días de retención por defecto", "horas de instalación por cámara" sean configurables sin
desplegar código, igual que ya se pide para Motor 4.

**Interfaz:**
```
calcular(items_resueltos: list[CatalogMatch], contexto: ProjectContext, parametros: dict) -> list[RuleEffect]
```

## Motor 6 — Motor de generación documental

**Responsabilidad:** producir todos los documentos del proyecto sin recapturar
información. Este es el motor más maduro hoy: `generate_from_survey` ya encadena
`suggest_budget_items` → `expand_with_rules` → `build_budget` → `build_quote_from_budget`
→ borrador de ingeniería (best-effort), y `mark_quote_approved` ya genera Materiales
(lista de compras) y Prefactura automáticamente al aprobar la cotización. Lo que falta
frente al objetivo:

- **Lista de Compras como artefacto explícito antes de la aprobación.** Hoy los
  `Material` se generan recién cuando se aprueba la cotización — correcto como
  comportamiento de negocio (no tiene sentido comprar algo no aprobado), pero el objetivo
  pide que "Lista de Compras" exista como documento generable. Diseño: exponer una vista
  de "lista de compras preliminar" derivada directamente de las líneas del `Budget`/
  `Quote` en estado `pendiente` (solo lectura, sin crear filas de `Material` todavía) —
  así el técnico/oficina puede revisarla antes de la aprobación sin adelantar el efecto de
  negocio de generar `Material`.
- **Cotización Ejecutiva vs. Detallada.** Hoy solo existe un tipo de `Quote` (itemizado).
  Diseño: no duplicar el registro financiero — "Ejecutiva" es una **plantilla de
  renderizado** distinta (PDF resumen: totales por categoría, sin desglose línea por
  línea) sobre el mismo `Quote`, igual que ya existe un servicio `pdf.py` para el
  documento actual. Evita el riesgo de que ambas versiones diverjan en cifras.

**Interfaz (orquestador, generaliza `generate_from_survey`):**
```
generar_desde_levantamiento(survey) -> DocumentSet
```
donde `DocumentSet` reporta qué se creó, qué ya existía (idempotencia — patrón ya usado
en `build_pre_invoice_from_quote`), y qué queda pendiente de aprobación humana.

**No cambia:** la frontera de aprobación humana antes de Prefactura→Factura, ni el
patrón "best-effort" para el borrador de ingeniería (si falla, no debe tumbar la
generación de presupuesto/cotización que sí funcionó).

## Motor 7 — Aprendizaje

**Responsabilidad:** que el sistema mejore sus sugerencias a partir de las correcciones
que oficina/ingeniería hacen sobre lo que la IA propuso. Hoy no existe ningún registro de
esto — cuando alguien edita un `Budget` generado por IA (cambia un producto, quita un
accesorio sugerido, ajusta una cantidad), esa señal se pierde.

**Diseño propuesto — captura pasiva, sin cambiar el flujo de trabajo del usuario:**

- Tabla `ai_feedback_events`: `project_id`, `entity_type` (`budget_item` | `engineering`),
  `origin` (`ai_suggested` | `human_added` | `human_removed` | `human_modified`),
  `product_id | None`, `field_changed | None`, `old_value`, `new_value`, `created_at`.
- Se registra automáticamente en los puntos donde ya existe edición humana sobre algo
  generado por IA (`update_budget`, la edición de `Engineering`): diff entre lo que la IA
  puso originalmente (se conserva en la creación del `Budget`/`Engineering` con un flag
  `ai_generated`) y lo que quedó tras la edición humana.

**Uso de la señal — deliberadamente no automático:** Motor 7 no reescribe `CatalogRule`
ni `Product.tags` por su cuenta. Es un **análisis periódico** (job, no tiempo real) que
agrega patrones ("en el 80% de los proyectos con fibra, se agregó manualmente
`Organizador de rack` aunque no está sugerido") y los presenta como **propuesta de nueva
regla** a un administrador, igual que una cotización pendiente espera aprobación. Esto
respeta el principio de aprobación humana ya establecido en el resto del sistema y evita
que un patrón espurio (ej. un solo proyecto atípico) contamine el catálogo de reglas para
todos.

## Modelo de datos consolidado

| Tabla | Estado | Motor |
|---|---|---|
| `products` | Extender: `cost`, `install_minutes`, `labor_role`, `priority` | 2 |
| `product_relations` | Nueva | 2 |
| `catalog_rules` | Sin cambios (se mantiene) | 4 |
| `technical_rules` | Nueva (generalización hacia adelante de `catalog_rules`) | 4 |
| `calculation_parameters` | Nueva | 5 |
| `ai_feedback_events` | Nueva | 7 |
| `budgets` / `engineering` | Extender: `ai_generated: bool` (para poder diffear en Motor 7) | 6, 7 |

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

1. **Reorganizar sin cambiar comportamiento:** mover `ai_client.py`/`quote_rules.py` a la
   estructura `ai_engine/`, separando NLU (Motor 1) de matching de catálogo (Motor 2) en
   dos llamadas al modelo en vez de una — esto ya destraba guardar entidades sin match.
2. **Generalizar `CatalogRule` → `TechnicalRule`** sin migrar datos existentes (tabla
   nueva en paralelo; `expand_with_rules` sigue funcionando igual para lo ya configurado).
3. **Motor 5:** agregar `calculation_parameters` + la primera calculadora (`CableCalculator`,
   la de mayor impacto/menor riesgo) antes de las demás.
4. **Motor 6:** cerrar el hueco de "lista de compras preliminar" y "cotización ejecutiva"
   como vista, sin nuevas tablas financieras.
5. **Motor 7:** instrumentar la captura pasiva de ediciones; el análisis periódico puede
   esperar a tener volumen suficiente de proyectos para que los patrones sean confiables.

Cada fase es útil por sí sola y ninguna depende de que las siguientes existan — se puede
pausar el plan en cualquier punto sin dejar deuda a medias.
