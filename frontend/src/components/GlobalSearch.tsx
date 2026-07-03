import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { SearchResults } from '../lib/types'
import { IconButton } from './ui'

export function GlobalSearch() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 300)
    return () => clearTimeout(timer)
  }, [query])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  const { data, isFetching } = useQuery({
    queryKey: ['global-search', debouncedQuery],
    queryFn: async () => (await api.get<SearchResults>('/search', { params: { q: debouncedQuery } })).data,
    enabled: open && debouncedQuery.trim().length >= 2,
  })

  function close() {
    setOpen(false)
    setQuery('')
    setDebouncedQuery('')
  }

  function goTo(path: string) {
    navigate(path)
    close()
  }

  const hasQuery = debouncedQuery.trim().length >= 2
  const hasResults = data && (data.clients.length > 0 || data.projects.length > 0 || data.tickets.length > 0)

  return (
    <div ref={containerRef} className="relative">
      {!open && (
        <IconButton aria-label="Buscar" onClick={() => setOpen(true)}>
          🔍
        </IconButton>
      )}

      {open && (
        <div className="absolute right-0 top-0 z-20 w-72 rounded-2xl bg-white p-3 shadow-lg ring-1 ring-black/5">
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              placeholder="Buscar clientes, proyectos, tickets…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Escape' && close()}
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base outline-none focus:border-brand-blue focus:ring-2 focus:ring-brand-blue/20"
            />
            <IconButton aria-label="Cerrar búsqueda" onClick={close}>
              ✕
            </IconButton>
          </div>

          {hasQuery && (
            <div className="mt-2 max-h-80 overflow-y-auto">
              {isFetching && <p className="px-2 py-2 text-xs text-gray-400">Buscando…</p>}

              {!isFetching && !hasResults && (
                <p className="px-2 py-2 text-xs text-gray-400">Sin resultados.</p>
              )}

              {data && data.clients.length > 0 && (
                <div className="mb-2">
                  <p className="px-2 text-[10px] font-semibold uppercase tracking-wide text-gray-400">Clientes</p>
                  {data.clients.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => goTo(`/clientes/${c.id}`)}
                      className="block w-full rounded-xl px-2 py-2 text-left text-sm text-gray-700 hover:bg-brand-gray"
                    >
                      {c.name}
                      {c.company && <span className="text-gray-400"> ({c.company})</span>}
                    </button>
                  ))}
                </div>
              )}

              {data && data.projects.length > 0 && (
                <div className="mb-2">
                  <p className="px-2 text-[10px] font-semibold uppercase tracking-wide text-gray-400">Proyectos</p>
                  {data.projects.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => goTo(`/proyectos/${p.id}`)}
                      className="block w-full rounded-xl px-2 py-2 text-left text-sm text-gray-700 hover:bg-brand-gray"
                    >
                      {p.code} <span className="text-gray-400">— {p.client_name}</span>
                    </button>
                  ))}
                </div>
              )}

              {data && data.tickets.length > 0 && (
                <div>
                  <p className="px-2 text-[10px] font-semibold uppercase tracking-wide text-gray-400">Tickets</p>
                  {data.tickets.map((t) => (
                    <button
                      key={t.id}
                      onClick={() => goTo(`/proyectos/${t.project_id}?tab=tickets`)}
                      className="block w-full rounded-xl px-2 py-2 text-left text-sm text-gray-700 hover:bg-brand-gray"
                    >
                      {t.code} <span className="text-gray-400">— {t.problem}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
