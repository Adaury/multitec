# Visión de arquitectura multiplataforma

> **Estado: visión a futuro, no roadmap comprometido.** Este documento describe hacia
> dónde podría crecer Multitec si el negocio lo justifica más adelante. No implica
> trabajo en curso ni reemplaza el frontend web (React + Vite, PWA) actual, que sigue
> siendo el cliente activo del sistema.

## Premisa

El sistema ya no se concibe como una aplicación móvil única, sino como una plataforma
empresarial multiplataforma: varios clientes (móvil, escritorio, macOS, web, portales
externos) consumiendo un mismo backend, sin duplicar lógica de negocio en ninguno de
ellos.

## Plataformas oficiales

### Backend

- FastAPI
- PostgreSQL
- SQLAlchemy 2
- Alembic

Toda la lógica de negocio reside en el backend. Toda la información se consume mediante
una única API REST (preparada para incorporar WebSocket y GraphQL en el futuro si hace
falta).

**Estado actual:** ya construido y cumple este principio — el backend de Multitec ya es
FastAPI + SQLAlchemy 2 + Alembic + PostgreSQL, con toda la lógica de negocio (códigos
automáticos, ITBIS, flujo presupuesto→cotización→factura, roles, IA) centralizada ahí.
Cualquier cliente nuevo puede consumir la misma API REST sin cambios en el backend.

### Cliente 1 — Aplicación móvil

- **Framework:** Flutter
- **Plataformas:** iPhone (prioridad principal), Android
- **Objetivo:** uso en campo por técnicos e instaladores.
- **Funciones:** crear proyectos, levantamientos, fotografías, grabaciones de voz,
  bitácora, tickets, consultar proyectos, trabajo con sincronización cuando haya
  conexión.

**Estado actual:** cubierto hoy por el PWA React (instalable en iPhone, mobile-first,
con Levantamiento/Bitácora/Tickets/fotos/notas de voz vía Web Speech API). Una app
Flutter nativa sería un reemplazo o complemento futuro, no algo pendiente ahora.

### Cliente 2 — Aplicación de escritorio para Windows

- **Tecnología recomendada:** Flutter Desktop o equivalente que reutilice la lógica del
  proyecto.
- **Objetivo:** administración completa del ERP.
- **Funciones:** clientes, proyectos, presupuestos, cotizaciones, compras, facturación,
  reportes, configuración.

**Estado actual:** cubierto hoy por el mismo PWA React funcionando en navegador de
escritorio. También existe una guía de despliegue en Windows Server
(`deploy/README.md`) para correr el sistema completo (backend + frontend) en
infraestructura Windows real.

### Cliente 3 — Aplicación nativa para macOS

- Desarrollar una aplicación específica para macOS, optimizada para el ecosistema Apple.
- **Objetivos:** ingeniería, administración, supervisión de proyectos, gestión
  comercial, panel ejecutivo.
- La interfaz debe seguir las Human Interface Guidelines de Apple.
- Aprovechar características propias de macOS cuando sea posible:
  - Ventanas múltiples.
  - Arrastrar y soltar archivos.
  - Atajos de teclado.
  - Integración con Finder.
  - Notificaciones nativas.

**Estado actual:** no existe ningún trabajo iniciado en esta línea. Sería un proyecto
nuevo y separado (probablemente Swift/SwiftUI para cumplir HIG de forma nativa).

## Principios de arquitectura

Todos los clientes deben compartir:

- La misma API.
- El mismo modelo de datos.
- La misma autenticación.
- Los mismos permisos.
- La misma lógica de negocio.

**Nunca duplicar lógica entre aplicaciones.** Toda la inteligencia del sistema debe
permanecer en el backend.

## Sincronización

Para clientes con uso offline (principalmente el móvil de campo) se necesitaría una capa
de sincronización con:

- Trabajo fuera de línea.
- Sincronización automática.
- Resolución de conflictos.
- Caché local.

**Estado actual:** no existe todavía — el PWA actual requiere conexión para casi todo
(salvo lo que el service worker cachea para lectura). Es la pieza más grande y compleja
de esta visión si se llega a construir un cliente móvil nativo con soporte offline real.

## Inteligencia artificial

La IA será consumida por cualquiera de los clientes mediante la misma API. Ninguna
plataforma implementará lógica de IA de forma independiente — toda la IA reside en el
servidor.

**Estado actual:** ya cumplido — la IA (Ollama local: resumen de levantamiento,
propuesta de ingeniería, sugerencia de materiales, preguntas sobre proyectos con
búsqueda semántica) vive enteramente en `backend/app/services/ai_client.py` y
`embeddings.py`, expuesta vía `/api/ai/*`. Cualquier cliente nuevo la usa gratis, sin
reimplementar nada.

## Escalabilidad

La arquitectura debe permitir incorporar fácilmente nuevos clientes en el futuro, como:

- Aplicación web.
- Panel para clientes.
- Portal para proveedores.
- Panel para técnicos externos.
- API pública para integraciones.

Toda nueva plataforma debe poder reutilizar la infraestructura existente sin modificar
la lógica del negocio.
