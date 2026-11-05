// Textos de la página de Ayuda. Están aquí, separados de la pantalla, para poder revisarlos y corregirlos sin tocar el
// código de la página. Los nombres de botones, menús y columnas son los mismos que se ven en la aplicación.
import type { Role } from './types'

export type PasoAyuda = {
  id: string
  titulo: string
  /** Dónde se hace, con el nombre del menú tal como aparece. */
  donde: string
  /** Video que acompaña el paso; si falta, el paso se muestra solo con texto. */
  tutorialId?: string
  /** Quién lo ve (por rol). Sin esto, todos. */
  roles?: Role[]
  /** Solo el dueño del sistema (administrador de la plataforma). */
  soloPlataforma?: boolean
  pasos: string[]
  consejo?: string
}

export const PASOS_AYUDA: PasoAyuda[] = [
  {
    id: 'entrar',
    titulo: 'Entrar al sistema',
    donde: 'Pantalla de inicio',
    tutorialId: '01-entrar-al-sistema',
    pasos: [
      'Abre la dirección del sistema en tu navegador (en el iPhone, en Safari).',
      'Escribe el correo y la contraseña que te dio el administrador y pulsa Ingresar.',
      'La primera vez entras con una clave temporal: el sistema te pide cambiarla por una tuya (mínimo 10 caracteres, que no sea una clave común).',
      'En Inicio, el asistente te dice qué hay para hoy: visitas, levantamientos listos para cotizar y cotizaciones que esperan respuesta.',
      'Cuando termines, pulsa Salir (arriba a la derecha). En Mi perfil puedes cambiar tu nombre, tu clave y cerrar tus otras sesiones.',
    ],
    consejo:
      'No compartas tu clave. Cada persona entra con su propio usuario y ve solo lo que su rol permite; los técnicos ven únicamente los proyectos que les asignaron.',
  },
  {
    id: 'cliente-proyecto',
    titulo: 'Registrar al cliente y crear el proyecto',
    donde: 'Menús Clientes y Proyectos',
    tutorialId: '02-cliente-y-proyecto',
    pasos: [
      'En Clientes pulsa + Nuevo, escribe el nombre, el teléfono y la dirección, y pulsa Guardar cliente.',
      'En Proyectos pulsa + Nuevo, elige al cliente, describe la obra y pulsa Crear proyecto.',
      'Cada proyecto lleva su propio código (PRY-000001…) y reúne el levantamiento, las cotizaciones, las compras, la bitácora y las facturas.',
    ],
    consejo: 'Si el cliente ya existe, escribe parte de su nombre en el proyecto nuevo y elígelo de la lista: no lo repitas.',
  },
  {
    id: 'levantamiento',
    titulo: 'Levantamiento, fotos y puntos marcados',
    donde: 'Proyecto → Datos → Levantamiento',
    tutorialId: '03-levantamiento-y-puntos',
    pasos: [
      'Escribe en Notas lo que viste en la obra (también puedes dictarlo). Anota las Medidas y las Observaciones, y pulsa Guardar levantamiento.',
      'Pulsa Tomar foto y sube las fotos de la obra.',
      'Sobre una foto pulsa Marcar equipos en la foto. Elige el tipo (cámara, NVR / DVR, switch, gabinete, punto de red, cerradura o lector, sensor o alarma) y toca la foto donde irá cada equipo.',
      'Pulsa Guardar puntos. Los números continúan de una foto a otra y salen en el anexo de la cotización para el cliente.',
    ],
    consejo:
      'Marca cada equipo con su tipo correcto: la inteligencia artificial cuenta esos puntos y los usa como cantidades exactas en la cotización.',
  },
  {
    id: 'cotizacion-ia',
    titulo: 'Generar la cotización con inteligencia artificial',
    donde: 'Proyecto → Datos → Levantamiento',
    tutorialId: '04-cotizacion-con-ia',
    roles: ['admin', 'oficina'],
    pasos: [
      'Pulsa Generar cotización con IA. Lee las notas, las medidas, las observaciones y los puntos marcados, y arma el presupuesto y la cotización con los precios de tu catálogo.',
      'La IA trabaja en el servidor: puedes salir de la pantalla, cerrar la app o hacer otra cosa. Una barra te avisa cuando termina y, si volviste después, la cotización ya está lista.',
      'Pulsa Ver y ajustar la cotización. Revisa las líneas y los avisos: si lo marcado en la foto no cuadra con lo cotizado, o una línea no se encontró en el catálogo, te lo dice.',
      'Ajusta lo que haga falta con Editar y, cuando esté bien, pulsa Aprobar (o compártela con el cliente por su enlace).',
    ],
    consejo: 'La IA propone, tú decides: revisa siempre las cantidades y los precios antes de enviar o aprobar.',
  },
  {
    id: 'precios-comparar',
    titulo: 'Actualizar precios y comparar con otra cotización',
    donde: 'Proyecto → Comercial → Cotización',
    tutorialId: '05-precios-y-comparar',
    roles: ['admin', 'oficina'],
    pasos: [
      'Si cambiaron los precios del catálogo, abre la cotización, toca el ícono Precios y pulsa Actualizar precios. Verás qué línea cambia, de cuánto a cuánto y el total nuevo, antes de aplicarlo.',
      'Una cotización pendiente se actualiza en su lugar. Una aprobada o rechazada genera una cotización nueva con los precios nuevos y la original queda igual (también puedes usar Crear nueva versión para editar).',
      'Para compararte con la competencia, pulsa Comparar con otra cotización, escribe de quién es y sube el PDF o la foto, o pega el texto.',
      'El resultado muestra línea por línea qué coincide, cuánto más barato o más caro está cada precio, qué trae solo una de las dos cotizaciones y cómo cada una cuadra con los puntos marcados en el levantamiento.',
    ],
    consejo:
      'La IA solo lee el documento y puede equivocarse: pulsa Corregir lo que leyó la IA y ajusta las líneas antes de fiarte del resultado. Un PDF escaneado hay que subirlo como foto.',
  },
  {
    id: 'enviar-cotizacion',
    titulo: 'Ver y enviar la cotización al cliente',
    donde: 'Cotizaciones → Ver y enviar, o Proyecto → Comercial → Cotización → Ver',
    tutorialId: '09-ver-y-enviar-cotizacion',
    roles: ['admin', 'oficina'],
    pasos: [
      'Toca Ver: la cotización se abre en grande dentro de la app, sin descargarla. En la computadora puedes acercar o alejar.',
      'En Formato y envío elige cómo la recibe el cliente: Con detalles (cada línea con su precio), Por categoría, o Monto general (las partidas con su cantidad y solo el total del servicio). Puedes incluir las fotos marcadas.',
      'Elige el canal: WhatsApp (en el teléfono se comparte el PDF; en la computadora se descarga y se abre WhatsApp para adjuntarlo), Correo (lo envía el sistema con el PDF adjunto) o Enlace (el portal del cliente, donde puede verla y aprobarla).',
      'Si ves algo que corregir, toca Editar desde el mismo visor.',
      'En Partidas, Descargar partidas (Excel) baja las líneas de la cotización. Al editar una cotización o un presupuesto, Cargar partidas desde archivo agrega las líneas de uno o varios archivos Excel o CSV (Código, Descripción, Cantidad, Precio, Nota); las que están en el catálogo quedan enlazadas a su producto.',
    ],
    consejo: 'Para enviar por correo hay que configurar antes la cuenta de correo del sistema (SMTP). Mientras tanto usa WhatsApp o el enlace.',
  },
  {
    id: 'mapa',
    titulo: 'Mapa y «Cómo llegar»',
    donde: 'Proyecto → Información, y las visitas del día',
    tutorialId: '06-mapa-y-como-llegar',
    pasos: [
      'En Ubicación de la obra escribe la dirección o pega un enlace de Google Maps. También puedes usar el GPS estando en el sitio.',
      'Pulsa Ver mapa: la dirección se ubica en el mapa.',
      'Pulsa Cómo llegar y elige con qué aplicación navegar: Google Maps, Waze o Apple Maps.',
    ],
    consejo: 'Si la dirección no se encuentra en el mapa, pega el enlace de ubicación de Google Maps o usa el GPS: con coordenadas siempre sale.',
  },
  {
    id: 'calendario',
    titulo: 'Calendario y visitas',
    donde: 'Menú Calendario',
    tutorialId: '10-calendario-y-visitas',
    pasos: [
      'Pulsa + Nueva, elige el proyecto, el técnico, el día, la hora y la duración, y pulsa Agendar visita. Si el técnico ya tiene visitas ese día, te avisa.',
      'Arriba ves la semana completa: los días con visitas llevan un punto. Usa las flechas, el botón Hoy o el selector de fecha para moverte.',
      'Con dos o más visitas el día sale la Ruta del día, que abre Google Maps con todas las paradas en orden.',
      'En la obra, el técnico toca Llegué al sitio y luego Terminé la visita: con eso se calcula la Hoja de tiempo.',
    ],
  },
  {
    id: 'tickets',
    titulo: 'Tickets de soporte',
    donde: 'Menú Tickets, o Proyecto → Obra → Tickets',
    tutorialId: '11-tickets',
    pasos: [
      'En Tickets ves los abiertos de todos los proyectos, con el cliente, el problema y el técnico asignado. Cambia a Todos para ver también los cerrados.',
      'Toca un ticket para ir directo a él dentro de su proyecto.',
      'Asigna al técnico, sube las fotos del problema, escribe la solución y cámbialo a Resuelto o Cerrado.',
      'Para abrir uno nuevo: en el proyecto, Obra → Tickets → + Nuevo.',
    ],
    consejo: 'El técnico solo ve los tickets de sus proyectos o los que tiene asignados.',
  },
  {
    id: 'catalogo',
    titulo: 'El catálogo de productos',
    donde: 'Menú Catálogo',
    tutorialId: '12-catalogo',
    roles: ['admin', 'oficina'],
    pasos: [
      'Cada producto sale como una ficha con su ícono, su precio y lo que hay en bodega.',
      'Busca por nombre, marca, código o etiqueta, o toca una categoría para filtrar.',
      'Toca un producto para ver su ficha completa: Editar producto, registrar entradas y salidas de bodega, y las reglas que usa la IA al cotizar.',
      'Con Importar cargas muchos productos de una vez: uno o varios archivos a la vez, en Excel o CSV. Hay listas listas para llenar de materiales de alarma y de ferretería (solo pones el precio), y las categorías que falten se crean con un toque.',
      'Con Exportar bajas todo el catálogo en Excel: lo corriges ahí y lo vuelves a subir con Importar (cada fila actualiza su producto por el código).',
      'Con RD$ Precios ajustas precios en lote.',
    ],
    consejo: 'Mientras más completo esté el catálogo, mejor cotiza la IA: busca los productos ahí antes de inventar precios.',
  },
  {
    id: 'compras',
    titulo: 'Compras y reporte 606',
    donde: 'Menú Compras',
    tutorialId: '13-compras-y-606',
    roles: ['admin', 'oficina'],
    pasos: [
      'Pulsa + Factura de compra, elige el suplidor y escribe el NCF, las fechas, los montos de servicios y bienes, el ITBIS y las retenciones.',
      'Arriba ves cuántas facturas, cuánto se compró y cuánto ITBIS se facturó en el mes.',
      'En Reporte 606 elige el mes y el año: Revisar (CSV) para verlo en Excel y Archivo DGII (.txt) para subirlo a la DGII.',
      'Los suplidores se manejan en la pestaña Proveedores.',
    ],
    consejo: 'Verifica siempre el archivo contra la plantilla oficial vigente de la DGII antes de remitirlo.',
  },
  {
    id: 'ncf',
    titulo: 'Comprobantes fiscales (NCF)',
    donde: 'Menú Administración → NCF — solo administrador',
    tutorialId: '14-comprobantes-fiscales-ncf',
    roles: ['admin'],
    pasos: [
      'Pulsa + Nueva y elige el tipo de comprobante (por ejemplo B01 crédito fiscal o B02 consumo).',
      'Escribe el rango que te autorizó la DGII (Desde y Hasta) y la fecha en que vence. Pulsa Crear secuencia.',
      'Al convertir una prefactura en factura, el sistema toma solo el siguiente número del rango vigente de ese tipo.',
      'Desde la misma pantalla bajas los reportes 607 (ventas) y 608 (anulados) del mes.',
    ],
    consejo: 'Registra el rango nuevo antes de que se acabe o venza el actual: sin un rango vigente no se puede facturar.',
  },
  {
    id: 'administracion',
    titulo: 'Administración: usuarios, empresa y auditoría',
    donde: 'Menú Administración — solo administrador',
    tutorialId: '15-administracion',
    roles: ['admin'],
    pasos: [
      'Usuarios: crea las cuentas con su rol (administrador, oficina o técnico). Ahí también restableces una clave, ves las sesiones abiertas y desactivas a quien ya no trabaja.',
      'Mi empresa: el logo, el RNC, la dirección y las cuentas bancarias que salen en las cotizaciones y facturas.',
      'Auditoría: quién hizo qué y cuándo (accesos, precios, facturas anuladas, cambios de usuarios). No se puede borrar.',
      'Ajustes de IA: lo que la IA aprende de tus correcciones y los parámetros de cálculo.',
    ],
  },
  {
    id: 'plataforma',
    titulo: 'Empresas y demostraciones para técnicos',
    donde: 'Menú Plataforma — solo el dueño del sistema',
    tutorialId: '07-plataforma-y-demos',
    soloPlataforma: true,
    pasos: [
      'Con Nueva empresa creas una empresa con su administrador, que entra con una clave temporal de un solo uso. Puedes ponerle días de prueba y un máximo de usuarios.',
      'Con Crear demo para técnicos eliges cuántos técnicos y cuántos días: se crea una empresa de prueba con un administrador, los técnicos y unos clientes y proyectos de ejemplo.',
      'En las cuentas nuevas puedes Editar clave, Descargar archivo con los accesos o enviarlos por WhatsApp o por correo.',
      'Desde el detalle de una empresa la extiendes (+7, +14 o +30 días), cambias su máximo de usuarios, restableces la clave de su administrador o la suspendes.',
    ],
    consejo: 'Las claves temporales se muestran una sola vez: descarga el archivo o envía el acceso antes de cerrar la tarjeta.',
  },
  {
    id: 'tecnico',
    titulo: 'El técnico en el iPhone',
    donde: 'Desde el teléfono',
    tutorialId: '08-el-tecnico-en-el-iphone',
    roles: ['admin', 'tecnico'],
    pasos: [
      'Entra con el correo y la clave temporal que te dieron; la primera vez cámbiala por una tuya.',
      'En Proyectos solo verás los que te asignaron. Con el botón + del centro haces un levantamiento nuevo en un toque.',
      'Toma las fotos, marca los equipos y guarda: todo queda sincronizado con la oficina. Si no hay señal, lo que no se alcanzó a enviar queda guardado en el teléfono y se envía al volver la conexión.',
      'Para tenerla como una aplicación más: en Safari pulsa Compartir y luego Añadir a pantalla de inicio.',
    ],
  },
]

export type PreguntaFrecuente = {
  pregunta: string
  respuesta: string
  roles?: Role[]
}

export const PREGUNTAS_FRECUENTES: PreguntaFrecuente[] = [
  {
    pregunta: 'Olvidé mi contraseña. ¿Qué hago?',
    respuesta:
      'Pídele al administrador de tu empresa que te restablezca la clave en Usuarios: te genera una clave temporal de un solo uso y la cambias al entrar. Si eres el administrador, pídesela al dueño del sistema.',
  },
  {
    pregunta: '¿Puedo salir de la app mientras la IA arma la cotización?',
    respuesta:
      'Sí. La cotización se arma en el servidor, no en tu teléfono: puedes cerrar la pantalla o cambiar de aplicación. Al volver, la barra de arriba te muestra el avance o el resultado.',
    roles: ['admin', 'oficina'],
  },
  {
    pregunta: '¿Por qué la cotización trae menos (o más) equipos de los que marqué en la foto?',
    respuesta:
      'La IA entiende también lo que escribiste en las notas. Si marcaste más equipos que los cotizados y hay una sola línea de ese equipo, la sube sola y te avisa; si hay varias líneas, solo te avisa. Revisa los avisos que salen al generar la cotización.',
    roles: ['admin', 'oficina'],
  },
  {
    pregunta: '¿Qué pasa si no hay internet en la obra?',
    respuesta:
      'El levantamiento rápido se guarda en el teléfono y se envía solo cuando vuelve la conexión; lo pendiente se ve en la aplicación. No cierres la sesión ni borres los datos del sitio hasta que se envíe.',
  },
  {
    pregunta: 'La pantalla se quedó negra o en blanco al abrir la app.',
    respuesta:
      'Casi siempre es una versión vieja guardada en el teléfono. Cierra la pestaña y ábrela de nuevo dos veces; si aparece el mensaje «Algo salió mal al abrir la app», pulsa Actualizar la app. En el iPhone también puedes borrar los datos del sitio en Ajustes → Safari → Avanzado → Datos de sitios web.',
  },
  {
    pregunta: '¿Por qué no veo Plataforma en el menú?',
    respuesta:
      'Plataforma es solo del dueño del sistema: desde ahí se crean y administran las empresas. El administrador de cada empresa gestiona la suya en Usuarios, Mi empresa, NCF y Auditoría.',
  },
  {
    pregunta: 'Mi empresa dice que el periodo de prueba terminó.',
    respuesta:
      'La prueba tenía fecha de vencimiento. Contacta al dueño del sistema para que la extienda desde Plataforma; tus datos siguen guardados.',
  },
  {
    pregunta: '¿La IA puede equivocarse?',
    respuesta:
      'Sí. La IA propone cantidades, líneas y lee cotizaciones de otros, pero tú la revisas: los avisos señalan lo que no cuadra, y lo que leyó de otra cotización se puede corregir línea por línea antes de comparar.',
    roles: ['admin', 'oficina'],
  },
]
