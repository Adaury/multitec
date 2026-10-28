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
      'Si cambiaron los precios del catálogo, abre la cotización y pulsa Actualizar precios. Verás qué línea cambia, de cuánto a cuánto y el total nuevo, antes de aplicarlo.',
      'Una cotización pendiente se actualiza en su lugar. Una aprobada o rechazada genera una cotización nueva con los precios nuevos y la original queda igual (también puedes usar Crear nueva versión para editar).',
      'Para compararte con la competencia, pulsa Comparar con otra cotización, escribe de quién es y sube el PDF o la foto, o pega el texto.',
      'El resultado muestra línea por línea qué coincide, cuánto más barato o más caro está cada precio, qué trae solo una de las dos cotizaciones y cómo cada una cuadra con los puntos marcados en el levantamiento.',
    ],
    consejo:
      'La IA solo lee el documento y puede equivocarse: pulsa Corregir lo que leyó la IA y ajusta las líneas antes de fiarte del resultado. Un PDF escaneado hay que subirlo como foto.',
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
