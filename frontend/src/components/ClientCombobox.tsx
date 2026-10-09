import { useEffect, useId, useMemo, useRef, useState } from 'react'
import type { Client } from '../lib/types'

/** Minúsculas y sin tildes: "jose" encuentra "José". */
function fold(text: string | null | undefined): string {
  return (text ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
}

const MAX_RESULTS = 8

/** Menú desplegable con búsqueda para elegir un cliente: se filtra al escribir por nombre,
 * empresa, teléfono o RNC, y el último renglón permite crear uno nuevo en el momento. */
export function ClientCombobox({
  clients,
  value,
  onSelect,
  onCreateNew,
  placeholder = 'Buscar cliente por nombre, empresa o teléfono',
}: {
  clients: Client[]
  /** Id del cliente elegido (o null). */
  value: number | null
  onSelect: (client: Client) => void
  /** Recibe lo que se había escrito, para precargarlo como nombre del cliente nuevo. */
  onCreateNew: (typed: string) => void
  placeholder?: string
}) {
  const listId = useId()
  const rootRef = useRef<HTMLDivElement>(null)
  const selected = clients.find((c) => c.id === value) ?? null
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)

  const results = useMemo(() => {
    const q = fold(query).trim()
    const list = q
      ? clients.filter((c) => [c.name, c.company, c.phone, c.rnc].some((v) => fold(v).includes(q)))
      : clients
    return list.slice(0, MAX_RESULTS)
  }, [clients, query])
  const totalRows = results.length + 1 // + el renglón "Crear cliente nuevo"

  // Cerrar al tocar fuera.
  useEffect(() => {
    function onPointerDown(e: PointerEvent) {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('pointerdown', onPointerDown)
    return () => document.removeEventListener('pointerdown', onPointerDown)
  }, [])

  function choose(client: Client) {
    onSelect(client)
    setQuery('')
    setOpen(false)
  }

  function createNew() {
    onCreateNew(query.trim())
    setQuery('')
    setOpen(false)
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setOpen(true)
      setActive((i) => Math.min(i + 1, totalRows - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter' && open) {
      e.preventDefault()
      if (active < results.length) choose(results[active])
      else createNew()
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  return (
    <div ref={rootRef} className="relative">
      <input
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        autoComplete="off"
        autoCapitalize="none"
        spellCheck={false}
        className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 outline-none focus:border-brand-blue focus:ring-2 focus:ring-brand-blue/20 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
        placeholder={selected ? selected.name : placeholder}
        value={query}
        onChange={(e) => {
          setQuery(e.target.value)
          setActive(0)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
      />
      {selected && !query && (
        <p className="mt-1 truncate text-xs text-gray-500 dark:text-gray-400">
          Elegido: <b>{selected.name}</b>
          {selected.company ? ` · ${selected.company}` : ''}
          {selected.phone ? ` · ${selected.phone}` : ''}
        </p>
      )}
      {open && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-20 mt-1 max-h-72 w-full overflow-y-auto rounded-2xl bg-white p-1 shadow-lg ring-1 ring-black/10 dark:bg-gray-900 dark:ring-white/15"
        >
          {results.map((c, i) => (
            <li
              key={c.id}
              role="option"
              aria-selected={c.id === value}
              onPointerDown={(e) => {
                e.preventDefault() // no perder el foco antes de elegir
                choose(c)
              }}
              onMouseEnter={() => setActive(i)}
              className={`cursor-pointer rounded-xl px-3 py-2 ${
                i === active ? 'bg-brand-gray dark:bg-gray-800' : ''
              }`}
            >
              <p className="truncate text-sm font-medium text-gray-900 dark:text-gray-100">{c.name}</p>
              {(c.company || c.phone) && (
                <p className="truncate text-xs text-gray-500 dark:text-gray-400">
                  {[c.company, c.phone].filter(Boolean).join(' · ')}
                </p>
              )}
            </li>
          ))}
          {results.length === 0 && (
            <li className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">
              {query ? `Ningún cliente coincide con "${query}"` : 'Aún no hay clientes'}
            </li>
          )}
          <li
            role="option"
            aria-selected={false}
            onPointerDown={(e) => {
              e.preventDefault()
              createNew()
            }}
            onMouseEnter={() => setActive(results.length)}
            className={`cursor-pointer rounded-xl px-3 py-3 text-sm font-medium text-brand-blue ${
              active === results.length ? 'bg-brand-gray dark:bg-gray-800' : ''
            }`}
          >
            ＋ Crear cliente nuevo{query ? ` "${query}"` : ''}
          </li>
        </ul>
      )}
    </div>
  )
}
