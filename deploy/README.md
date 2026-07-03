# Despliegue en Windows Server

Esta carpeta tiene todo lo necesario para correr Multitec como servicio permanente en un
Windows Server real (o cualquier Windows con permisos de administrador), siguiendo el
stack del brief original: **Windows Server + PostgreSQL + FastAPI**.

## Arquitectura

```
Internet / LAN
      │
      ▼
  Caddy (servicio "MultitecWeb")
      │  sirve frontend/dist (estático) en "/"
      │  reverse proxy "/api/*" y "/uploads/*" ──────►  uvicorn (servicio "MultitecBackend")
      │                                                  127.0.0.1:8000 (solo localhost)
      ▼                                                        │
  443/80 (expuesto)                                             ▼
                                                          PostgreSQL (127.0.0.1:5432)
```

El backend **nunca** se expone directamente a la red — solo Caddy escucha en 443/80, y
le hace proxy internamente. Esto evita tener que manejar CORS/TLS dentro de FastAPI.

## Requisitos

- Windows Server 2019+ (o Windows 10/11 para pruebas) con permisos de administrador.
- Python 3.13+, Node.js 20+, PostgreSQL 17 ya instalados (ver README principal).
- [NSSM](https://nssm.cc/) para correr el backend y Caddy como servicios de Windows:
  `winget install --id NSSM.NSSM -e`
- [Caddy](https://caddyserver.com/) como reverse proxy + servidor de estáticos:
  `winget install --id CaddyServer.Caddy -e`

Todos los comandos de esta guía asumen PowerShell **como administrador**.

## 1. Preparar la base de datos

Sigue "[Migrar a PostgreSQL](../README.md#migrar-a-postgresql)" del README principal —
crea un usuario y base de datos dedicados, nunca uses el superusuario `postgres`
directamente para la app.

## 2. Preparar el backend

```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edita backend\.env:
#   - DATABASE_URL apuntando al Postgres de producción
#   - JWT_SECRET: genera uno nuevo y único (nunca el de .env.example)
#   - ADMIN_PASSWORD: cambia el valor por defecto
#   - CORS_ORIGINS: el dominio real de producción (no localhost)
alembic upgrade head
python -m app.db.seed
```

## 3. Instalar el backend como servicio de Windows

```powershell
.\deploy\install-backend-service.ps1
```

Esto crea el servicio `MultitecBackend` (auto-inicio, se reinicia solo si falla), con
logs en `backend\logs\`. Verifica: `Invoke-WebRequest http://127.0.0.1:8000/api/health`

## 4. Preparar y construir el frontend

```powershell
cd frontend
npm install
npm run build
```

## 5. Configurar Caddy

Edita `deploy\Caddyfile`:

- Si tienes un dominio real con acceso a internet, cambia el bloque de sitio a tu
  dominio (ej. `erp.multitec.com.do {`) — Caddy obtiene HTTPS automático de Let's
  Encrypt sin configuración adicional.
- Si es una red local sin dominio público, deja `tls internal` — Caddy genera un
  certificado autofirmado. Cada equipo cliente necesitará confiar en ese certificado
  (Caddy lo instala automáticamente en el store de Windows del servidor, pero otros
  equipos en la red deberán importarlo manualmente o aceptar la advertencia del
  navegador).

## 6. Instalar Caddy como servicio de Windows

```powershell
.\deploy\install-web-service.ps1
```

Esto crea el servicio `MultitecWeb`. Abre el firewall si hace falta:

```powershell
New-NetFirewallRule -DisplayName "Multitec HTTPS" -Direction Inbound -LocalPort 443 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Multitec HTTP" -Direction Inbound -LocalPort 80 -Protocol TCP -Action Allow
```

## 7. Backups automáticos de PostgreSQL

```powershell
.\deploy\register-backup-task.ps1 -PgPassword "el-password-real-de-produccion"
```

Registra una Tarea Programada diaria (2:00 AM) que corre `backup-postgres.ps1`,
guardando dumps en `deploy\backups\` y borrando los de más de 14 días
(`-RetentionDays`). Para restaurar un backup:

```powershell
pg_restore -h 127.0.0.1 -U multitec -d multitec --clean deploy\backups\multitec_2026-01-01_020000.dump
```

## Actualizar a una versión nueva

```powershell
git pull
cd backend
venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
Restart-Service MultitecBackend

cd ..\frontend
npm install
npm run build
Restart-Service MultitecWeb
```

## Desinstalar

```powershell
.\deploy\uninstall-services.ps1
```

## Troubleshooting

- **El servicio no arranca**: revisa `backend\logs\backend.err.log` o
  `deploy\logs\web.err.log`.
- **Caddy no consigue certificado**: si usas un dominio real, confirma que el puerto 80
  esté abierto y accesible desde internet (Let's Encrypt lo necesita para validar el
  dominio vía HTTP-01).
- **El backend responde 401/403 raro después de reiniciar**: confirma que `JWT_SECRET`
  en `backend\.env` no cambió entre reinicios (si cambia, todos los tokens existentes
  quedan inválidos — los usuarios deben volver a iniciar sesión, es el comportamiento
  esperado, no un bug).
