# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [Sin publicar]

### Añadido

- **Marcar equipos en fotos del teléfono**: las posiciones de los puntos se medían contra el recuadro y no contra la foto, así que
  en fotos verticales (las normales del teléfono) salían corridas en el anexo de la cotización. Ahora se miden sobre la foto, un
  toque en el margen no crea un punto, la hoja del teléfono ya no se mueve al añadir el primer punto y se avisa mientras la foto carga.
- **Videos de la Ayuda en pantalla completa**: botón propio «Pantalla completa» que usa la del navegador y, si no se puede (marco sin
  permiso, algunos navegadores del iPhone), ocupa toda la pantalla desde la propia página.
- **Ayuda con videos** (`/ayuda`, todos los roles): guía completa de 4 minutos, paso a paso con un video corto por tema y sus
  pasos en texto, y preguntas frecuentes, filtradas por rol. «Aprende a usar el sistema» en la pantalla de entrada. Videos MP4
  (H.264) con portada en `frontend/public/videos/`; los scripts para regrabarlos están en `frontend/scripts/videos/`.
- **Periodo de prueba, tope de usuarios y empresas demo** (migración `e1b5c8d2f4a6`): cada empresa puede tener fecha
  de vencimiento (al vencer funciona como suspendida hasta que la plataforma la extiende) y un máximo de usuarios
  activos. El panel crea una **empresa demo** con administrador, técnicos de prueba con clave temporal y
  clientes/proyectos de ejemplo repartidos entre ellos.
- **Cotización con IA más exacta**: cada punto marcado en las fotos lleva un tipo (cámara, NVR, switch...) y la IA recibe
  los conteos como dato fijo; si la cotización trae menos de lo marcado, la corrige (una sola línea) o avisa
  (migración `f2c6d9e3a5b7`).
- **Actualizar precios** de una cotización con los del catálogo, viendo antes qué cambia. Una pendiente se actualiza en su
  lugar; una aprobada o rechazada genera una versión nueva y la original queda intacta. «Crear nueva versión para editar».
- **Comparar otra cotización** (PDF con texto, foto o texto pegado) con el levantamiento y con la cotización propia: la IA
  solo lee el documento (se puede corregir) y la comparación es por reglas fijas (migración `a4e8f1b6c2d9`, `pypdf`).
- **Claves de las cuentas nuevas** (empresa o demo): editar la clave, descargar el archivo con los accesos y enviar el enlace
  por WhatsApp o correo.
- **Mapa y «Cómo llegar»**: las direcciones sin coordenadas se ubican con OpenStreetMap (el mapa gratuito de Google ya no
  existe) y «Cómo llegar» ofrece Google Maps, Waze y Apple Maps.
- **Pantalla de recuperación** si la app falla al abrir (en vez de una pantalla negra) y recarga automática una vez cuando el
  teléfono guardó una versión vieja; `PWA_RESET=1 npm run build` genera la limpieza forzada del service worker.
- **Multi-empresa**: una sola instalación y base de datos para varias empresas, con los datos separados por
  `company_id` (migración `d9a4b7c2e1f3`). El aislamiento es automático (`TenantSession`): filtra toda
  consulta, sella lo que se crea, rechaza datos de otra empresa y falla cerrado si la sesión no tiene empresa.
  Correlativos, NCF, logo, archivos (`uploads/c{id}/`) y RNC de la DGII son por empresa.
- **Panel de plataforma** (`/plataforma`, solo el dueño del sistema): crear una empresa con su administrador
  (clave temporal de un solo uso), ver su uso, suspender / reactivar (cierra sus sesiones) y restablecer la clave
  de su administrador. Todo queda en la auditoría.
- **Generación de cotizaciones con IA en el servidor**: sigue aunque salgas de la app y se retoma al volver; una
  línea con dato inválido de la IA se omite con aviso en vez de tumbar toda la cotización.
- **Administración del equipo**: ficha (teléfono, zona, especialidades, vehículo), último acceso, restablecer
  clave temporal, sesiones activas con cierre remoto, carga de trabajo por técnico y **bitácora de auditoría**
  (migración `b7d2e9a4c1f6`).
- **Visitas**: entrada y salida con GPS opcional, duración estimada, **hoja de tiempo** con CSV y avisos por
  WhatsApp al cliente. Una visita no se puede asignar a un usuario desactivado.
- **Equipos instalados por cliente** (serial, MAC, IP, ubicación, garantía) (migración `c8e3f5a1d7b9`).
- **El técnico solo ve lo suyo** (proyectos y clientes propios, asignados o con visita/ticket).
- **Iconos** de línea (lucide-react) en navegación, inicio y cabecera; menú lateral de escritorio que se
  encoge a iconos; Inicio y detalle de proyecto en dos columnas en pantalla ancha.
- **iPhone**: `dvh`, campos de al menos 16 px, zona segura superior, `navigator.storage.persist()`, reenvío de
  pendientes al volver a la app, nota de voz con el formato real (`.m4a` en iPhone) y error visible si falta el permiso.
- Guía para publicar con **dominio propio** y HTTPS (`deploy/DOMINIO.md`).

### Seguridad

- PyJWT en lugar de python-jose; refresh token en cookie HttpOnly; bloqueo por cuenta; política de
  contraseñas; límite y cuota de la IA; validación de archivos por contenido; neutralización de fórmulas en
  CSV; cabeceras en la API y CSP en la web; `psycopg` 3; `pip-audit` y `npm audit` en 0.
- Un técnico ya no recibe el token del portal del cliente (abría cotizaciones y facturas).
- **Aislamiento entre empresas (revisión)**: una empresa podía crear presupuestos, cotizaciones y prefacturas colgados del
  proyecto de OTRA empresa (con un aviso por correo que mostraba el cliente ajeno) y un administrador de otra empresa podía
  cerrar sesiones ajenas conociendo los ids. Ahora la sesión rechaza guardar cualquier fila que apunte a un registro de otra
  empresa (responde «No encontrado») y la ruta de sesiones comprueba la empresa. La prueba de aislamiento recorría solo 2
  rutas por cómo FastAPI anida los routers; ahora recorre las 203 operaciones del esquema OpenAPI.

### Añadido (anterior)

- **Conversación hablada con el asistente** en el Inicio ("Hablar con el asistente"): saluda en voz
  alta por el nombre del técnico, pregunta "¿Qué toca hoy?", escucha la respuesta y lo lleva a donde
  corresponde: un levantamiento nuevo (con cliente, tipo y teléfono ya entendidos; reconoce si el
  cliente ya existe), continuar un proyecto, la agenda del día, cotizaciones o tickets
  (`POST /api/assistant/talk` para texto, `POST /api/assistant/listen` para audio).
  - Entender la frase: reglas primero (instantáneo); la IA local solo si las reglas no reconocen
    la frase (~5-7 s en esta máquina) y, si falla, se pide repetir con ejemplos: nunca inventa una acción.
  - Escuchar: el teléfono solo graba (`useVoiceTurn`, con corte automático al notar la pausa) y el
    servidor transcribe con Whisper local (~2 s por frase). El dictado del navegador fallaba seguido en
    iPhone. Hablar: síntesis del teléfono (`useSpeaker`), con los cuidados que pide Safari.
  - El asistente del Inicio pregunta "¿Cómo quieres que te llame?" la primera vez y ofrece
    "¿Cómo quieres trabajar hoy?": hablar, dictar un levantamiento, escribirlo paso a paso o continuar
    uno de los últimos proyectos. `/nuevo` acepta `?cliente=`, `?nombre=`, `?tipo=`, `?telefono=` y `?modo=voz`.
- **La web se sirve compilada** (`vite preview` desde `deploy/multitec.ps1`, que compila antes de
  arrancar): unos 40 archivos en vez de los cientos del modo desarrollo, mucho más rápida por el túnel,
  y con el service worker de la PWA activo (el modo sin conexión funciona de verdad en el teléfono).
- **Túnel a pedido**: `abrir-tunel-multitec.bat` / `cerrar-tunel-multitec.bat` (ngrok). No se abre con
  `iniciar-multitec.bat`: publicar la app en internet es una decisión de cada vez.
- **Permiso de ubicación denegado**: la app explica dónde se activa en iPhone y Android en vez de un
  aviso corto, y deja seguir escribiendo la dirección.
- **Estado del sistema visible** (`GET /api/system/status`, `SystemStatus` en el encabezado): un punto
  verde/ámbar/rojo que al tocarlo dice si el servidor, la base de datos, la IA de texto (apagada, sin
  modelo, fría o lista) y la voz están listos, y avisa cuando no hay conexión. Así el técnico sabe por qué
  algo tarda en vez de adivinar.
- **Arranque y parada sin procesos huérfanos** (`deploy/multitec.ps1`, `iniciar-multitec.bat`,
  `detener-multitec.bat`, `estado-multitec.bat`): se detiene por PUERTO con todo su árbol y se arranca
  sin `--reload`, en segundo plano y con logs en `backend/logs`. Resuelve que un proceso hijo huérfano
  siguiera sirviendo código viejo en el 8000 mientras el servidor "nuevo" no llegaba a escuchar. Tras
  cambiar código hay que reiniciar (`iniciar-multitec.bat`).
- **Asistente del día** en el Inicio (`GET /api/assistant/today`, `TodayAssistant`): saluda por el nombre
  que el usuario configuró ("Buenos días, Ing. Pérez"), resume lo que hay para hoy y pregunta "¿Qué
  desarrollamos juntos hoy?" con un toque por pendiente: visitas de hoy (con "Cómo llegar"),
  levantamientos con notas listos para cotizar, cotizaciones esperando respuesta y tickets abiertos.
  El técnico ve lo suyo (responsable o quien lo creó); admin y oficina ven todo. A propósito no usa
  el modelo de IA: aparece al instante y funciona aunque Ollama no esté cargado.
- **Unidades por paquete** (`products.pack_size`, migración `d4a8b3c6e2f5`): un producto que se vende
  en bolsa/caja de varias piezas (ej. conectores RJ45, bolsa de 100) pasa lo que el técnico dijo
  en unidades sueltas a paquetes enteros: "16 conectores RJ45" → 1 bolsa. Si el técnico ya habló
  en paquetes ("2 bolsas") se respeta, y cada conversión sale como aviso. Disponible en el formulario
  del catálogo y en la importación CSV ("Unidades por paquete"). Las cantidades que generan las
  reglas de accesorios no se convierten: las define quien escribe la regla.
- **Reporte 608 y anulación de facturas**: el admin anula una factura con un tipo de anulación
  de la DGII (migración `a1d5c8e2f9b7`); sale del 607, del dashboard y del margen y entra al 608.
  Los reportes 606/607/608 se descargan como CSV (revisar) o como `.txt` de envío
  (`DGII_F_<formato>_<RNC>_<AAAAMM>.TXT`, requiere `COMPANY_RNC`).
- **606: tipo de retención de ISR** (migración `c3f7a2b8d4e1`), obligatorio con retención de renta,
  y fecha de pago obligatoria con ITBIS/renta retenidos, según el instructivo.
- **Marcadores numerados sobre las fotos del levantamiento** (migración `b2e6f1a7c3d9`) y anexo
  fotográfico en el PDF de la cotización (`?photos=marked|all`).
- **Portal del cliente**: PDF de la cotización, rechazo con motivo, nombre de quien aprueba o
  rechaza (historial + aviso a admins), y sin facturas anuladas.
- **Envío por WhatsApp** del enlace del portal desde la cotización.
- **Levantamiento sin conexión**: cola en IndexedDB que se envía sola al volver la señal.

### Corregido

- **607**: la retención de renta iba en la columna 13 (ISR percibido) y va en la 12; nombres de
  las columnas 10 a 14 alineados al instructivo; las facturas de consumo (B02) menores de
  RD$250,000 ya no se detallan (van al resumen de la Oficina Virtual); el tipo de identificación
  "3" ya no se asigna a quien no tiene documento (es pasaporte / ID tributaria).

- **La IA ya puede trabajar con un catálogo grande** (probado con 54 productos): antes el prompt
  llevaba el catálogo completo, no cabía en el contexto del modelo (4096 tokens), se truncaba y la
  generación se desbocaba (>20 min con la CPU al 100%). Ahora (`catalog_matching.py`): (1) se empareja
  primero por texto con puntaje (sinónimos > nombre > etiquetas > categoría, y los NÚMEROS cuentan:
  "16 puertos" suma, "8 puertos" resta), (2) a la IA solo van las entidades realmente ambiguas, con
  un máximo de 40 candidatos y una respuesta compacta (`product_ids`), (3) lo que no se parece a nada
  queda sin producto en vez de dejar que la IA invente uno, y (4) si la IA falla la cotización sigue
  con lo resuelto por texto. Catálogos de 25 productos o menos conservan el comportamiento anterior.
  Todas las llamadas a Ollama tienen un tope de 2048 tokens de salida (`MAX_RESPONSE_TOKENS`).
- **Menos basura al interpretar el levantamiento** (`nlu.py`): las medidas del sitio ("40 metros",
  "Altura de instalación 3.5 m") ya no se toman como materiales —inflaban cálculos: 40 cámaras
  fantasma pedían 26 discos— pero "200 metros de cable UTP" sí se conserva; la interpretación usa
  temperatura 0 (mismo levantamiento, misma lista) y conserva canales/puertos/megapíxeles. Un error
  de respuesta incompleta ya no se reporta como "Ollama no está corriendo".
  Medido con un dictado de 16 cámaras: de >3 min (y con error) a 23 s, con NVR de 32 canales, switch
  de 16 puertos y 8 discos en vez de 26.
- **Correo por Gmail, con activación segura** (`backend/scripts/setup_smtp.py`): pide la contraseña
  de aplicación de Google sin mostrarla, envía un correo de PRUEBA y solo si llega escribe
  `SMTP_HOST` y `SMTP_PASSWORD` en `backend/.env` (si falla no cambia nada, así la app nunca queda
  esperando a un SMTP que no responde). Nuevo `NOTIFICATION_EMAIL`: las alertas de admin (cotización
  pendiente, aprobación del cliente, portal, cotización vencida) llegan a ese buzón real en vez de al
  correo de inicio de sesión de cada admin (p. ej. `admin@multitec.com`, que no existe como buzón).
  Las pruebas ya no leen el `.env` real (SMTP y destinatario vacíos en `conftest.py`).
- **Doble clic para dejar PostgreSQL como servicio** (`deploy/activar-servicio-postgres.bat`):
  pide permiso de administrador y ejecuta `enable-postgres-service.ps1`.
- **Cotización con IA en la mitad del tiempo:** el borrador de ingeniería era el 54% de la espera
  (~42 s) y la cotización no lo necesita. `POST /api/projects/{id}/generate-from-survey?background_engineering=true`
  entrega la cotización de inmediato (`engineering_pending: true`) y redacta la ingeniería en un hilo
  aparte, que solo escribe si la ingeniería sigue vacía al terminar (no pisa lo que alguien editó).
  El levantamiento rápido del celular usa este modo; el comportamiento por defecto no cambia. Medido
  con Ollama real: cotización a los 47 s en vez de 101 s, ingeniería lista a los ~104 s.
- **IA local más ágil (modelo precalentado y en memoria):** Ollama descargaba el modelo a los 5
  minutos de inactividad y el siguiente uso pagaba un arranque en frío. Ahora el cliente de IA
  (`get_client`) inyecta `keep_alive` (configurable con `AI_KEEP_ALIVE`, por defecto 30 min) en
  todas las llamadas, y `POST /api/ai/warmup` precarga en segundo plano el modelo de texto y el de
  voz; el levantamiento rápido lo pide al abrirse. Medido con Ollama real: la primera frase tras
  inactividad pasó de 12.6 s a 6.6 s; con el modelo ya cargado se mantiene en ~5 s. El
  precalentamiento nunca falla ni bloquea (si Ollama no está, no hace nada) y no se repite más
  seguido que cada 2 minutos.
- **Cambio obligatorio de la contraseña temporal** (`users.must_change_password`, migración
  `f7a3c1e9b2d4`): un usuario creado por un admin, o cuya contraseña restableció otro admin, queda
  marcado y **el servidor** (`get_current_user`) bloquea con 403 todo salvo `/api/auth/me`,
  `/api/auth/change-password` y `/api/auth/logout` hasta que la cambie; la app lo lleva a `/perfil`
  con un aviso. Un admin que se pone su propia contraseña no queda marcado. Los usuarios existentes
  no se tocan.
- **Importación masiva de productos al catálogo** (Catálogo → "⬆ Importar", solo admin): carga una
  lista de precios desde un CSV (el que guarda Excel) en vez de crear producto por producto.
  Plantilla descargable (`GET /api/catalog/import-template`, con `sep=;` para que Excel separe las
  columnas) y vista previa obligatoria antes de aplicar (`POST /api/catalog/import?dry_run=true|false`).
  Reconoce productos existentes por `codigo` o por nombre (sin importar tildes ni mayúsculas) y los
  actualiza; una celda vacía **nunca** borra un dato ya guardado; la categoría se busca por nombre o
  por ruta ("CCTV > Cámaras IP") y si el nombre se repite en varias ramas pide la ruta; las filas con
  error se informan una por una sin frenar al resto; acepta números como `1,250.50`, `1.250,50` o
  `RD$ 3,500`. Las filas que empiezan con "EJEMPLO" se ignoran. Motivo: el catálogo real tenía solo 8
  productos y la IA no podía cotizar casi nada de lo que se dicta.
- **Redondeo de cajas y rollos en el margen de cable:** el margen de desperdicio ya no produce "2.1
  cajas"; las unidades indivisibles (caja, rollo, unidad…) se redondean hacia arriba y los metros
  conservan dos decimales.
- **Forma de pago y retenciones en las facturas, y reporte 607 completo**: nuevos campos de
  `invoices` (`payment_method`, `itbis_withheld`, `isr_withheld`, `retention_date`, migración
  `e4c7a9b2d5f1`; las facturas existentes quedan sin registrar) y `PUT /api/invoices/{id}/payment`
  (admin y oficina; valida que no se retenga más ITBIS que el de la factura ni más renta que el
  subtotal, y exige fecha cuando hay retención). Se registran desde el bloque "Cobro y
  retenciones" de la factura (`InvoicePaymentForm`). El 607 pone el total cobrado en la columna
  de la forma de pago y las retenciones con su fecha en las suyas; antes esas columnas salían
  siempre vacías.
- **Respaldo diario de la base sin administrador** (`deploy/register-backup-task-user.ps1`):
  registra una tarea programada con el usuario de Windows (02:00, o apenas haya sesión si la PC
  estaba apagada) que corre `backup-postgres.ps1`. `backup-postgres.ps1` acepta ahora
  `-EnvFile backend\.env` y toma usuario, base y contraseña de `DATABASE_URL`, así la contraseña
  no queda escrita en la definición de la tarea; borra el dump si `pg_dump` falla. Los respaldos
  van fuera del repositorio (`%USERPROFILE%\MultitecBackups`, 14 días de retención).
- **Levantamiento rápido sin scroll y sin esperas en el celular** (`/nuevo`):
  - **Una cosa por pantalla:** primero el cliente (saludo corto, buscador y dos botones grandes);
    con el cliente elegido, el tipo de levantamiento y "Comenzar". La ubicación va plegada en un
    renglón ("📍 Ubicación capturada · Ver mapa ▾") y solo despliega el mapa y los campos al
    pedirlo (`LocationBar`). Ambas pantallas caben sin scroll en un celular.
  - **La IA ya no bloquea:** el dictado se procesa en segundo plano (`VoiceRecorderCard` en modo
    grande). Mientras tanto se puede tomar fotos o grabar otra nota; se muestra un cronómetro y la
    etapa ("Escuchando…", "La IA ordena notas, medidas y observaciones…") y, al terminar, aparece
    "✅ Tu dictado está listo" (con vibración donde se pueda) para revisarlo al tocar. Los dictados
    listos se encolan.
  - **Mejor dictado de términos técnicos:** `DOMAIN_PROMPT` de Whisper ampliado con marcas y
    equipos (Hikvision, Dahua, patch panel, megapíxeles, gabinete 12U, UPS…). Con una grabación
    real, "metodopiceles / Marqueehibition / Pashpanen" pasaron a "megapíxeles / Hikvision / patch
    panel", sin costo de velocidad.
- **Asistente de IA que saluda por su nombre** (`/nuevo`): al abrir el levantamiento rápido
  aparece solo, dice "Hola, Ing. X. Soy tu asistente de levantamientos", explica en qué puede
  ayudar y ofrece "Cliente nuevo", "Decir todo de una vez" y "Buscar un cliente". Cada usuario
  configura cómo lo llama en `/perfil` ("Cómo te llama el asistente de IA", p. ej. "Ing. Pérez";
  vacío = "Ing." + primer nombre) — `users.assistant_alias`, migración `d9b3f6a1c4e8`,
  `PUT /api/auth/me` acepta `assistant_alias` (si no viene no se toca; vacío lo borra).
- **El mapa carga siempre:** con coordenadas la vista previa usa OpenStreetMap (sin clave); el
  mapa de Google se quedaba en blanco en varios iPhone. Con solo una dirección sigue usando el de
  Google, y tocar el mapa abre Google Maps.
- **Levantamiento rápido más ágil** (`/nuevo`, y `/proyectos`):
  - **Ubicación automática:** al abrir el levantamiento rápido se pide el GPS solo (una vez) y
    se guarda en el proyecto; el mapa muestra "Cómo llegar" al punto. En la ficha de un
    proyecto sin ubicación, "Agregar" también la pide al tocarlo (nunca al abrir la ficha,
    para que mirar un proyecto desde la oficina no sobrescriba la ubicación de la obra).
  - **Menú de búsqueda de clientes** (`ClientCombobox`): filtra al escribir por nombre,
    empresa, teléfono o RNC, sin importar tildes, y ofrece "＋ Crear cliente nuevo" en el
    momento. Reemplaza al `<select>` del formulario de proyectos.
  - **Asistente de alta de cliente** (`IntakeAssistant`): pregunta nombre → teléfono → tipo de
    levantamiento, se contesta escribiendo, dictando o tocando una opción, o se dice todo de una
    vez ("Juan Pérez, 809 555 1234, cámaras") y la IA local lo separa
    (`POST /api/ai/intake-parse`; teléfono y tipo se detectan con reglas, la IA ayuda con
    nombre/empresa y, si Ollama no responde, el resultado sale igual solo de las reglas).
  - **Tipo de levantamiento** (`projects.survey_type`, migración `c5a2e8d4f1b6`): se guarda en
    el proyecto, se muestra en la lista y alimenta la descripción ("Levantamiento · Alarma").
    La lista de tipos vive en `frontend/src/lib/surveyTypes.ts`.
- **Módulo de Compras y reporte 606** (`/compras`, admin+oficina): registro de facturas de
  proveedores con NCF, tipo de gasto, forma de pago, ITBIS y retenciones
  (`/api/purchase-invoices`, tabla `purchase_invoices`, migración `b7e4d1c9a2f3`) y export
  CSV del formato 606 (`GET /api/reports/dgii-606?year=&month=`). Rechaza NCF duplicado por
  proveedor. Columnas no verificadas contra la plantilla oficial de la DGII.
- **Proveedores y compras reales** (`/proveedores`, admin+oficina, sin acceso `tecnico`
  igual que Catálogo/Compras): maestro simple de proveedores (nombre, RNC, teléfono,
  correo, dirección, notas — calco de Clientes). Cada `Material` marcado **"Comprado"** en
  la pestaña Compras de un proyecto puede ahora registrar **a quién se le compró y a qué
  precio real** (`GET/PUT /api/suppliers`, `PUT /api/materials/{id}/status` extendido con
  `supplier_id`/`purchase_price` opcionales) — antes solo existía un estado interno sin
  ningún dato de a quién ni a cuánto. Cada proveedor tiene un **historial de compras**
  expandible (`GET /api/suppliers/{id}/materials`) con el proyecto, producto, cantidad y
  precio de cada compra, cruzando todos los proyectos donde se le ha comprado. Deliberadamente
  **no** alimenta el cálculo de rentabilidad/margen ya existente (que sigue usando el costo
  estimado de catálogo, no el precio real pagado) ni la bodega general
  (`StockMovement`/entradas-salidas) — quedan como posibles extensiones futuras. 6 tests
  nuevos.
- **Rentabilidad / margen por proyecto** (`GET /quotes/{id}/margin`, `/invoices/{id}/margin`,
  `/projects/{id}/margin`, `/reports/margin` — todos **admin-only**): el sistema ya
  guardaba el costo de adquisición de cada producto (`Product.cost`) pero nada lo usaba;
  ahora se calcula el margen (venta − costo, %) en vivo cruzando cada línea de
  cotización/factura contra el costo actual del catálogo, sin snapshot histórico por
  línea. Se muestra en la caja de totales de Cotización y Factura, en un resumen nuevo por
  proyecto (prioriza lo facturado; si aún no hay factura, proyecta sobre la cotización
  aprobada) y como KPI en el Dashboard (agregado de los últimos 6 meses). Una línea sin
  producto de catálogo (mano de obra, texto libre) o con costo sin cargar cuenta como
  venta pero no como costo — se avisa en la UI cuando el margen es parcial. Gateado a
  `admin` únicamente (no `oficina`, no `tecnico`) porque revela el poder de compra de la
  empresa; nunca aparece en los PDFs de cotización/factura ni en el portal de cliente. 8
  tests nuevos.
- **Portal de cliente** (`/portal/{token}`, sin login): enlace de solo lectura para que
  un cliente vea el estado de su proyecto, sus cotizaciones (con líneas y totales) y sus
  facturas (con NCF y PDF descargable). Se activa por proyecto desde la pestaña
  Información (solo admin/oficina) — "Generar enlace" crea un token opaco de 256 bits
  (`secrets.token_urlsafe(32)`, no el id numérico del proyecto, que sería trivial de
  adivinar/enumerar), "Regenerar" invalida el anterior, "Desactivar" apaga el portal sin
  borrar el proyecto. Los endpoints públicos (`/api/public/projects/{token}` y su PDF de
  factura) tienen rate limiting (30/min) igual que login, y el endpoint del PDF valida
  que la factura pedida pertenezca al proyecto del token, no solo que exista. 9 tests
  nuevos.
- **Fotos de evidencia en Tickets**: cada ticket ahora puede llevar fotos adjuntas (p.
  ej. antes/después de una reparación), igual que Levantamiento y Bitácora ya podían —
  era el único módulo con soporte de fotos que le faltaba. Subir (`POST
  /api/tickets/{id}/photos`) y borrar (`DELETE /api/tickets/{id}/photos/{asset_id}`)
  individualmente, mismos roles que el resto de Tickets. 6 tests nuevos.
- **Calendario de visitas técnicas** (`/calendario`, los tres roles): agenda simple por
  día — navegación con flechas o selector de fecha, agendar una visita a un proyecto con
  técnico y hora opcionales, y marcar completada/cancelada. `GET /api/visits?start=&end=`
  para listar por rango de fechas, `POST/PUT /api/visits` para agendar/actualizar. Mismo
  esquema de permisos que Tickets — un técnico también puede agendar y actualizar sus
  propias visitas. 7 tests nuevos.
- **Reporte 607 (Ventas) para la DGII**, en `/ncf` (solo admin/oficina): exporta las
  facturas de un mes en las columnas del formato 607 (RNC/cédula del comprador, tipo de
  identificación inferido del RNC, NCF, tipo de ingreso, fecha, monto facturado, ITBIS).
  **Alcance deliberadamente limitado**: no se generó el formato 606 (Compras) porque el
  sistema no lleva registro de facturas de proveedores con su propio NCF/RNC — haría
  falta un módulo de compras que no existe hoy. Tampoco se trackea forma de pago
  (efectivo/tarjeta/crédito) ni retenciones, así que esas columnas del 607 quedan vacías
  para completar a mano si aplican. La estructura de columnas es la mejor aproximación
  disponible a partir de fuentes públicas de la DGII, no se pudo verificar byte a byte
  contra la plantilla oficial vigente — **hay que confirmarla contra dgii.gov.do antes de
  remitir el archivo**, algo que se advierte explícitamente en la propia pantalla.
  5 tests nuevos.
- **Notificaciones dentro de la app**: campanita 🔔 en el encabezado (visible en toda la
  app) con las mismas dos alertas que ya iban por correo — cotización pendiente de
  aprobar (a los admins) y ticket asignado (al técnico) — ahora también como
  notificación en vivo, con contador de no leídas (`GET /api/notifications/unread-count`,
  refresco cada 30s), lista desplegable (`GET /api/notifications`), marcar como
  leída/marcar todas, y clic para ir directo a la pestaña relevante del proyecto. La
  notificación de factura emitida sigue siendo solo por correo, ya que va al cliente
  (que no tiene cuenta en el sistema). 5 tests nuevos.
- **Exportar a CSV** (admin/oficina): botón "Exportar CSV" en Clientes y Proyectos, y
  "Exportar resumen"/"Exportar facturas" en el Dashboard — descargan `text/csv` con BOM
  UTF-8 (para que Excel en Windows muestre bien tildes y la ñ). El resumen del dashboard
  exporta cada sección (cotizaciones pendientes, tickets abiertos, proyectos por estado,
  facturación mensual, tickets por técnico) como filas `Sección,Etiqueta,Valor`.
  6 tests nuevos.
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
- **Multi-empresa**: una sola instalación y base de datos para varias empresas, con los datos separados por
- **Marcar equipos en fotos del teléfono**: las posiciones de los puntos se medían contra el recuadro y no contra la foto, así que
  en fotos verticales (las normales del teléfono) salían corridas en el anexo de la cotización. Ahora se miden sobre la foto, un
  toque en el margen no crea un punto, la hoja del teléfono ya no se mueve al añadir el primer punto y se avisa mientras la foto carga.
- **Videos de la Ayuda en pantalla completa**: botón propio «Pantalla completa» que usa la del navegador y, si no se puede (marco sin
  permiso, algunos navegadores del iPhone), ocupa toda la pantalla desde la propia página.
- **Ayuda con videos** (`/ayuda`, todos los roles): guía completa de 4 minutos, paso a paso con un video corto por tema y sus
  pasos en texto, y preguntas frecuentes, filtradas por rol. «Aprende a usar el sistema» en la pantalla de entrada. Videos MP4
  (H.264) con portada en `frontend/public/videos/`; los scripts para regrabarlos están en `frontend/scripts/videos/`.
- **Periodo de prueba, tope de usuarios y empresas demo** (migración `e1b5c8d2f4a6`): cada empresa puede tener fecha
  de vencimiento (al vencer funciona como suspendida hasta que la plataforma la extiende) y un máximo de usuarios
  activos. El panel crea una **empresa demo** con administrador, técnicos de prueba con clave temporal y
  clientes/proyectos de ejemplo repartidos entre ellos.
- **Cotización con IA más exacta**: cada punto marcado en las fotos lleva un tipo (cámara, NVR, switch...) y la IA recibe
  los conteos como dato fijo; si la cotización trae menos de lo marcado, la corrige (una sola línea) o avisa
  (migración `f2c6d9e3a5b7`).
- **Actualizar precios** de una cotización con los del catálogo, viendo antes qué cambia. Una pendiente se actualiza en su
  lugar; una aprobada o rechazada genera una versión nueva y la original queda intacta. «Crear nueva versión para editar».
- **Comparar otra cotización** (PDF con texto, foto o texto pegado) con el levantamiento y con la cotización propia: la IA
  solo lee el documento (se puede corregir) y la comparación es por reglas fijas (migración `a4e8f1b6c2d9`, `pypdf`).
- **Claves de las cuentas nuevas** (empresa o demo): editar la clave, descargar el archivo con los accesos y enviar el enlace
  por WhatsApp o correo.
- **Mapa y «Cómo llegar»**: las direcciones sin coordenadas se ubican con OpenStreetMap (el mapa gratuito de Google ya no
  existe) y «Cómo llegar» ofrece Google Maps, Waze y Apple Maps.
- **Pantalla de recuperación** si la app falla al abrir (en vez de una pantalla negra) y recarga automática una vez cuando el
  teléfono guardó una versión vieja; `PWA_RESET=1 npm run build` genera la limpieza forzada del service worker.
  `company_id` (migración `d9a4b7c2e1f3`). El aislamiento es automático (`TenantSession`): filtra toda
  consulta, sella lo que se crea, rechaza datos de otra empresa y falla cerrado si la sesión no tiene empresa.
  Correlativos, NCF, logo, archivos (`uploads/c{id}/`) y RNC de la DGII son por empresa.
- **Panel de plataforma** (`/plataforma`, solo el dueño del sistema): crear una empresa con su administrador
  (clave temporal de un solo uso), ver su uso, suspender / reactivar (cierra sus sesiones) y restablecer la clave
  de su administrador. Todo queda en la auditoría.
- **Generación de cotizaciones con IA en el servidor**: sigue aunque salgas de la app y se retoma al volver; una
  línea con dato inválido de la IA se omite con aviso en vez de tumbar toda la cotización.

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
