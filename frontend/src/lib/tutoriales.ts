// Catálogo de video tutoriales. Los archivos viven en /public/videos/<id>.mp4 (con su portada <id>.jpg) y se sirven como
// estáticos, sin iniciar sesión: así también se ven desde la pantalla de entrada. Cada video trae su transcripción para
// quien no pueda o no quiera reproducirlo. MP4 (H.264) y no WebM: es lo que reproduce el iPhone de los técnicos.
export type Tutorial = {
  id: string
  titulo: string
  descripcion: string
  /** Duración aproximada, solo para mostrar (ej. «30 s»). */
  duracion: string
  /** Lo que se dice y se hace en el video, en orden. */
  transcripcion: string[]
}

export const TUTORIALES: Tutorial[] = [
  {
    id: '00-guia-completa',
    titulo: 'Guía completa de Multitec',
    descripcion: 'Del levantamiento en la obra a la cotización, con ayuda de la inteligencia artificial.',
    duracion: '5 min 47 s',
    transcripcion: [
      'Entras con tu correo y tu contraseña; cada empresa ve solo sus datos.',
      'Registras al cliente y creas el proyecto de la obra.',
      'En el levantamiento escribes lo que viste, subes fotos y marcas dónde irá cada equipo.',
      'Un toque y la IA arma la cotización con los precios de tu catálogo; sigue trabajando aunque salgas de la pantalla.',
      'Actualizas precios y comparas con la cotización de un competidor.',
      'Ves la cotización en grande y la envías con detalles o con el monto general, por WhatsApp, correo o enlace.',
      'Agendas visitas en el Calendario, atiendes los Tickets, y revisas el Catálogo y las Compras con su reporte 606.',
      'En Administración registras los comprobantes fiscales (NCF), los usuarios y los datos de tu empresa.',
      'El mapa ubica la obra y «Cómo llegar» abre Google Maps, Waze o Apple Maps.',
      'El dueño del sistema crea empresas y demostraciones para los técnicos, que entran desde su iPhone.',
    ],
  },
  {
    id: '01-entrar-al-sistema',
    titulo: 'Entrar al sistema',
    descripcion: 'Inicia sesión y conoce el asistente de Inicio.',
    duracion: '24 s',
    transcripcion: [
      'Escribe tu correo y tu contraseña y pulsa Ingresar.',
      'En Inicio, el asistente te dice qué hay para hoy: visitas, levantamientos listos para cotizar y cotizaciones que esperan respuesta.',
      'En la computadora el menú está oculto: se abre con el botón ☰ de arriba o acercando el mouse al borde izquierdo, y se va al alejarlo.',
    ],
  },
  {
    id: '02-cliente-y-proyecto',
    titulo: 'Registrar al cliente y crear el proyecto',
    descripcion: 'El primer paso de toda obra.',
    duracion: '28 s',
    transcripcion: [
      'Entra a Clientes, pulsa + Nuevo y escribe el nombre, el teléfono y la dirección. Guarda el cliente.',
      'Desde la tarjeta del cliente lo llamas o le escribes por WhatsApp con un toque.',
      'Entra a Proyectos, pulsa + Nuevo, elige al cliente, describe la obra y pulsa Crear proyecto.',
    ],
  },
  {
    id: '03-levantamiento-y-puntos',
    titulo: 'Levantamiento, fotos y puntos marcados',
    descripcion: 'Lo que ves en la obra, y dónde va cada equipo.',
    duracion: '30 s',
    transcripcion: [
      'Abre el proyecto, entra a Datos y luego a Levantamiento. Escribe las notas y pulsa Guardar levantamiento.',
      'Sube una foto con Tomar foto.',
      'Pulsa Marcar equipos en la foto, elige el tipo (cámara, NVR / DVR, switch…) y toca la foto donde irá cada equipo.',
      'Guarda los puntos. La IA los cuenta para dar cantidades exactas.',
    ],
  },
  {
    id: '04-cotizacion-con-ia',
    titulo: 'Generar la cotización con IA',
    descripcion: 'Un toque, y puedes seguir trabajando.',
    duracion: '30 s',
    transcripcion: [
      'En Levantamiento pulsa Generar cotización con IA.',
      'La IA trabaja en el servidor: puedes salir de la pantalla y seguir con otra cosa. Una barra te avisa cuando termina.',
      'Pulsa Ver y ajustar la cotización. Cada acción es un ícono: Ver, Enviar, Editar, Aprobar, Partidas, Precios, Compras e Historial.',
    ],
  },
  {
    id: '05-precios-y-comparar',
    titulo: 'Actualizar precios y comparar con otra cotización',
    descripcion: 'Mantén tus precios al día y mira cómo estás frente a la competencia.',
    duracion: '31 s',
    transcripcion: [
      'Si cambiaron los precios del catálogo, abre la cotización, toca el ícono Precios y pulsa Actualizar precios. Ves qué cambia antes de aplicarlo.',
      'En Comparar con otra cotización escribe de quién es, sube el PDF o la foto —o pega el texto— y pulsa Subir y comparar.',
      'Verás línea por línea qué coincide, qué cuesta más o menos y qué le falta a cada cotización frente a los puntos marcados.',
      'Si la IA leyó algo mal, pulsa Corregir lo que leyó la IA.',
    ],
  },
  {
    id: '06-mapa-y-como-llegar',
    titulo: 'Mapa y «Cómo llegar»',
    descripcion: 'Ubica la obra y llega con tu aplicación favorita.',
    duracion: '11 s',
    transcripcion: [
      'En la ficha del proyecto pulsa Ver mapa: se ubica la dirección de la obra.',
      'Pulsa Cómo llegar y elige Google Maps, Waze o Apple Maps.',
    ],
  },
  {
    id: '07-plataforma-y-demos',
    titulo: 'Plataforma: empresas y demostraciones',
    descripcion: 'Solo para el dueño del sistema.',
    duracion: '28 s',
    transcripcion: [
      'Entra a Plataforma. Desde ahí creas empresas con su administrador, controlas su periodo de prueba y las suspendes o reactivas.',
      'Con Crear demo para técnicos eliges cuántos técnicos y cuántos días; se crean las cuentas con su clave temporal.',
      'Puedes editar la clave, descargar el archivo con los accesos o enviarlos por WhatsApp o correo.',
    ],
  },
  {
    id: '08-el-tecnico-en-el-iphone',
    titulo: 'El técnico en el iPhone',
    descripcion: 'Primera entrada y trabajo en la obra.',
    duracion: '33 s',
    transcripcion: [
      'Entra con el correo y la clave temporal que te dieron.',
      'La primera vez cambia la clave temporal por una tuya (mínimo 10 caracteres).',
      'Solo ves los proyectos que te asignaron; desde el teléfono haces el levantamiento, tomas las fotos y marcas los equipos.',
    ],
  },
  {
    id: '09-ver-y-enviar-cotizacion',
    titulo: 'Ver y enviar la cotización al cliente',
    descripcion: 'En grande, sin descargarla, y por el canal que prefieras.',
    duracion: '19 s',
    transcripcion: [
      'Abre la cotización y toca Ver: se abre en grande dentro de la app.',
      'Elige el formato: Con detalles, Por categoría o Monto general (solo el total del servicio).',
      'Envíala por WhatsApp, por correo o con el enlace del portal del cliente. Desde el visor también la editas.',
    ],
  },
  {
    id: '10-calendario-y-visitas',
    titulo: 'Calendario y visitas',
    descripcion: 'Agenda las visitas y ve la semana de un vistazo.',
    duracion: '12 s',
    transcripcion: [
      'Entra a Calendario y pulsa + Nueva. Elige el proyecto, el técnico, el día y la hora, y pulsa Agendar visita.',
      'Arriba ves la semana: los días con visitas llevan un punto. Toca un día para ver sus visitas.',
      'En la obra, el técnico marca Llegué al sitio y Terminé la visita; con eso se arma la Hoja de tiempo.',
    ],
  },
  {
    id: '11-tickets',
    titulo: 'Tickets de soporte',
    descripcion: 'Las averías abiertas de todos los proyectos en un solo lugar.',
    duracion: '12 s',
    transcripcion: [
      'Entra a Tickets: salen los abiertos, con el cliente, el problema y el técnico.',
      'Toca uno y llegas a ese ticket dentro de su proyecto: asigna al técnico, sube fotos, escribe la solución y ciérralo.',
    ],
  },
  {
    id: '12-catalogo',
    titulo: 'El catálogo de productos',
    descripcion: 'Tu vitrina, con precios y existencias.',
    duracion: '19 s',
    transcripcion: [
      'Entra a Catálogo: cada producto sale con su ícono, su precio y lo que hay en bodega.',
      'Busca por nombre, marca o código, o filtra por categoría.',
      'Toca un producto para ver su ficha: editarlo, registrar entradas y salidas de bodega y sus reglas para la IA.',
    ],
  },
  {
    id: '13-compras-y-606',
    titulo: 'Compras y reporte 606',
    descripcion: 'Las facturas de tus suplidores, listas para la DGII.',
    duracion: '14 s',
    transcripcion: [
      'Entra a Compras y pulsa + Factura de compra: el suplidor, el NCF, los montos y el ITBIS.',
      'Arriba ves lo comprado y el ITBIS del mes.',
      'En Reporte 606 eliges el mes y bajas el archivo para la DGII (y uno en CSV para revisarlo).',
    ],
  },
  {
    id: '14-comprobantes-fiscales-ncf',
    titulo: 'Comprobantes fiscales (NCF)',
    descripcion: 'Los rangos que te autoriza la DGII y los reportes 607 y 608.',
    duracion: '18 s',
    transcripcion: [
      'Entra a Administración y luego a NCF. Pulsa + Nueva.',
      'Elige el tipo de comprobante, escribe el rango autorizado (desde y hasta) y la fecha en que vence. Pulsa Crear secuencia.',
      'Cada factura toma sola el siguiente número del rango vigente.',
      'Desde aquí bajas los reportes 607 (ventas) y 608 (anulados) del mes.',
    ],
  },
  {
    id: '15-administracion',
    titulo: 'Administración',
    descripcion: 'Usuarios, datos de tu empresa y auditoría.',
    duracion: '13 s',
    transcripcion: [
      'En Administración está toda la configuración, cada parte con su botón.',
      'Usuarios: quién entra al sistema y con qué rol; ahí también restableces claves.',
      'Mi empresa: el logo y los datos que salen en las cotizaciones y facturas.',
      'Auditoría: quién hizo qué y cuándo.',
    ],
  },
]

export function tutorialPorId(id: string): Tutorial | undefined {
  return TUTORIALES.find((t) => t.id === id)
}

export function videoUrl(id: string): string {
  return `/videos/${id}.mp4`
}

export function posterUrl(id: string): string {
  return `/videos/${id}.jpg`
}
