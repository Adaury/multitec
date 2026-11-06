import { Link } from 'react-router-dom'

// Texto base para revisar con un abogado antes de usarlo con clientes. Al cambiarlo, actualizar VERSION.
const VERSION = '5 de noviembre de 2026'

const SECTIONS: { title: string; body: string[] }[] = [
  {
    title: '1. El servicio',
    body: [
      'Multitec ERP es un sistema en internet para empresas de seguridad electrónica: clientes, levantamientos, cotizaciones, técnicos, tickets, facturación y reportes. Lo ofrece Multitec («nosotros») a la empresa que se registra («el cliente»).',
    ],
  },
  {
    title: '2. Prueba gratis, instalación y mensualidad',
    body: [
      'Al registrarse, el cliente tiene un periodo de prueba gratis. Al terminar, para seguir usando el sistema paga una sola vez la instalación y explicación, y luego una mensualidad por el soporte y el uso de la plataforma, según las tarifas vigentes publicadas en la página de registro.',
      'La mensualidad se paga por adelantado. Si no se paga, el sistema avisa y, pasados unos días de gracia, el acceso se suspende hasta ponerse al día. Los datos no se borran por un atraso.',
    ],
  },
  {
    title: '3. Los datos del cliente',
    body: [
      'Los datos que el cliente carga (sus clientes, proyectos, fotos, precios, facturas) son del cliente. Cada empresa tiene sus datos separados y ninguna otra empresa puede verlos.',
      'Guardamos copias de seguridad diarias. Si el cliente deja el servicio, puede pedir una copia de sus datos dentro de los 30 días siguientes; después de ese plazo se eliminan.',
    ],
  },
  {
    title: '4. Acceso de soporte',
    body: [
      'Para dar soporte, el personal autorizado de Multitec puede entrar a la cuenta del cliente. Ese acceso es por tiempo limitado, normalmente de solo lectura, y cada entrada y cada cambio quedan registrados en la auditoría que el administrador del cliente puede ver. Nunca pedimos ni vemos las contraseñas de los usuarios.',
    ],
  },
  {
    title: '5. Privacidad',
    body: [
      'Tratamos los datos personales conforme a la Ley 172-13 de Protección de Datos de Carácter Personal de la República Dominicana. Usamos los datos de contacto del cliente solo para dar el servicio, cobrarlo y avisarle de cambios. No vendemos ni compartimos datos con terceros, salvo obligación legal.',
      'El cliente es responsable de tener la autorización de sus propios clientes para registrar sus datos en el sistema.',
    ],
  },
  {
    title: '6. Uso correcto',
    body: [
      'El cliente se compromete a no usar el sistema para actividades ilegales, a cuidar las contraseñas de sus usuarios y a no intentar acceder a datos de otras empresas. Podemos suspender una cuenta que ponga en riesgo la seguridad del servicio.',
    ],
  },
  {
    title: '7. Disponibilidad y cambios',
    body: [
      'Hacemos lo posible para que el sistema esté disponible siempre, pero puede haber pausas por mantenimiento o causas ajenas. Podemos mejorar o cambiar funciones; si cambian las tarifas o estos términos, avisaremos con al menos 30 días.',
    ],
  },
]

/** Términos del servicio y política de privacidad (página pública). */
export function Terminos() {
  return (
    <div className="min-h-dvh bg-brand-bg px-5 py-8 dark:bg-gray-950">
      <article className="mx-auto max-w-3xl rounded-3xl bg-white p-6 shadow-sm ring-1 ring-black/5 md:p-10 dark:bg-gray-900 dark:ring-white/10">
        <h1 className="text-3xl font-extrabold tracking-tight text-gray-900 dark:text-gray-100">
          Términos del servicio y privacidad
        </h1>
        <p className="mt-1 text-sm text-gray-500">Vigentes desde el {VERSION}</p>
        <div className="mt-6 space-y-6">
          {SECTIONS.map((s) => (
            <section key={s.title}>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{s.title}</h2>
              {s.body.map((p) => (
                <p key={p.slice(0, 30)} className="mt-2 leading-relaxed text-gray-700 dark:text-gray-300">
                  {p}
                </p>
              ))}
            </section>
          ))}
        </div>
        <Link to="/registro" className="mt-8 inline-block font-semibold text-brand-blue hover:underline">
          ← Volver al registro
        </Link>
      </article>
    </div>
  )
}
