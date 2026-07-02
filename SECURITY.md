# Política de seguridad

## Reportar una vulnerabilidad

Si encuentras una vulnerabilidad de seguridad en Multitec (por ejemplo: bypass de
autenticación, fuga de datos entre proyectos/clientes, inyección SQL, XSS, exposición de
credenciales), repórtala de forma privada a **profeadaurypaulino@gmail.com** en vez de
abrir un Issue público.

Incluye si es posible:

- Descripción del problema y su impacto potencial.
- Pasos para reproducirlo.
- Versión/commit afectado.

Recibirás una respuesta en un plazo razonable confirmando el reporte y los próximos
pasos. Como este es un repositorio privado de uso interno, no hay un programa formal de
recompensas, pero todo reporte responsable es bienvenido y se atenderá con prioridad.

## Versiones soportadas

Este proyecto no mantiene versiones paralelas: solo la rama `master` recibe
correcciones de seguridad.

## Alcance

Cosas que consideramos parte del alcance de seguridad de este proyecto:

- Autenticación y control de acceso por rol (`admin` / `oficina`).
- Aislamiento de datos entre proyectos y clientes.
- Manejo de archivos subidos (fotos, audio de levantamientos).
- Configuración de secretos (`JWT_SECRET`, credenciales de base de datos, API keys).

## Buenas prácticas al desplegar

- Cambia `JWT_SECRET`, `ADMIN_PASSWORD` y las credenciales de base de datos por defecto
  antes de pasar a producción (ver `.env.example`).
- Nunca subas el archivo `backend/.env` real al repositorio — ya está excluido en
  `.gitignore`.
- Si usas PostgreSQL en producción, restringe el acceso de red a la base de datos y usa
  credenciales dedicadas (no el usuario por defecto).
- Revisa periódicamente los usuarios con rol `admin`; solo ese rol puede convertir
  prefacturas en facturas.
