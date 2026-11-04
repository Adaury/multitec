import type { ReactNode } from 'react'
import { Search, X, type LucideIcon } from 'lucide-react'

/** Buscador de las listas (clientes, proyectos, catálogo…): grande, con lupa y botón para borrar. */
export function SearchBox({
  value,
  onChange,
  placeholder,
  label,
}: {
  value: string
  onChange: (value: string) => void
  placeholder: string
  label: string
}) {
  return (
    <div className="relative w-full md:max-w-md">
      <Search className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" aria-hidden="true" />
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={label}
        className="w-full rounded-full border border-gray-200 bg-white py-3 pl-12 pr-11 text-base text-gray-900 shadow-sm outline-none transition focus:border-brand-blue focus:ring-2 focus:ring-brand-blue/20 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100 [&::-webkit-search-cancel-button]:hidden"
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange('')}
          aria-label="Borrar búsqueda"
          className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-1 text-gray-400 hover:bg-brand-gray hover:text-gray-600 dark:hover:bg-gray-800"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      )}
    </div>
  )
}

/** Fila de filtros tipo «chip» con el número de elementos de cada uno. */
export function FilterChips<T extends string>({
  value,
  onChange,
  options,
  label,
}: {
  value: T
  onChange: (value: T) => void
  options: { key: T; label: string; count?: number }[]
  label: string
}) {
  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-2">
      {options.map((option) => {
        const active = option.key === value
        return (
          <button
            key={option.key}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(option.key)}
            className={`flex shrink-0 items-center gap-2 whitespace-nowrap rounded-full px-4 py-2 text-sm font-medium transition ${
              active
                ? 'bg-brand-blue text-white shadow-sm'
                : 'bg-white text-gray-600 ring-1 ring-black/5 hover:bg-brand-gray dark:bg-gray-900 dark:text-gray-300 dark:ring-white/10 dark:hover:bg-gray-800'
            }`}
          >
            {option.label}
            {option.count !== undefined && (
              <span
                className={`rounded-full px-2 py-0.5 text-xs ${
                  active ? 'bg-white/20 text-white' : 'bg-brand-gray text-gray-500 dark:bg-gray-800 dark:text-gray-400'
                }`}
              >
                {option.count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}

const AVATAR_COLORS = [
  'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
  'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
  'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
  'bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300',
  'bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300',
  'bg-cyan-100 text-cyan-700 dark:bg-cyan-950 dark:text-cyan-300',
]

/** Círculo con las iniciales; el color sale del nombre, así cada cliente conserva siempre el suyo. */
export function Avatar({ name, size = 'md' }: { name: string; size?: 'md' | 'lg' }) {
  const words = name.trim().split(/\s+/).filter(Boolean)
  const initials = ((words[0]?.[0] ?? '?') + (words.length > 1 ? words[words.length - 1][0] : '')).toUpperCase()
  let hash = 0
  for (const ch of name) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0
  const color = AVATAR_COLORS[hash % AVATAR_COLORS.length]
  const box = size === 'lg' ? 'h-14 w-14 text-lg' : 'h-12 w-12 text-base'
  return (
    <span aria-hidden="true" className={`flex shrink-0 items-center justify-center rounded-2xl font-semibold ${box} ${color}`}>
      {initials}
    </span>
  )
}

/** Tarjetita de resumen (número grande con su ícono) para encabezar una lista. */
export function StatTile({ icon: Icon, label, value, tone }: { icon: LucideIcon; label: string; value: ReactNode; tone: string }) {
  return (
    <div className="flex items-center gap-3 rounded-3xl bg-white p-4 shadow-sm ring-1 ring-black/5 dark:bg-gray-900 dark:ring-white/10">
      <span className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ${tone}`}>
        <Icon className="h-6 w-6" aria-hidden="true" />
      </span>
      <span className="min-w-0">
        <span className="block truncate whitespace-nowrap text-xl font-bold leading-tight text-gray-900 xl:text-2xl dark:text-gray-100">{value}</span>
        <span className="block truncate text-xs font-medium text-gray-500 dark:text-gray-400">{label}</span>
      </span>
    </div>
  )
}

/** Mensaje de lista vacía con ícono. */
export function EmptyState({ icon: Icon, children }: { icon: LucideIcon; children: ReactNode }) {
  return (
    <div className="col-span-full rounded-3xl border-2 border-dashed border-gray-200 px-6 py-10 text-center dark:border-gray-800">
      <Icon className="mx-auto h-10 w-10 text-gray-300 dark:text-gray-600" aria-hidden="true" />
      <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{children}</p>
    </div>
  )
}

/** Comparación sin acentos ni mayúsculas para los buscadores. */
export function normalize(text: string | null | undefined): string {
  return (text ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
}
