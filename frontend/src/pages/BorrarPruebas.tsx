import { useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, Eraser, Package, ShieldCheck, Users } from 'lucide-react'
import { api } from '../lib/api'
import { Button, Card, Modal } from '../components/ui'
import { SearchBox, normalize } from '../components/ListTools'

interface ClientRow {
  id: number
  name: string
  company: string | null
  created_at: string
  projects: number
  quotes: number
  invoices: number
  fiscal_invoices: number
  tickets: number
  suspect: boolean
}

interface ProductRow {
  id: number
  code: string
  name: string
  price: number
  used_in_quotes: number
  suspect: boolean
}

interface Candidates {
  clients: ClientRow[]
  products: ProductRow[]
  confirm_word: string
}

interface Summary {
  clients: string[]
  products: string[]
  counts: { key: string; label: string; count: number }[]
  fiscal_invoices: { code: string; ncf: string; voided: boolean }[]
  files: number
  backup?: string | null
  files_removed?: number
}

function errorText(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail
  return typeof detail === 'string' ? detail : fallback
}

function toggle(set: Set<number>, id: number): Set<number> {
  const next = new Set(set)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  return next
}

function Chip({ children, tone = 'gray' }: { children: React.ReactNode; tone?: 'gray' | 'amber' | 'red' }) {
  const tones = {
    gray: 'bg-brand-gray text-gray-600 dark:bg-gray-800 dark:text-gray-300',
    amber: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300',
    red: 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300',
  }
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${tones[tone]}`}>{children}</span>
}

/** Administración → Borrar datos de prueba. Se eligen clientes (se borra todo lo suyo: proyectos, cotizaciones,
 * facturas, tickets…) y productos; antes de borrar se muestra exactamente qué se va a eliminar, hay que escribir
 * BORRAR y el servidor saca una copia de seguridad completa. */
export function BorrarPruebas() {
  const queryClient = useQueryClient()
  const { data, isLoading, error } = useQuery({
    queryKey: ['test-data'],
    queryFn: async () => (await api.get<Candidates>('/admin/test-data')).data,
  })
  const [clients, setClients] = useState<Set<number>>(new Set())
  const [products, setProducts] = useState<Set<number>>(new Set())
  const [initialized, setInitialized] = useState(false)
  const [search, setSearch] = useState('')
  const [preview, setPreview] = useState<Summary | null>(null)
  const [done, setDone] = useState<Summary | null>(null)
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState<string | null>(null)

  // Al abrir, quedan marcados los clientes cuyo nombre parece de prueba; el administrador revisa y decide.
  useEffect(() => {
    if (data && !initialized) {
      setClients(new Set(data.clients.filter((c) => c.suspect).map((c) => c.id)))
      setProducts(new Set(data.products.filter((p) => p.suspect).map((p) => p.id)))
      setInitialized(true)
    }
  }, [data, initialized])

  const q = normalize(search)
  const visibleClients = useMemo(
    () => (data?.clients ?? []).filter((c) => !q || normalize(`${c.name} ${c.company ?? ''}`).includes(q)),
    [data, q],
  )
  const visibleProducts = useMemo(
    () => (data?.products ?? []).filter((p) => !q || normalize(`${p.name} ${p.code}`).includes(q)),
    [data, q],
  )
  const word = data?.confirm_word ?? 'BORRAR'
  const total = clients.size + products.size

  async function review() {
    setBusy(true)
    setProblem(null)
    try {
      const { data: summary } = await api.post<Summary>('/admin/test-data/preview', {
        client_ids: [...clients],
        product_ids: [...products],
      })
      setConfirm('')
      setPreview(summary)
    } catch (err) {
      setProblem(errorText(err, 'No se pudo calcular qué se borra'))
    } finally {
      setBusy(false)
    }
  }

  async function remove() {
    setBusy(true)
    setProblem(null)
    try {
      const { data: result } = await api.post<Summary>(
        '/admin/test-data/delete',
        { client_ids: [...clients], product_ids: [...products], confirm },
        { timeout: 600_000 },
      )
      setPreview(null)
      setDone(result)
      setClients(new Set())
      setProducts(new Set())
      // Todo lo que se ve en las demás pantallas cambió.
      queryClient.invalidateQueries()
    } catch (err) {
      setProblem(errorText(err, 'No se pudo borrar'))
    } finally {
      setBusy(false)
    }
  }

  if (isLoading) return <p className="py-8 text-center text-gray-500">Cargando…</p>
  if (error || !data) return <p className="py-8 text-center text-red-600">No se pudo cargar la lista.</p>

  return (
    <div className="space-y-4 pb-28 pt-4 md:space-y-6 md:pt-8">
      <h1 className="sr-only">Borrar datos de prueba</h1>

      {done && (
        <div role="status" className="flex gap-3 rounded-3xl bg-emerald-50 p-4 text-sm text-emerald-900 ring-1 ring-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-200 dark:ring-emerald-900">
          <CheckCircle2 className="h-6 w-6 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-semibold">Listo, se borraron los datos de prueba.</p>
            <p>{done.counts.map((c) => `${c.count} ${c.label.toLowerCase()}`).join(' · ')}</p>
            {done.backup && (
              <p className="mt-1 text-xs opacity-80">
                Copia de seguridad de antes de borrar: <b>{done.backup}</b> (carpeta MultitecBackups).
              </p>
            )}
          </div>
        </div>
      )}

      <div className="flex gap-3 rounded-3xl bg-amber-50 p-4 text-sm text-amber-900 ring-1 ring-amber-200 dark:bg-amber-950/40 dark:text-amber-200 dark:ring-amber-900">
        <ShieldCheck className="h-6 w-6 shrink-0" aria-hidden="true" />
        <div className="space-y-1">
          <p>
            Marca lo que usaste <b>de prueba</b>. Al borrar un cliente se borra <b>todo lo suyo</b>: proyectos,
            cotizaciones, facturas, tickets, visitas y fotos.
          </p>
          <p>
            Antes de borrar te mostramos exactamente qué se elimina y se saca una <b>copia de seguridad</b> automática. Las
            compras (606) y los productos usados en cotizaciones reales se conservan.
          </p>
        </div>
      </div>

      <SearchBox value={search} onChange={setSearch} placeholder="Buscar cliente o producto…" label="Buscar cliente o producto" />

      <Card>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
            <Users className="h-5 w-5 text-brand-blue" aria-hidden="true" /> Clientes ({clients.size} de {data.clients.length})
          </h2>
          <div className="flex flex-wrap gap-2 text-sm">
            <button
              type="button"
              className="rounded-full bg-brand-gray px-3 py-1 font-medium text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-200"
              onClick={() => setClients(new Set(data.clients.filter((c) => c.suspect).map((c) => c.id)))}
            >
              Marcar los que parecen de prueba
            </button>
            <button
              type="button"
              className="rounded-full bg-brand-gray px-3 py-1 font-medium text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-200"
              onClick={() => setClients(new Set())}
            >
              Desmarcar todo
            </button>
          </div>
        </div>
        {visibleClients.length === 0 ? (
          <p className="py-4 text-center text-sm text-gray-500">No hay clientes que coincidan.</p>
        ) : (
          <ul className="grid grid-cols-1 gap-2 lg:grid-cols-2">
            {visibleClients.map((c) => {
              const checked = clients.has(c.id)
              return (
                <li key={c.id}>
                  <label
                    className={`flex cursor-pointer items-start gap-3 rounded-2xl p-3 ring-1 transition ${
                      checked
                        ? 'bg-red-50 ring-red-200 dark:bg-red-950/30 dark:ring-red-900'
                        : 'bg-white ring-black/5 hover:bg-brand-gray dark:bg-gray-900 dark:ring-white/10 dark:hover:bg-gray-800'
                    }`}
                  >
                    <input
                      type="checkbox"
                      className="mt-1 h-5 w-5 shrink-0 rounded accent-red-600"
                      checked={checked}
                      onChange={() => setClients((s) => toggle(s, c.id))}
                      aria-label={`Borrar cliente ${c.name}`}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium text-gray-900 dark:text-gray-100">{c.name}</span>
                      <span className="block truncate text-xs text-gray-500 dark:text-gray-400">
                        {c.company ? `${c.company} · ` : ''}creado el {new Date(c.created_at).toLocaleDateString('es-DO')}
                      </span>
                      <span className="mt-1.5 flex flex-wrap gap-1">
                        {c.suspect && <Chip tone="amber">parece de prueba</Chip>}
                        <Chip>{c.projects} proyecto(s)</Chip>
                        {c.quotes > 0 && <Chip>{c.quotes} cotización(es)</Chip>}
                        {c.tickets > 0 && <Chip>{c.tickets} ticket(s)</Chip>}
                        {c.invoices > 0 && <Chip tone={c.fiscal_invoices ? 'red' : 'gray'}>
                          {c.invoices} factura(s){c.fiscal_invoices ? `, ${c.fiscal_invoices} con NCF` : ''}
                        </Chip>}
                      </span>
                    </span>
                  </label>
                </li>
              )
            })}
          </ul>
        )}
      </Card>

      <Card>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
            <Package className="h-5 w-5 text-brand-blue" aria-hidden="true" /> Productos del catálogo ({products.size} de{' '}
            {data.products.length})
          </h2>
          {products.size > 0 && (
            <button
              type="button"
              className="rounded-full bg-brand-gray px-3 py-1 text-sm font-medium text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-200"
              onClick={() => setProducts(new Set())}
            >
              Desmarcar todo
            </button>
          )}
        </div>
        <p className="mb-3 text-xs text-gray-500 dark:text-gray-400">
          Si un producto está en una cotización que se queda, la línea se conserva con su descripción y su precio.
        </p>
        {visibleProducts.length === 0 ? (
          <p className="py-4 text-center text-sm text-gray-500">No hay productos que coincidan.</p>
        ) : (
          <ul className="grid grid-cols-1 gap-2 lg:grid-cols-2">
            {visibleProducts.map((p) => {
              const checked = products.has(p.id)
              return (
                <li key={p.id}>
                  <label
                    className={`flex cursor-pointer items-start gap-3 rounded-2xl p-3 ring-1 transition ${
                      checked
                        ? 'bg-red-50 ring-red-200 dark:bg-red-950/30 dark:ring-red-900'
                        : 'bg-white ring-black/5 hover:bg-brand-gray dark:bg-gray-900 dark:ring-white/10 dark:hover:bg-gray-800'
                    }`}
                  >
                    <input
                      type="checkbox"
                      className="mt-1 h-5 w-5 shrink-0 rounded accent-red-600"
                      checked={checked}
                      onChange={() => setProducts((s) => toggle(s, p.id))}
                      aria-label={`Borrar producto ${p.name}`}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium text-gray-900 dark:text-gray-100">{p.name}</span>
                      <span className="mt-1 flex flex-wrap gap-1">
                        <Chip>{p.code}</Chip>
                        <Chip>RD$ {p.price.toLocaleString('es-DO', { minimumFractionDigits: 2 })}</Chip>
                        {p.used_in_quotes > 0 && <Chip>en {p.used_in_quotes} línea(s) de cotización</Chip>}
                        {p.suspect && <Chip tone="amber">parece de prueba</Chip>}
                      </span>
                    </span>
                  </label>
                </li>
              )
            })}
          </ul>
        )}
      </Card>

      {problem && !preview && <p className="text-sm text-red-600 dark:text-red-400">{problem}</p>}

      <div className="fixed inset-x-0 bottom-[calc(4.5rem+env(safe-area-inset-bottom))] z-30 px-4 md:bottom-6">
        <div className="mx-auto flex max-w-3xl flex-col items-stretch gap-2 rounded-3xl bg-white/95 p-3 shadow-lg ring-1 ring-black/10 backdrop-blur sm:flex-row sm:items-center dark:bg-gray-900/95 dark:ring-white/10">
          <p className="flex-1 px-2 text-sm text-gray-700 dark:text-gray-300">
            {total === 0 ? 'No has elegido nada.' : `${clients.size} cliente(s) y ${products.size} producto(s) elegidos.`}
          </p>
          <Button className="!w-auto !py-3 px-5 text-sm" disabled={total === 0 || busy} onClick={review}>
            <span className="inline-flex items-center gap-2">
              <Eraser className="h-4 w-4" aria-hidden="true" /> {busy && !preview ? 'Calculando…' : 'Revisar qué se borra'}
            </span>
          </Button>
        </div>
      </div>

      <Modal open={preview !== null} onClose={() => !busy && setPreview(null)} title="Confirmar borrado">
        {preview && (
          <div className="space-y-4">
            <p className="text-sm text-gray-700 dark:text-gray-300">Se va a borrar para siempre:</p>
            <ul className="grid grid-cols-2 gap-2">
              {preview.counts.map((c) => (
                <li key={c.key} className="rounded-2xl bg-brand-gray px-3 py-2 dark:bg-gray-800">
                  <span className="block text-xl font-bold text-gray-900 dark:text-gray-100">{c.count}</span>
                  <span className="text-xs text-gray-600 dark:text-gray-400">{c.label}</span>
                </li>
              ))}
              {preview.files > 0 && (
                <li className="rounded-2xl bg-brand-gray px-3 py-2 dark:bg-gray-800">
                  <span className="block text-xl font-bold text-gray-900 dark:text-gray-100">{preview.files}</span>
                  <span className="text-xs text-gray-600 dark:text-gray-400">Archivos (fotos, audios)</span>
                </li>
              )}
            </ul>

            {preview.fiscal_invoices.length > 0 && (
              <div className="flex gap-2 rounded-2xl bg-red-50 p-3 text-sm text-red-800 dark:bg-red-950/40 dark:text-red-200">
                <AlertTriangle className="h-5 w-5 shrink-0" aria-hidden="true" />
                <div>
                  <p className="font-semibold">Hay {preview.fiscal_invoices.length} factura(s) con NCF:</p>
                  <p className="break-words text-xs">{preview.fiscal_invoices.map((f) => `${f.code} (${f.ncf})`).join(', ')}</p>
                  <p className="mt-1 text-xs">
                    Si esos NCF son de prueba, no pasa nada. Si son comprobantes <b>reales</b> autorizados por la DGII, no
                    los borres: anúlalos y repórtalos en el 608.
                  </p>
                </div>
              </div>
            )}

            <label className="block text-sm text-gray-700 dark:text-gray-300">
              Para confirmar, escribe <b>{word}</b>:
              <input
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                autoComplete="off"
                aria-label={`Escribe ${word} para confirmar`}
                className="mt-1 w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-base uppercase tracking-widest text-gray-900 outline-none focus:border-red-500 focus:ring-2 focus:ring-red-500/20 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
              />
            </label>
            {problem && <p className="text-sm text-red-600 dark:text-red-400">{problem}</p>}
            <div className="flex flex-col gap-2">
              <button
                type="button"
                onClick={remove}
                disabled={busy || confirm.trim().toUpperCase() !== word}
                className="w-full rounded-2xl bg-red-600 px-5 py-4 text-base font-medium text-white transition hover:bg-red-700 active:scale-[0.98] disabled:opacity-50"
              >
                {busy ? 'Sacando copia y borrando…' : 'Borrar definitivamente'}
              </button>
              <Button variant="ghost" onClick={() => setPreview(null)} disabled={busy}>
                Cancelar
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
