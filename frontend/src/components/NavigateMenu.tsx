import { useEffect, useRef, useState, type ReactNode } from 'react'
import { navigationLinks, type Coords, type Place } from '../lib/maps'

/** Botón «Cómo llegar» que deja elegir con qué app navegar: Google Maps, Waze o Apple Maps. Si solo hay una opción
 * (un enlace corto de Maps sin coordenadas ni dirección) va directo, sin menú. */
export function NavigateMenu({
  place,
  geocoded,
  className,
  wrapperClassName = 'flex flex-1',
  children,
}: {
  place: Place
  geocoded?: Coords | null
  className: string
  wrapperClassName?: string
  children: ReactNode
}) {
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const links = navigationLinks(place, geocoded)

  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent | TouchEvent) => {
      if (root.current && !root.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    document.addEventListener('touchstart', close)
    return () => {
      document.removeEventListener('mousedown', close)
      document.removeEventListener('touchstart', close)
    }
  }, [open])

  if (links.length === 0) return null
  if (links.length === 1) {
    return (
      <a href={links[0].href} target="_blank" rel="noopener noreferrer" className={className}>
        {children}
      </a>
    )
  }
  return (
    <div ref={root} className={`relative ${wrapperClassName}`}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className={`${className} w-full`}
      >
        {children}
      </button>
      {open && (
        <ul
          role="menu"
          className="absolute bottom-full right-0 z-30 mb-2 w-48 overflow-hidden rounded-2xl border border-gray-200 bg-white text-sm shadow-xl dark:border-gray-700 dark:bg-gray-900"
        >
          {links.map((link) => (
            <li key={link.id} role="none">
              <a
                role="menuitem"
                href={link.href}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => setOpen(false)}
                className="block px-4 py-3 font-medium text-gray-900 hover:bg-gray-50 dark:text-gray-100 dark:hover:bg-gray-800"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
