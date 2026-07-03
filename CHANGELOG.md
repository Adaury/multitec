# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [Sin publicar]

### Añadido

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

- `backend/app/main.py` ya no falla al arrancar si `backend/uploads/` no existe (pasa
  en un clon nuevo, ya que está en `.gitignore`) — ahora se crea automáticamente antes
  de montar `StaticFiles`. Detectado al escribir los tests.
- Numeración duplicada en la sección "Configurar la IA" del README.

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
