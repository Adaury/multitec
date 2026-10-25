# Publicar Multitec con un dominio propio (HTTPS)

Hoy los técnicos entran por un túnel de ngrok cuya dirección cambia. Con un **dominio propio** la dirección es
fija, y eso es lo que pide el iPhone para instalar la app en la pantalla de inicio y usar cámara, micrófono y GPS
(todos exigen HTTPS con una dirección estable).

## Recomendación: Cloudflare Tunnel + Caddy local

```
iPhone ──HTTPS──► Cloudflare ──túnel (conexión SALIENTE)──► cloudflared ──► Caddy 127.0.0.1:8080 ──► web (dist) y /api → uvicorn :8000
```

Por qué esta y no otras:

| Opción | Costo | ¿Abre puertos del router? | ¿Sirve con IP compartida (CGNAT)? | Riesgo |
|---|---|---|---|---|
| **Cloudflare Tunnel** | $0 + el dominio | **No** | **Sí** | Medio: queda en internet (se mitiga abajo) |
| ngrok con dominio propio | de pago | No | Sí | Medio |
| Caddy + DNS dinámico + reenvío de puertos | $0 | **Sí (80 y 443)** | **No** | Alto: el PC queda expuesto directo |
| Tailscale (solo equipo) | $0 | No | Sí | Bajo, pero cada teléfono necesita la app de Tailscale |

> Los precios y límites de planes los dan fuentes de terceros y cambian: confírmalos al contratar.

## Lo que necesitas de tu lado

1. **Un dominio.** Un `.com` cuesta unos 10-12 USD al año (Cloudflare Registrar lo vende a costo; Namecheap y
   Porkbun son alternativas). Un `.do` es bastante más caro (consulta nic.do) y solo aporta imagen local.
2. **Una cuenta gratuita de Cloudflare** con ese dominio agregado (se cambian los *nameservers* en el registrador).

## Pasos (PowerShell como administrador)

1. En Cloudflare: **Zero Trust → Networks → Tunnels → Create a tunnel**. Pon como *Public Hostname*
   `erp.tudominio.com` → servicio `http://127.0.0.1:8080`. Cloudflare te da un comando con un *token*.
2. Instala el conector y regístralo como servicio (arranca solo con Windows):
   ```powershell
   winget install --id Cloudflare.cloudflared -e
   cloudflared.exe service install <TOKEN_QUE_TE_DIO_CLOUDFLARE>
   ```
3. Configura el backend en `backend\.env`:
   ```ini
   ENVIRONMENT=production
   JWT_SECRET=<uno nuevo: python -c "import secrets;print(secrets.token_urlsafe(64))">
   CORS_ORIGINS=https://erp.tudominio.com
   ADMIN_PASSWORD=<una clave propia, no la de .env.example>
   ```
   Con `ENVIRONMENT=production` la app **se niega a arrancar** si `JWT_SECRET` sigue en su valor por defecto.
4. Compila la web y deja Caddy sirviéndola en `127.0.0.1:8080` con el archivo preparado para el túnel:
   ```powershell
   cd frontend; npm run build; cd ..
   caddy run --config deploy\Caddyfile.tunnel
   ```
   (Para dejarlo como servicio usa `deploy\install-web-service.ps1` apuntando a `Caddyfile.tunnel`.)
5. Prueba **desde el iPhone con datos móviles** (no con el WiFi de la oficina): abre `https://erp.tudominio.com`,
   inicia sesión y en Safari toca Compartir → **Añadir a pantalla de inicio**.
6. **Deja de usar** `abrir-tunel-multitec.bat` (ngrok) y **no abras** reglas de firewall para los puertos 80 ni 443:
   con el túnel no hacen falta.

## Seguridad mínima al quedar en internet

El ERP guarda datos de clientes, RNC y facturas. Antes de compartir la dirección:

- **Cloudflare Access** (Zero Trust, gratis hasta 50 usuarios): pide un correo autorizado y un código **antes** de
  que nadie vea siquiera la pantalla de login. Es la capa más fuerte. Pruébalo con la PWA instalada, porque
  algunas políticas de Access pueden interferir con las llamadas a `/api`.
- **Regla de límite de peticiones** en `/api/auth/*` (por ejemplo 10 por minuto por IP) y **bloqueo de países**
  distintos de República Dominicana (y donde viajen los técnicos). Las reglas gratuitas son pocas; confirma la cuota.
- La app ya trae: bloqueo por cuenta tras 5 intentos fallidos, contraseñas de al menos 10 caracteres, auditoría de
  accesos (menú **Auditoría**) y la documentación de la API apagada (`ENABLE_DOCS=false`).
- **Respaldos fuera de este equipo** (disco externo o nube cifrada) y una prueba de restauración de vez en cuando.
- **Actualizaciones**: Windows, Python, Caddy y `cloudflared update`.

## Lo que no está verificado

Las comparaciones de planes y precios, los límites del plan gratuito de Cloudflare, el precio oficial del `.do` y el
comportamiento exacto de la PWA tras Cloudflare Access salen de fuentes de terceros o de deducción del código, no
de pruebas en esta máquina. Valídalos con el primer despliegue.
