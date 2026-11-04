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

/** Encabezado grande y centrado de cada pantalla del menú, con el mismo estilo que el saludo del Inicio:
 * compacto en el celular y grande en la computadora. El título visible es decorativo: cada página
 * conserva su propio h1 (oculto a la vista) para lectores de pantalla. */
export function PageBanner({ to, label, icon: Icon }: { to: string; label: string; icon: LucideIcon }) {
  const info = PAGE_INFO[to]
  if (!info) return null
  return (
    <section
      aria-hidden="true"
      className={`mt-1 rounded-3xl bg-gradient-to-br ${info.gradient} px-5 py-5 text-center text-white shadow-lg md:mt-2 md:rounded-[2rem] md:px-8 md:py-6`}
    >
      <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-2xl bg-white/15 ring-1 ring-white/25 md:h-14 md:w-14">
        <Icon className="h-6 w-6 md:h-8 md:w-8" />
      </span>
      <p className="mt-2 text-2xl font-bold tracking-tight md:mt-3 md:text-4xl">{label}</p>
      <p className="mx-auto mt-1 max-w-2xl text-sm text-white/80 md:mt-2 md:text-base">{info.description}</p>
    </section>
  )
}
