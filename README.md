# Multitec ERP

[![GitHub repo](https://img.shields.io/badge/GitHub-Adaury%2Fmultitec-blue?logo=github)](https://github.com/Adaury/multitec)
[![CI](https://github.com/Adaury/multitec/actions/workflows/ci.yml/badge.svg)](https://github.com/Adaury/multitec/actions/workflows/ci.yml)
[![Stars](https://img.shields.io/github/stars/Adaury/multitec?style=flat)](https://github.com/Adaury/multitec/stargazers)
[![Forks](https://img.shields.io/github/forks/Adaury/multitec?style=flat)](https://github.com/Adaury/multitec/forks)

**Repositorio:** https://github.com/Adaury/multitec

ERP especializado en seguridad electrónica (CCTV, redes LAN, fibra óptica, control de
acceso, videoporteros, barreras vehiculares, automatización y soporte técnico). El
**proyecto** es el núcleo del sistema: cliente, levantamiento, ingeniería, presupuesto,
cotización, compras, ejecución, bitácora, facturación, ampliaciones y soporte cuelgan
siempre de un proyecto.

Construidas hasta ahora:

- **Fase 1 (fundación):** autenticación con roles, Clientes, núcleo Proyecto con pestañas
  (Información / Levantamiento / Ingeniería) y Catálogo con código automático.
- **Fase 2 (comercial):** pestañas **Presupuesto** (resumen, solo total, líneas de catálogo
  o texto libre) y **Cotización** (detalle con ITBIS 18%, estados pendiente/aprobada/no
  aprobada/archivada, auto-archivo tras 7 días sin decisión, historial), con conversión de
  presupuesto → cotización y pantallas globales `/presupuestos` y `/cotizaciones`.
- **Fase 3 (operación):** al **aprobar una cotización** se genera automáticamente la lista
  de **materiales** (§18 inventario simple: disponible/pendiente de compra/comprado/
  instalado) — pestaña **Compras** con la "lista inteligente" de pendientes. Pestaña
  **Ejecución** con 5 etapas secuenciales (Inicio→Instalación→Configuración→Pruebas→
  Entrega) y % de avance. Pestaña **Bitácora** con entradas cronológicas y fotos.
- **Fase 4 (administrativa):** pestaña **Prefactura** generada desde una cotización
  aprobada (subtotal/ITBIS/total); pestaña **Factura** de solo lectura con historial —
  la conversión Prefactura→Factura es la única acción del sistema restringida a rol
  **admin** (oficina puede crear/ver prefacturas pero no convertirlas). Pestaña
  **Ampliaciones** (siempre atadas al mismo proyecto, con enlace opcional a una
  cotización). Pestaña **Tickets** de soporte con historial de estados.
- **Fase 5 (IA):** **"🤖 Organizar con IA"** en Levantamiento (resume notas + analiza
  fotos, guarda en `Survey.ai_summary`). **Dictado por voz** (🎙️) en los campos de texto
  del Levantamiento vía Web Speech API del navegador — ningún modelo de IA transcribe
  audio nativamente, así que esto es 100% del lado del cliente, sin costo. **"🤖 Generar
  propuesta técnica"** en Ingeniería (borrador editable, no se auto-guarda). **"🤖 Sugerir
  materiales"** en Presupuesto (prellenar líneas desde el catálogo real). Pantalla global
  **"Preguntar a la IA"** (`/preguntar`): elige un proyecto y pregunta en lenguaje natural
  sobre su expediente completo.
  **Motor de IA: local y gratis con [Ollama](https://ollama.com)** (`llama3.2` para texto,
  `llava` para fotos) — corre en tu propia PC, sin costo por uso ni API key. Si
  Ollama no está corriendo, cada botón muestra un mensaje claro en vez de fallar — ver
  [Configurar la IA](#configurar-la-ia-fase-5).

Con esto quedan completadas las 5 fases del brief original.

## Capturas

<p>
  <img src="docs/screenshots/dashboard.png" alt="Dashboard de Multitec" width="280">
  <img src="docs/screenshots/presupuesto.png" alt="Presupuesto con sugerencia de materiales por IA" width="280">
</p>

## Arquitectura

- **Backend:** FastAPI + SQLAlchemy + Alembic, Python 3.14. Autenticación JWT, roles
  `admin` / `oficina`.
- **Base de datos:** SQLite por defecto en desarrollo (`backend/multitec.db`). Cambiar
  `DATABASE_URL` en `backend/.env` para usar PostgreSQL sin tocar el código.
- **Frontend:** React + Vite + TypeScript + Tailwind CSS v4, PWA (instalable en iPhone y
  escritorio), mobile-first, estilo inspirado en Apple.

## Requisitos

- Python 3.10+ (probado con 3.14)
- Node.js 20+ (probado con 24)
- (Opcional, para producción) PostgreSQL

## Backend — arrancar en desarrollo

```bash
cd backend
python -m venv venv
source venv/Scripts/activate        # Windows Git Bash. En PowerShell: venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                # ajustar ADMIN_EMAIL / ADMIN_PASSWORD / JWT_SECRET
alembic upgrade head                # crea las tablas
python -m app.db.seed                # crea el usuario admin inicial
uvicorn app.main:app --reload --port 8000
```

- Swagger interactivo: http://127.0.0.1:8000/docs
- Salud: http://127.0.0.1:8000/api/health

### Configurar la IA (Fase 5) — Ollama local, gratis

1. Instala [Ollama](https://ollama.com/download) (o vía `winget install --id Ollama.Ollama -e`
   en Windows). Queda corriendo como servicio local en `http://localhost:11434`.
2. Descarga los dos modelos que usa la app:
   ```bash
   ollama pull llama3.2   # ~2 GB — texto (propuestas, presupuestos, preguntas)
   ollama pull llava      # ~4.7 GB — visión (análisis de fotos del levantamiento)
   ```
3. `backend/.env` ya trae los valores por defecto (`OLLAMA_HOST`, `AI_MODEL=llama3.2`,
   `AI_VISION_MODEL=llava`) — no hace falta ninguna API key. Si Ollama no está
   corriendo o falta un modelo, los botones de IA muestran un mensaje claro en vez de
   fallar.
4. **Rendimiento:** al correr por CPU (sin GPU NVIDIA/CUDA no hay aceleración), cada
   respuesta puede tardar entre ~10 y ~60+ segundos según la laptop — normal, no es un
   error. Con GPU NVIDIA, Ollama la usa automáticamente sin cambiar nada en el código.
5. **GPU AMD (Vulkan) con salida corrupta:** en algunas GPU AMD (confirmado en una
   Radeon Pro 5300M) el backend Vulkan de Ollama produce JSON truncado o respuestas
   vacías por un bug del motor de gramática de llama.cpp. Si la propuesta técnica o la
   sugerencia de materiales fallan con errores de JSON, fuerza CPU-only cerrando Ollama
   (`taskkill /IM "ollama app.exe" /F` y `taskkill /IM ollama.exe /F`) y arrancándolo de
   nuevo con la variable `OLLAMA_VULKAN=0` puesta antes de `ollama serve` (o definida a
   nivel de sistema en Windows si el problema persiste tras reiniciar, ya que la app de
   bandeja de Ollama no la hereda por defecto).
6. Limitación conocida: las fotos en formato **HEIC** (nativo de iPhone) no son
   compatibles con el modelo de visión local — el análisis las omite automáticamente y
   sigue solo con las fotos en JPEG/PNG/WebP y el texto del levantamiento.
7. **Alternativa de pago (mejor calidad, más rápida):** el proyecto se integró
   originalmente con la API de Claude (`claude-haiku-4-5`) antes de cambiar a Ollama. Para
   volver a esa opción, el cambio queda acotado a
   `backend/app/services/ai_client.py` + `backend/app/core/config.py` (ver historial de
   git) — se necesitaría una API key de https://console.anthropic.com con crédito
   cargado.

### Migrar a PostgreSQL

`psycopg2-binary` ya está en `requirements.txt`, así que no hace falta instalarlo aparte.

1. Instalar PostgreSQL (en Windows: `winget install --id PostgreSQL.PostgreSQL.17 -e`).
2. Crear un usuario y una base de datos dedicados (evita usar el superusuario `postgres`
   directamente):
   ```sql
   CREATE USER multitec WITH PASSWORD 'tu-password';
   CREATE DATABASE multitec OWNER multitec;
   ```
3. En `backend/.env`, cambiar:
   ```
   DATABASE_URL=postgresql+psycopg2://multitec:tu-password@localhost:5432/multitec
   ```
4. Ejecutar `alembic upgrade head` de nuevo apuntando a la nueva base, y
   `python -m app.db.seed` para crear el usuario admin (los datos de SQLite no se migran
   automáticamente — es una base nueva).

Migración probada de punta a punta: las 4 migraciones de Alembic aplican limpio sobre
PostgreSQL sin cambios (son todas `create_table`, sin `ALTER` específico de SQLite).

## Frontend — arrancar en desarrollo

```bash
cd frontend
npm install
npm run dev
```

- App: http://localhost:5173 (el dev server hace proxy de `/api` y `/uploads` hacia
  `http://127.0.0.1:8000`, así que el backend debe estar corriendo).
- Para instalar como PWA en iPhone: abrir en Safari → compartir → "Agregar a pantalla de
  inicio".

## Usuario inicial

Definido en `backend/.env` (`ADMIN_EMAIL` / `ADMIN_PASSWORD`), creado por
`python -m app.db.seed`. Cámbialo antes de desplegar a producción.

Durante las pruebas de Fase 4 se creó además un usuario de prueba con rol `oficina`:
`oficina@multitec.com` / `oficina123` — útil para probar la restricción de "solo admin
convierte a factura". Elimínalo antes de producción si no lo necesitas.

## Estructura

```
multitec/
├─ backend/    FastAPI, modelos, migraciones Alembic, uploads (fotos/audio)
└─ frontend/   React + Vite PWA
```

## Roadmap

Todas las fases del brief original están construidas. Ideas para seguir creciendo el
sistema (no solicitadas, solo sugerencias):

- **Búsqueda semántica entre todos los proyectos** (embeddings/vector DB) si el Q&A actual
  (proyecto por proyecto) resulta insuficiente en uso real.
- **Infra:** Windows Server, servidor dedicado / cloud multiusuario (PostgreSQL ya
  soportado, ver [Migrar a PostgreSQL](#migrar-a-postgresql)).
