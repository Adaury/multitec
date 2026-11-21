# Multitec en Hostinger — guía de instalación

Esta guía instala la versión Laravel + MySQL de Multitec en un hosting compartido de Hostinger (sin VPS ni servidor propio: solo
PHP y MySQL). Hay **dos formas de instalar**; elige una:

| Forma | Cuándo | Qué importas en el paso 5 |
|---|---|---|
| **A. Instalación limpia** (por defecto) | Empiezas desde cero, sin clientes ni proyectos. | `base-de-datos-limpia.sql` + el primer acceso de `PRIMER-ACCESO.txt` |
| **B. Con tus datos** | Pasas tu sistema actual con clientes, proyectos y facturas. | `base-de-datos.sql` (+ `archivos-subidos.zip`); el paquete se construye con `build.ps1 -ConDatos` |

## 0. Lo que necesitas

| Cosa | Detalle |
|---|---|
| Plan de Hostinger | Cualquiera que permita **PHP 8.3** y **MySQL**. Con **SSH** es más cómodo (ver paso 8), pero no es obligatorio. |
| Dominio o subdominio | Ejemplo `app.tudominio.com`, con **SSL gratis** activado (hPanel → Seguridad → SSL). |
| El paquete | La carpeta que genera `build.ps1` / `migrar-datos.ps1` (queda en `MultitecBackups\despliegue-hostinger\<fecha>`). |

El paquete trae: `multitec-app.zip` (la aplicación), `multitec-public_html.zip` (la parte web), `requisitos.php`,
`.env.production.example`, `GUIA-INSTALACION.md` (esta guía), `LEEME.txt` (pasos resumidos y sumas de comprobación) y:
- instalación limpia: `base-de-datos-limpia.sql` y `PRIMER-ACCESO.txt` (correo y clave temporal del administrador);
- con datos (`-ConDatos`): `base-de-datos.sql` y `archivos-subidos.zip`.

Para generar el paquete en tu PC: `deploy\hostinger\build.ps1` (limpia) o `build.ps1 -ConDatos`. Para una instalación limpia
puedes poner tus datos: `build.ps1 -Empresa "Mi empresa" -NombreAdmin "Tu nombre" -CorreoAdmin tu@correo.com`.
No sube nada a ningún sitio: solo escribe archivos en `MultitecBackups\despliegue-hostinger\<fecha>`.

> **Estructura.** La aplicación (código, `.env`, claves) va **fuera** de `public_html`; solo la carpeta web va dentro. Así nadie
> puede pedir por internet el `.env` ni el código. Quedará así:
>
> ```
> domains/tudominio.com/
> ├── multitec/        ← la aplicación (multitec-app.zip)
> └── public_html/     ← la parte web (multitec-public_html.zip)
> ```

## 1. Revisar el servidor (5 minutos)

1. hPanel → **Avanzado → Configuración de PHP**: elige **PHP 8.3** y activa las extensiones: `pdo_mysql`, `mbstring`, `openssl`,
   `gd`, `fileinfo`, `ctype`, `json`, `tokenizer`, `xml`, `dom`, `curl`, `exif`, y para Excel: `zip`, `simplexml`, `xmlreader`, `xmlwriter`.
2. En **Opciones de PHP** pon: `upload_max_filesize = 32M`, `post_max_size = 40M`, `memory_limit = 256M`, `max_execution_time = 120`.
   (Las fotos y audios pueden pesar hasta 25 MB.)
3. Opcional: sube `requisitos.php` a `public_html`, edita la `CLAVE` dentro, ábrelo en
   `https://tudominio.com/requisitos.php?clave=...`, **y bórralo**.

## 2. Crear la base de datos

hPanel → **Bases de datos → Bases de datos MySQL**: crea una base y su usuario. Anota los tres datos (nombre, usuario,
contraseña); en Hostinger el nombre y el usuario llevan prefijo (`u123456789_multitec`).

## 3. Subir la aplicación

1. **Administrador de archivos** → entra a `domains/tudominio.com/` → sube **`multitec-app.zip`** → clic derecho → **Extraer**.
   Debe quedar la carpeta `multitec` al lado de `public_html`.
2. Entra a `public_html` → sube **`multitec-public_html.zip`** → **Extraer** (borra antes el `index.html`/`default.php` de Hostinger si hay).
3. Si el paquete incluye archivos subidos: sube **`archivos-subidos.zip`** a `multitec/storage/app/private/` y extráelo ahí
   (queda `multitec/storage/app/private/uploads/…`).
4. Permisos: las carpetas `multitec/storage` y `multitec/bootstrap/cache` deben ser escribibles (755 normalmente alcanza; 775 si falla).

## 4. Configurar (`.env`)

1. Copia `.env.production.example` a `multitec/.env` (en el administrador de archivos: subir y renombrar).
2. Rellena, como mínimo:
   - `APP_URL=https://tudominio.com`
   - `APP_KEY=` → 32 bytes aleatorios en base64 con prefijo `base64:` (con SSH: `php artisan key:generate --show`).
   - `JWT_SECRET=` → 64 caracteres aleatorios **distintos** de `APP_KEY`.
   - `DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD` (los del paso 2).
3. Verifica que `APP_ENV=production` y `APP_DEBUG=false`. **Nunca** lo dejes con `APP_DEBUG=true` en internet.

> Para generar claves sin SSH: en tu PC, en una consola, `php -r "echo 'base64:'.base64_encode(random_bytes(32));"` y
> `php -r "echo bin2hex(random_bytes(32));"`.

## 5. Cargar los datos

phpMyAdmin (hPanel → Bases de datos → phpMyAdmin) → elige tu base (vacía) → **Importar**:

- **Instalación limpia:** `base-de-datos-limpia.sql`. Trae todas las tablas, los planes, el catálogo base de artículos y un
  administrador. Su correo y su clave temporal están en `PRIMER-ACCESO.txt`.
  Si el correo del paquete es `admin@cambia-esto.com`, cámbialo en la pestaña **SQL** de phpMyAdmin:
  `UPDATE users SET email='tu@correo.com' WHERE id=1;` (y `UPDATE companies SET contact_email='tu@correo.com' WHERE id=1;`).
- **Con tus datos:** `base-de-datos.sql`.

El archivo pesa poco: entra sin problema. Con SSH, en vez de importar puedes crear la base vacía desde el propio servidor:
`php artisan migrate --force` y luego `php artisan multitec:crear-administrador tu@correo.com --empresa="Mi empresa" --nombre="Tu nombre"`
(muestra la clave temporal una sola vez).

## 6. Primer arranque

1. Abre `https://tudominio.com`. Debe verse la pantalla de entrada con el logo de Multitec.
2. **Instalación limpia:** entra con el correo y la **clave temporal** de `PRIMER-ACCESO.txt`. El sistema te lleva a *Mi perfil* y no te
   deja usar nada más hasta que la cambies por una tuya (mínimo 10 caracteres). Después **borra `PRIMER-ACCESO.txt`**.
   **Con tus datos:** entra con tu usuario y contraseña de siempre (las claves se conservaron: son compatibles).
3. Revisa: Clientes, Proyectos, abrir una cotización y ver su PDF (con detalles, por categoría y monto general), Facturación → reportes DGII.
4. Abre `https://tudominio.com/web`: es la página pública. La sección **Empresas aliadas** sale de la base de datos: en una instalación
   limpia está vacía; agrégalas en *Plataforma → Sitio* (nombre, descripción, enlace y logo; los logos van en la carpeta `public_html/brand`).
5. Registro de empresas (`/registro`): quien se registra no elige clave. El sistema le genera una clave temporal (se muestra una sola
   vez) que debe cambiar al entrar, y el formulario avisa en vivo si el correo ya existe. Si no quieres registro público:
   `PUBLIC_SIGNUP_ENABLED=false` en el `.env`.

## 7. Seguridad: antes de dar acceso a otras personas

- [ ] HTTPS activo (candado) y `APP_URL` con `https://`.
- [ ] `APP_DEBUG=false` y `APP_ENV=production`.
- [ ] `APP_KEY` y `JWT_SECRET` propios (no los de ejemplo).
- [ ] Sin usuarios de prueba (el paquete ya los quita; `multitec:check-server` lo verifica).
- [ ] `requisitos.php` borrado del servidor.
- [ ] Cambia las contraseñas de las cuentas administradoras si las compartiste alguna vez.
- [ ] Correo configurado (`MAIL_*`) para que lleguen los avisos y para enviar cotizaciones al cliente (sin SMTP el botón avisa que no está configurado y se usa WhatsApp o el PDF).

## 8. Verificar con SSH (recomendado)

Si tu plan tiene SSH (hPanel → Avanzado → Acceso SSH):

```bash
cd ~/domains/tudominio.com/multitec
php artisan multitec:check-server        # revisa PHP, extensiones, límites, carpetas, claves, base de datos
php artisan config:cache                 # opcional: acelera y evita leer el .env en cada visita
php artisan route:cache                  # opcional
```

> Si usas `config:cache`, **cada vez que cambies el `.env` corre `php artisan config:cache` otra vez** (o `config:clear`).
> En Linux/LiteSpeed no se necesita para que funcione; en la PC de pruebas con Apache de Windows sí hacía falta.

Sin SSH, `multitec:check-server` no se puede correr; usa `requisitos.php` (paso 1) y las pruebas del paso 6.

## 9. Respaldos

- **Base de datos:** hPanel → Bases de datos → phpMyAdmin → Exportar, o los respaldos automáticos de tu plan. Hazlo antes de cada
  actualización y cada semana como mínimo.
- **Archivos subidos:** la carpeta `multitec/storage/app/private/uploads` (fotos, audios, logo). Descárgala de vez en cuando.
- Guarda las copias fuera del servidor y **no en OneDrive del trabajo**: contienen datos de clientes.

## 10. Actualizar a una versión nueva

1. En tu PC: `deploy\hostinger\build.ps1` (sin `-ConDatos`) genera `multitec-app.zip` y `multitec-public_html.zip` nuevos.
2. Respalda la base (paso 9).
3. Sube y extrae `multitec-app.zip` **encima** de `multitec` (no borra tu `.env` ni `storage`, que no vienen en el zip).
4. Sube y extrae `multitec-public_html.zip` encima de `public_html`.
5. Si la versión trae cambios de base de datos: con SSH `php artisan migrate --force`; sin SSH, se te entregará un `.sql` para importar.
6. Con `config:cache` activo: `php artisan config:cache`.

## 11. El día del cambio (migración final desde el sistema original)

Hazlo cuando quieras dejar de usar el Python. **Los datos que se escriban en el sistema original después de la exportación se pierden.**

1. Avisa a tu equipo y **detén el sistema original** (`detener-multitec.bat`).
2. En PowerShell: `cd C:\laragon\www\multitec-php\deploy\hostinger` y
   `.\migrar-datos.ps1 -QuitarEmpresas 2` (el número es el id de la empresa de pruebas que no debe viajar).
   El script exporta, importa, **verifica campo por campo**, compara los reportes DGII contra el original y construye el paquete.
   Si algo no coincide, **se detiene** y no genera nada.
3. Sube el paquete nuevo siguiendo los pasos 3 a 6 (base de datos vacía o, mejor, una nueva).
4. Prueba con tu equipo. Mantén el sistema original **apagado pero guardado** (no lo borres) algunas semanas.
5. Cuando todo esté bien, apunta el dominio que usan tus técnicos a Hostinger.

## 12. Lo que todavía NO está en esta versión

| Pendiente | Qué pasa hoy |
|---|---|
| e-CF (facturación electrónica DGII) | Fuera de alcance en esta versión (ver nota de cumplimiento). |

**Ya incluido:** asistente «de hoy» (saluda al abrir el Inicio y escucha), puntos marcados en las fotos del levantamiento y
cotización con IA, comparación de cotizaciones ajenas, cotización en tres formatos (con detalles, por categoría y monto general),
exportaciones a Excel/CSV y modo claro/oscuro.

**La IA necesita `GEMINI_API_KEY`** en el `.env`: sin clave queda apagada y todo se hace a mano. Los datos de clientes que vayan en
una consulta salen hacia Google. **El micrófono del asistente solo funciona con HTTPS** (el candado del paso 0).

## 13. Si algo falla

| Síntoma | Qué mirar |
|---|---|
| Página en blanco o «500» | `multitec/storage/logs/laravel.log` (ahí queda el detalle; al usuario solo se le muestra un mensaje genérico). |
| «Falta app.html» / pantalla vacía | `multitec-public_html.zip` no se extrajo dentro de `public_html`. |
| «No conecta a la base de datos» | Datos de `DB_*` en el `.env` (el nombre y usuario llevan prefijo en Hostinger). |
| Las fotos no suben | `upload_max_filesize` / `post_max_size` (paso 1). |
| Todos reciben 401 al entrar | `JWT_SECRET` vacío o cambiado; o el reloj del servidor. |
| Se ve la «M» o logos viejos tras actualizar | Caché del navegador/teléfono: Ctrl+Shift+R, o borra los datos del sitio. En el teléfono quita la app de la pantalla de inicio y vuelve a agregarla. |
| El PDF o la IA fallan | `multitec/storage/logs/laravel.log`; la IA además pide `GEMINI_API_KEY`. |
| «Demasiados intentos» | Límite de seguridad (10 inicios de sesión por minuto por dirección). Espera un minuto. |
