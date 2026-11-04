import type { LucideIcon } from 'lucide-react'

/** Color y frase de cada pantalla del menú. Las clases van completas (Tailwind solo ve texto literal). */
export const PAGE_INFO: Record<string, { description: string; gradient: string }> = {
  '/clientes': { description: 'Tus clientes, sus datos de contacto y sus proyectos.', gradient: 'from-brand-blue to-indigo-800' },
  '/proyectos': { description: 'Cada trabajo, desde el levantamiento hasta la entrega.', gradient: 'from-blue-600 to-cyan-800' },
  '/calendario': { description: 'Las visitas programadas de cada día y de cada técnico.', gradient: 'from-violet-600 to-indigo-800' },
  '/tickets': { description: 'Las averías y soportes que siguen abiertos.', gradient: 'from-rose-600 to-red-800' },
  '/preguntar': { description: 'Pregúntale a la IA sobre tus proyectos, precios y clientes.', gradient: 'from-fuchsia-600 to-purple-800' },
  '/cotizaciones': { description: 'Lo que se le propone al cliente: verla, editarla y enviarla.', gradient: 'from-amber-500 to-orange-700' },
  '/catalogo': { description: 'Productos, servicios, precios y existencias en bodega.', gradient: 'from-emerald-600 to-teal-800' },
  '/compras': { description: 'Facturas de compra y suplidores.', gradient: 'from-teal-600 to-cyan-800' },
  '/seguimiento': { description: 'Lo que falta por cobrar y las cotizaciones sin respuesta.', gradient: 'from-orange-500 to-rose-700' },
  '/hoja-de-tiempo': { description: 'Las horas trabajadas por técnico y por proyecto.', gradient: 'from-sky-600 to-blue-800' },
  '/administracion': { description: 'Usuarios, comprobantes, datos de la empresa y ajustes.', gradient: 'from-slate-700 to-gray-900' },
  '/usuarios': { description: 'Quién entra al sistema y qué puede hacer.', gradient: 'from-slate-600 to-slate-800' },
  '/ncf': { description: 'Secuencias de comprobantes fiscales de la DGII.', gradient: 'from-indigo-600 to-blue-900' },
  '/empresa': { description: 'Los datos de tu empresa que salen en cotizaciones y facturas.', gradient: 'from-blue-700 to-slate-800' },
  '/auditoria': { description: 'Quién hizo qué y cuándo dentro del sistema.', gradient: 'from-gray-600 to-gray-800' },
  '/aprendizaje-ia': { description: 'Lo que la IA aprende de tus correcciones y sus parámetros.', gradient: 'from-purple-600 to-indigo-800' },
  '/plataforma': { description: 'Las empresas que usan el sistema.', gradient: 'from-cyan-600 to-blue-800' },
  '/ayuda': { description: 'Videos, paso a paso y preguntas frecuentes.', gradient: 'from-green-600 to-emerald-800' },
}

/** Encabezado grande y centrado de cada pantalla del menú en la computadora, con el mismo estilo que el
 * saludo del Inicio. El título visible es decorativo: cada página conserva su propio h1 para lectores
 * de pantalla. En el celular no sale (ahí el espacio vale más). */
export function PageBanner({ to, label, icon: Icon }: { to: string; label: string; icon: LucideIcon }) {
  const info = PAGE_INFO[to]
  if (!info) return null
  return (
    <section
      aria-hidden="true"
      className={`mt-2 hidden rounded-[2rem] bg-gradient-to-br ${info.gradient} px-8 py-6 text-center text-white shadow-lg md:block`}
    >
      <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-white/15 ring-1 ring-white/25">
        <Icon className="h-8 w-8" />
      </span>
      <p className="mt-3 text-4xl font-bold tracking-tight">{label}</p>
      <p className="mx-auto mt-2 max-w-2xl text-base text-white/80">{info.description}</p>
    </section>
  )
}
