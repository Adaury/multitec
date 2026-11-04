import { Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { ADMIN_ITEMS } from '../components/navItems'
import { PAGE_INFO } from '../components/PageBanner'

/** Las secciones de configuración del negocio en un solo lugar del menú, cada una como un botón grande
 * con su ícono y para qué sirve. Así el menú lateral entra completo en la pantalla. */
export function Administracion() {
  return (
    <div className="space-y-4 py-4 md:space-y-6 md:py-8">
      <h1 className="text-xl font-semibold text-gray-900 md:sr-only dark:text-gray-100">Administración</h1>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:gap-4 xl:grid-cols-3">
        {ADMIN_ITEMS.map((item) => {
          const info = PAGE_INFO[item.to]
          return (
            <Link
              key={item.to}
              to={item.to}
              className="group flex items-center gap-4 rounded-3xl bg-white p-5 shadow-sm ring-1 ring-black/5 transition hover:-translate-y-0.5 hover:shadow-md active:scale-[0.98] dark:bg-gray-900 dark:ring-white/10"
            >
              <span
                className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br text-white shadow-sm ${info?.gradient ?? 'from-brand-blue to-blue-800'}`}
              >
                <item.icon className="h-7 w-7" aria-hidden="true" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-base font-semibold text-gray-900 dark:text-gray-100">{item.label}</span>
                {info && <span className="block text-sm text-gray-500 dark:text-gray-400">{info.description}</span>}
              </span>
              <ChevronRight
                className="h-5 w-5 shrink-0 text-gray-300 transition group-hover:translate-x-0.5 group-hover:text-brand-blue"
                aria-hidden="true"
              />
            </Link>
          )
        })}
      </div>
    </div>
  )
}
