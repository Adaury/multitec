# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [Sin publicar]

### Añadido

- **Control de inventario de bodega** en el Catálogo: cada producto tiene ahora
  `stock_quantity` y un botón para expandirlo y registrar **entradas/salidas**
  (`POST /api/products/{id}/stock-movements`) con motivo opcional e historial completo.
  Una salida que supere el stock disponible se rechaza con un mensaje claro (no deja el
  stock en negativo). Es un conteo de bodega independiente de los materiales por proyecto
  (`Material`, ya existente) — sirve para saber qué hay físicamente disponible más allá
  de lo ya asignado a un proyecto. Mismos roles que el resto del Catálogo (admin/oficina,
  sin acceso para `tecnico`). 6 tests nuevos.
- **Notificaciones automáticas por correo** (`backend/app/services/email.py` +
  `notifications.py`): cotización pendiente de aprobar (a los admins activos), ticket
  asignado (al técnico, sin re-notificar si se "reasigna" al mismo técnico), y factura
  emitida (al cliente, con el PDF adjunto, si tiene correo registrado). Configurable por
  `SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASSWORD`/`SMTP_FROM`/`SMTP_USE_TLS` en
  `.env` — sin `SMTP_HOST`, los correos solo se registran en el log (modo consola, no
  hace falta SMTP real para desarrollar). Un fallo de envío nunca revierte ni bloquea la
  operación que lo disparó, solo se registra el error. 6 tests nuevos.
- **Asignar técnico a un ticket desde la UI**: cada ticket tiene un selector "Técnico
  asignado" (al crearlo y para reasignarlo después), poblado desde el nuevo
  `GET /api/users/technicians` (nombre/id únicamente, a diferencia de `GET /api/users`
  que es admin-only y expone más datos — este lo puede llamar cualquier rol que gestione
  tickets). Antes `technician_id` existía en el modelo pero no había forma de asignarlo
  desde la interfaz, así que el Dashboard siempre mostraba todo bajo "Sin asignar".
  3 tests nuevos.
- **Búsqueda global** (`GET /api/search`, ícono 🔍 en el encabezado, accesible desde
  cualquier pantalla): encuentra clientes (nombre/empresa/RNC), proyectos (código,
  descripción, o por el nombre del cliente) y tickets (código o descripción del
  problema) mientras se escribe (debounce 300ms, mínimo 2 caracteres). Disponible para
  los tres roles, ya que solo expone lo que cada uno ya puede ver en sus respectivas
  listas. Los resultados de tickets llevan directo a la pestaña Tickets del proyecto
  (`/proyectos/{id}?tab=tickets` — la pestaña inicial de un proyecto ahora se puede fijar
  por URL). 4 tests nuevos.
- **Dashboard con reportes/KPIs** (`GET /api/reports/dashboard`, solo admin/oficina):
  cotizaciones pendientes de decisión, tickets abiertos (total y por técnico), proyectos
  agrupados por estado, y facturación de los últimos 6 meses en un gráfico de barras
  simple (CSS, sin librería de gráficos). Aparece en la pantalla de inicio arriba del
  menú; no visible para el rol `tecnico` (datos comerciales/financieros). 4 tests nuevos.
- **PDF de Cotización y Factura** (`GET /api/quotes/{id}/pdf`, `GET /api/invoices/{id}/pdf`,
  con `reportlab`): membrete de la empresa (nombre/RNC/dirección/teléfono, configurable en
  `.env`), datos del cliente y proyecto, líneas con precios, subtotal/ITBIS/total, y el
  NCF en la factura. Antes solo se podían ver en pantalla, sin forma de entregarle un
  documento formal al cliente. La Factura tiene una segunda versión, **"Detalle de
  trabajo (sin precios)"** (`?variant=global`): mismas líneas con descripción y cantidad,
  sin precio unitario ni desglose de ITBIS, pero con el **total general del servicio** al
  final (sin el NCF, que es propio del documento fiscal con precios) — para entregar como
  detalle técnico sin exponer el desglose de montos. Cada una de las dos versiones tiene
  botones **"Ver"** (abre el PDF en una pestaña nueva) y **"Descargar"**.
- **NCF (Números de Comprobante Fiscal) en Facturación**: secuencias autorizadas por la
  DGII administrables desde `/ncf` (solo admin) — tipo (B01 crédito fiscal, B02 consumo,
  B14 regímenes especiales, B15 gubernamental), rango, vencimiento y activar/desactivar.
  Al convertir una prefactura en factura se le asigna automáticamente el siguiente número
  de la secuencia vigente correspondiente (rechaza si está vencida, agotada o inactiva);
  el tipo por defecto se infiere de si el cliente tiene RNC (B01) o no (B02), pero el
  admin puede elegir otro tipo antes de convertir. El NCF queda expuesto en la factura y
  en el tab de Factura del proyecto. 8 tests nuevos.
- **Tests E2E de UI con Playwright** (`frontend/e2e/`), integrados a un nuevo job de CI
  (`E2E (Playwright)`) que levanta un backend real (SQLite fresco + migraciones +
  seed) y un `vite dev` real en el runner, y corre los tests contra la app de verdad:
  login/logout con revocación de sesión, crear cliente + proyecto, flujo completo
  presupuesto→cotización→aprobar (verificando el cálculo de ITBIS 18%)→materiales, y
  gestión de usuarios. La mayoría de los tests reusan una sesión iniciada una sola vez
  (`global-setup.ts`) para no agotar el rate limit de login.
- **Gestión de usuarios** (`/usuarios`, solo `admin`): `GET/POST /api/users`,
  `PUT /api/users/{id}` para crear usuarios oficina/técnico, cambiar rol, activar/
  desactivar y resetear contraseña desde la app — antes solo existía el admin inicial
  vía `python -m app.db.seed`, sin forma de agregar más usuarios sin tocar la base de
  datos directamente. Un admin no puede desactivarse ni quitarse el rol admin a sí
  mismo (evita quedarse sin ningún admin activo). 9 tests nuevos.
- **Endurecimiento de seguridad y manejo de errores del backend:**
  - Rate limiting (`slowapi`) en login (10/min) y refresh (30/min) por IP.
  - Límite de tamaño de subida de archivos (`MAX_UPLOAD_MB`, 25 MB por defecto) en
    fotos/audio de Levantamiento y Bitácora.
  - Manejo global de excepciones: cualquier error no capturado devuelve un 500 genérico
    al cliente y el detalle completo (con traceback) se registra en el log del servidor.
  - Logging centralizado con rotación (`backend/logs/app.log`).
  - Validación de longitud máxima en todos los campos de texto libre de la API
    (alineada con los límites de columna en la base de datos).
  - Advertencia en el arranque si `JWT_SECRET` sigue en su valor por defecto.
  - Rol `tecnico` nuevo: acceso completo a Levantamiento/Ingeniería/Ejecución/Bitácora/
    Tickets, solo lectura de Clientes/Proyectos, sin acceso a Presupuestos/Cotizaciones/
    Compras/Facturación/Catálogo.
  - **Refresh tokens**: login ahora devuelve access token (60 min) + refresh token
    (30 días, revocable server-side vía hash SHA-256 en `refresh_tokens`).
    `POST /api/auth/refresh` renueva el access token; `POST /api/auth/logout` revoca el
    refresh token. El frontend renueva el access token automáticamente ante un 401
    (interceptor de axios) y "Salir" ahora invalida la sesión en el servidor, no solo
    borra el token del navegador.
  - **Columnas de auditoría** (`created_by`, `updated_at`) en las 13 entidades
    principales (Clientes, Proyectos, Levantamientos, Ingeniería, Catálogo,
    Presupuestos, Cotizaciones, Materiales, Bitácora, Prefacturas, Facturas,
    Ampliaciones, Tickets), expuestas en las respuestas de la API.
- **Despliegue en Windows Server** (`deploy/`): backend como servicio de Windows
  (`MultitecBackend`, vía NSSM), Caddy como reverse proxy + HTTPS + servidor de
  estáticos del frontend (`MultitecWeb`), y backups automáticos diarios de PostgreSQL
  vía Tarea Programada. Guía completa en `deploy/README.md`. Probado de punta a punta
  en local: proxy `/api` y `/uploads`, fallback de SPA a `index.html`, y un backup real
  restaurable con `pg_restore --list`.
- **Borrar fotos/notas de voz del Levantamiento** individualmente (nuevo endpoint
  `DELETE /api/projects/{id}/survey/assets/{asset_id}`, botón ✕ en cada foto/audio en
  el frontend). Las notas de texto ya eran editables desde Fase 1.
- **Referencia del levantamiento en la pestaña Factura**: notas, observaciones y fotos
  del levantamiento se muestran como respaldo de lo facturado.
- **Suite de tests automatizados del backend** (pytest, 27 tests): autenticación/roles,
  clientes, proyectos, el flujo presupuesto→cotización→aprobación→materiales (incluyendo
  no-duplicación al re-aprobar), ejecución por etapas, restricción admin-only de
  facturación, y los endpoints de IA con Ollama mockeado. Corre contra SQLite aislado en
  cada push/PR vía GitHub Actions (job `backend` nuevo en `ci.yml`).
- **Búsqueda semántica entre proyectos** en "Preguntar a la IA": opción "Todos los
  proyectos" que compara la pregunta contra el embedding de cada proyecto (Ollama +
  `nomic-embed-text`, guardado en la tabla `project_embeddings`, sin depender de
  pgvector) y responde citando de qué proyecto(s) sacó la información. Los proyectos se
  indexan automáticamente al usar cualquier función de IA sobre ellos.
- Migración a **PostgreSQL** verificada de punta a punta: `psycopg2-binary` agregado a
  `requirements.txt`, las 4 migraciones de Alembic aplican limpio sin cambios, y se
  confirmó login + lectura/escritura contra una base Postgres real.
- CI en GitHub Actions (`lint` + `build` del frontend en cada push/PR).
- Plantilla de Pull Request y plantillas de Issues (bug report, feature request).
- Topics del repositorio en GitHub para descubribilidad.
- `SECURITY.md` con política de reporte de vulnerabilidades y buenas prácticas de despliegue.
- `CODE_OF_CONDUCT.md` (basado en Contributor Covenant v2.1).
- `CODEOWNERS` en `.github/`.
- `CONTRIBUTING.md` con flujo de trabajo y convenciones de código.
- `LICENSE` propietario (todos los derechos reservados, Ferretería Popular SRL).
- Badge de GitHub en el README enlazando al repositorio.

### Corregido

- `assign_ncf` no tenía criterio de desempate cuando dos secuencias NCF activas del mismo
  tipo compartían fecha de vencimiento (p. ej. dos rangos autorizados el mismo día) —
  podía resolverse de forma no determinista y, en el peor caso, generar un NCF ya usado
  por otra secuencia, lo que la restricción `UNIQUE` de la base rechazaba como un 500
  genérico. Ahora se desempata por `id` (la secuencia más antigua gana) y, si aun así hay
  colisión (rangos realmente superpuestos configurados por error), se devuelve un 400 con
  el mensaje explicando qué revisar, en vez de un error genérico. Encontrado al verificar
  manualmente el flujo de conversión con secuencias de prueba duplicadas.
- El botón **"Ver"** de los PDF de Factura abría una pestaña en blanco: `window.open`
  se llamaba después de un `await` (fuera de la pila síncrona del click), así que el
  navegador lo trataba como un popup no solicitado. Se abre la pestaña primero,
  sincrónicamente, y se navega a la URL del PDF una vez que el blob llega.
- La pestaña **Tickets** de un proyecto mostraba el badge de estado general del proyecto
  (p. ej. "Levantamiento") junto al código en el encabezado, aunque los tickets tienen su
  propio estado independiente (abierto/en proceso/cerrado) — daba a entender que el
  ticket estaba "en Levantamiento". Ese badge ahora se oculta específicamente en la
  pestaña Tickets.
- `backend/app/main.py` ya no falla al arrancar si `backend/uploads/` no existe (pasa
  en un clon nuevo, ya que está en `.gitignore`) — ahora se crea automáticamente antes
  de montar `StaticFiles`. Detectado al escribir los tests.
- Numeración duplicada en la sección "Configurar la IA" del README.
- `Project.responsible` y `Ticket.technician` rompían con `AmbiguousForeignKeysError` al
  agregar la columna `created_by` (segunda FK a `users` en la misma tabla) — se
  desambiguó con `foreign_keys=[...]` explícito. Detectado por la suite de tests antes
  de llegar a producción.
- Comparación de fechas del refresh token fallaba con
  `TypeError: can't compare offset-naive and offset-aware datetimes` en SQLite (que
  devuelve datetimes "naive" aunque la columna sea `DateTime(timezone=True)`, a
  diferencia de Postgres) — se normaliza a UTC antes de comparar. El manejo global de
  errores lo atrapó como un 500 limpio en vez de tumbar el proceso; el test de
  integración lo expuso de inmediato.
- **`alembic upgrade head` estaba roto en SQLite desde las migraciones de refresh
  tokens/auditoría** — dos bugs reales que habrían bloqueado a cualquiera siguiendo el
  setup de desarrollo documentado (SQLite es el default en `.env.example`):
  - `server_default=sa.text('now()')` es sintaxis específica de Postgres; en SQLite
    `now()` no existe. Cambiado a `CURRENT_TIMESTAMP` (estándar SQL, funciona en ambos).
  - `op.create_foreign_key` después de `op.add_column` no funciona en SQLite fuera de
    "batch mode" (`NotImplementedError: No support for ALTER of constraints`). Envuelto
    en `op.batch_alter_table(..., recreate='always')`. Encontrado al armar el job de CI
    de E2E, que corre las migraciones contra SQLite fresco — nadie lo había hecho desde
    que estas migraciones se generaron trabajando directo contra Postgres.
- El job `E2E (Playwright)` fallaba en su primera corrida real en GitHub Actions: el
  chequeo de salud del workflow le hacía `curl` a `http://127.0.0.1:5173`, pero Vite (sin
  `--host`) escucha en `localhost`, que en el runner de Ubuntu resuelve primero a `::1`
  (IPv6) — el `curl` a la IPv4 explícita nunca conectaba aunque Vite ya estuviera arriba.
  Cambiado a `http://localhost:5173`, igual que ya usaba `playwright.config.ts`.

## [2026-07-02] — Lanzamiento inicial: fases 1-5 + IA local

Primer commit del proyecto, con las 5 fases del brief original completas.

### Añadido

- **Fase 1 (fundación):** autenticación con roles (`admin` / `oficina`), módulo de
  Clientes, núcleo de Proyecto con pestañas (Información / Levantamiento / Ingeniería) y
  Catálogo con generación automática de códigos.
- **Fase 2 (comercial):** pestañas Presupuesto y Cotización con ITBIS 18%, estados
  pendiente/aprobada/no aprobada/archivada, auto-archivo tras 7 días sin decisión, y
  conversión de presupuesto a cotización.
- **Fase 3 (operación):** generación automática de lista de materiales al aprobar una
  cotización, pestaña Compras con "lista inteligente" de pendientes, pestaña Ejecución
  con 5 etapas secuenciales y % de avance, pestaña Bitácora con entradas cronológicas y
  fotos.
- **Fase 4 (administrativa):** pestaña Prefactura generada desde una cotización
  aprobada, pestaña Factura de solo lectura (conversión restringida a rol `admin`),
  pestaña Ampliaciones, pestaña Tickets de soporte.
- **Fase 5 (IA):** organizar levantamiento con IA (resumen de notas + análisis de fotos),
  dictado por voz vía Web Speech API del navegador, generación de propuesta técnica de
  ingeniería, sugerencia de materiales para presupuesto, y pantalla global "Preguntar a
  la IA" sobre el expediente de un proyecto.
- **Fase 5b:** motor de IA migrado de la API de Claude a **Ollama local y gratuito**
  (`llama3.2` para texto, `llava` para fotos) — corre en la propia PC sin costo por uso
  ni API key. Incluye reintento automático y degradación a resumen de solo texto cuando
  el modelo de visión local no logra analizar una foto adjunta.
- Backend FastAPI + SQLAlchemy + Alembic sobre SQLite (con soporte para migrar a
  PostgreSQL vía `DATABASE_URL`).
- Frontend React + Vite + TypeScript + Tailwind CSS v4, PWA instalable, mobile-first.
