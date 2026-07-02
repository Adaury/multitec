# Contribuir a Multitec

Este es un repositorio privado de [Ferretería Popular SRL](./LICENSE). Esta guía es para
el equipo interno y colaboradores autorizados.

## Entorno de desarrollo

Sigue la sección "Backend — arrancar en desarrollo" y "Frontend — arrancar en desarrollo"
del [README](./README.md) para levantar el proyecto localmente antes de hacer cambios.

## Flujo de trabajo

1. Crea una rama a partir de `master`: `feature/<descripcion-corta>` o `fix/<descripcion-corta>`.
2. Haz commits pequeños y con mensajes que expliquen el *por qué* del cambio, no solo el qué.
3. Antes de subir cambios, corre las verificaciones locales (ver abajo).
4. Abre un Pull Request hacia `master` describiendo el cambio y cómo lo probaste.

## Convenciones de código

- **Backend (FastAPI + SQLAlchemy + Pydantic v2):**
  - Modelos con sintaxis `Mapped` / `mapped_column` de SQLAlchemy 2.x.
  - Cualquier cambio de modelo requiere una migración: `alembic revision --autogenerate -m "..."`.
  - Todo módulo de negocio (Survey, Engineering, Budget, Quote, Material, etc.) cuelga de
    `project_id` — el Proyecto es la entidad central del sistema.
  - Los códigos autogenerados (`PRY-`, `CAM-`, `COT-`, etc.) usan `services/code_generator.py`;
    no generes códigos manualmente en otros endpoints.
- **Frontend (React + Vite + TypeScript + Tailwind v4):**
  - Mobile-first; prueba cualquier cambio de UI en un viewport angosto (iPhone) antes de subir.
  - Corre `npm run lint` en `frontend/` antes de un PR.
- No subas secretos: `.env`, tokens o API keys van solo en `.env` local (ver `.env.example`).

## Verificaciones antes de un PR

```bash
# Backend
cd backend
source venv/Scripts/activate
alembic upgrade head          # confirma que las migraciones aplican limpio

# Frontend
cd frontend
npm run lint
npm run build                 # confirma que compila sin errores de tipos
```

## Reportar bugs o proponer cambios

Abre un Issue en este repositorio describiendo el comportamiento actual, el esperado, y
pasos para reproducir si aplica.
