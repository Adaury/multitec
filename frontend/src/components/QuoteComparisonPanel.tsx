import { useState, type ChangeEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, apiErrorMessage } from '../lib/api'
import { formatDOP } from '../lib/format'
import type { Quote } from '../lib/types'
import { Badge, Button, Card, Field, Input, Textarea } from './ui'
import { openUpload } from './UploadMedia'

interface Line {
  description: string
  quantity: number
  unit_price: number
}

interface Matched {
  external: Line
  ours: Line
  same_quantity: boolean
  price: 'igual' | 'mas_caro' | 'mas_barato'
  price_diff_pct: number
  status: 'igual' | 'diferente'
}

interface Coverage {
  kind: string
  label: string
  marked: number
  external: number
  ours: number
  external_status: 'ok' | 'falta' | 'sobra'
  ours_status: 'ok' | 'falta' | 'sobra'
}

interface Comparison {
  id: number
  label: string
  filename: string | null
  file_path: string | null
  quote_id: number | null
  items: Line[]
  total: number | null
  matched: Matched[]
  only_external: Line[]
  only_ours: Line[]
  coverage: Coverage[]
  totals: {
    external_subtotal: number
    external_total: number | null
    our_subtotal: number | null
    our_total: number | null
    our_code: string | null
  }
}

interface Summary {
  id: number
  label: string
  filename: string | null
  created_at: string
  lines: number
}

const COVERAGE_TONE = { ok: 'green', falta: 'red', sobra: 'amber' } as const
const COVERAGE_TEXT = { ok: 'Cuadra', falta: 'Falta', sobra: 'Sobra' } as const

/** Sube una cotización de otro (competidor o proveedor) —PDF, foto o texto pegado— y la compara con el levantamiento
 * (los puntos marcados en las fotos) y con la cotización propia. La IA solo LEE el documento; la comparación son reglas
 * fijas, y lo que la IA leyó se puede corregir antes de fiarse del resultado. */
export function QuoteComparisonPanel({ projectId, quotes }: { projectId: number; quotes: Quote[] }) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [selected, setSelected] = useState<number | null>(null)
  const [label, setLabel] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [text, setText] = useState('')
  const [quoteId, setQuoteId] = useState('')
  const [error, setError] = useState<string | null>(null)

  const list = useQuery({
    queryKey: ['comparisons', projectId],
    queryFn: async () => (await api.get<Summary[]>(`/projects/${projectId}/comparisons`)).data,
    enabled: open,
  })

  const upload = useMutation({
    mutationFn: async () => {
      const body = new FormData()
      body.append('label', label.trim())
      if (quoteId) body.append('quote_id', quoteId)
      if (file) body.append('file', file)
      else body.append('text', text)
      // Leer un PDF o una foto con la IA puede tardar: no se corta a los 30 s de siempre
      return (await api.post<Comparison>(`/projects/${projectId}/comparisons`, body, { timeout: 180000 })).data
    },
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ['comparisons', projectId] })
      queryClient.setQueryData(['comparison', projectId, created.id], created)
      setSelected(created.id)
      setLabel('')
      setFile(null)
      setText('')
      setError(null)
    },
    onError: (e) => setError(apiErrorMessage(e, 'No se pudo leer esa cotización')),
  })

  const canUpload = label.trim().length > 0 && (file !== null || text.trim().length > 0)

  return (
    <div className="space-y-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="w-full rounded-2xl bg-brand-gray px-4 py-3 text-left text-sm font-semibold text-gray-800 dark:bg-gray-800 dark:text-gray-100"
      >
        {open ? '▾' : '▸'} Comparar con otra cotización
      </button>
      {open && (
        <div className="space-y-3" data-testid="comparison-panel">
          <Card className="space-y-3">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Sube la cotización de un competidor o de un proveedor (PDF con texto, o una foto) y la comparo con el
              levantamiento y con tu cotización. También puedes pegar su texto.
            </p>
            <Field label="¿De quién es?">
              <Input value={label} maxLength={120} placeholder="Ej.: Competidor, Proveedor X" onChange={(e) => setLabel(e.target.value)} />
            </Field>
            <Field label="Archivo (PDF o foto)">
              <input
                type="file"
                accept="application/pdf,image/jpeg,image/png,image/webp"
                aria-label="Archivo de la cotización"
                className="block w-full text-sm text-gray-600 dark:text-gray-300"
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFile(e.target.files?.[0] ?? null)}
              />
            </Field>
            {!file && (
              <Field label="…o pega el texto de la cotización">
                <Textarea rows={4} value={text} onChange={(e) => setText(e.target.value)} />
              </Field>
            )}
            <Field label="Compararla con">
              <select
                value={quoteId}
                onChange={(e) => setQuoteId(e.target.value)}
                className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
              >
                <option value="">Mi cotización más reciente</option>
                {quotes.map((q) => (
                  <option key={q.id} value={q.id}>
                    {q.code} · {formatDOP(q.total)}
                  </option>
                ))}
              </select>
            </Field>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <Button onClick={() => upload.mutate()} disabled={!canUpload || upload.isPending}>
              {upload.isPending ? 'Leyendo la cotización… puede tardar un minuto' : 'Subir y comparar'}
            </Button>
          </Card>

          {list.data && list.data.length > 0 && (
            <div className="flex flex-wrap gap-2" role="list" aria-label="Comparaciones hechas">
              {list.data.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  role="listitem"
                  onClick={() => setSelected(c.id)}
                  className={`rounded-full px-3 py-1.5 text-xs font-medium ${
                    selected === c.id ? 'bg-brand-blue text-white' : 'bg-brand-gray text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                  }`}
                >
                  {c.label} · {c.lines} líneas
                </button>
              ))}
            </div>
          )}

          {selected !== null && (
            <ComparisonDetail
              key={selected}
              projectId={projectId}
              id={selected}
              quotes={quotes}
              onDeleted={() => {
                setSelected(null)
                queryClient.invalidateQueries({ queryKey: ['comparisons', projectId] })
              }}
            />
          )}
        </div>
      )}
    </div>
  )
}

function ComparisonDetail({
  projectId,
  id,
  quotes,
  onDeleted,
}: {
  projectId: number
  id: number
  quotes: Quote[]
  onDeleted: () => void
}) {
  const queryClient = useQueryClient()
  const key = ['comparison', projectId, id]
  const { data } = useQuery({
    queryKey: key,
    queryFn: async () => (await api.get<Comparison>(`/projects/${projectId}/comparisons/${id}`)).data,
  })
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<Line[]>([])
  const [error, setError] = useState<string | null>(null)

  const save = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      (await api.put<Comparison>(`/projects/${projectId}/comparisons/${id}`, payload)).data,
    onSuccess: (updated) => {
      queryClient.setQueryData(key, updated)
      queryClient.invalidateQueries({ queryKey: ['comparisons', projectId] })
      setEditing(false)
      setError(null)
    },
    onError: (e) => setError(apiErrorMessage(e, 'No se pudo guardar')),
  })
  const remove = useMutation({
    mutationFn: async () => api.delete(`/projects/${projectId}/comparisons/${id}`),
    onSuccess: onDeleted,
  })

  if (!data) return <p className="text-sm text-gray-500">Cargando comparación…</p>
  const t = data.totals

  return (
    <Card className="space-y-4" testId="comparison-result">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="font-semibold text-gray-900 dark:text-gray-100">{data.label}</p>
          <p className="text-xs text-gray-500">{data.filename ?? 'Texto pegado'}</p>
        </div>
        <div className="flex gap-2">
          {data.file_path && (
            <Button variant="secondary" className="!w-auto !px-3 !py-1.5 text-xs" onClick={() => openUpload(data.file_path!)}>
              Ver archivo
            </Button>
          )}
          <Button
            variant="ghost"
            className="!w-auto !px-3 !py-1.5 text-xs !text-red-600"
            onClick={() => window.confirm('¿Eliminar esta comparación?') && remove.mutate()}
          >
            Eliminar
          </Button>
        </div>
      </div>

      <Field label="Comparada con">
        <select
          value={data.quote_id ?? ''}
          onChange={(e) => save.mutate({ quote_id: e.target.value ? Number(e.target.value) : null })}
          className="w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
        >
          <option value="">Mi cotización más reciente{t.our_code ? ` (${t.our_code})` : ''}</option>
          {quotes.map((q) => (
            <option key={q.id} value={q.id}>
              {q.code} · {formatDOP(q.total)}
            </option>
          ))}
        </select>
      </Field>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-xl bg-gray-50 p-3 dark:bg-gray-800/60">
          <p className="text-xs text-gray-500">La otra cotización (sin ITBIS)</p>
          <p className="font-semibold">{formatDOP(t.external_subtotal)}</p>
          {t.external_total !== null && <p className="text-xs text-gray-500">Total que dice: {formatDOP(t.external_total)}</p>}
        </div>
        <div className="rounded-xl bg-gray-50 p-3 dark:bg-gray-800/60">
          <p className="text-xs text-gray-500">{t.our_code ? `La tuya (${t.our_code}, sin ITBIS)` : 'La tuya'}</p>
          <p className="font-semibold">{t.our_subtotal !== null ? formatDOP(t.our_subtotal) : 'Sin cotización'}</p>
          {t.our_total !== null && <p className="text-xs text-gray-500">Con ITBIS: {formatDOP(t.our_total)}</p>}
        </div>
      </div>

      {data.coverage.length > 0 && (
        <section>
          <p className="mb-1 text-sm font-semibold text-gray-900 dark:text-gray-100">Contra el levantamiento (puntos marcados)</p>
          <ul className="space-y-1 text-sm" data-testid="comparison-coverage">
            {data.coverage.map((c) => (
              <li key={c.kind} className="flex flex-wrap items-center justify-between gap-2">
                <span>
                  {c.label}: <strong>{c.marked}</strong> marcados
                </span>
                <span className="flex items-center gap-2 text-xs">
                  Otra: {c.external} <Badge tone={COVERAGE_TONE[c.external_status]}>{COVERAGE_TEXT[c.external_status]}</Badge>
                  Tuya: {c.ours} <Badge tone={COVERAGE_TONE[c.ours_status]}>{COVERAGE_TEXT[c.ours_status]}</Badge>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <p className="mb-1 text-sm font-semibold text-gray-900 dark:text-gray-100">Línea por línea</p>
        {data.matched.length === 0 && <p className="text-sm text-gray-500">Ninguna línea se parece a las de tu cotización.</p>}
        <ul className="space-y-2 text-sm" data-testid="comparison-matched">
          {data.matched.map((m, i) => (
            <li key={i} className="rounded-xl bg-gray-50 p-3 dark:bg-gray-800/60">
              <p className="font-medium text-gray-900 dark:text-gray-100">{m.external.description}</p>
              <p className="text-xs text-gray-500">Tuya: {m.ours.description}</p>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs">
                <span>
                  Cantidad: {m.external.quantity} vs {m.ours.quantity}
                </span>
                {!m.same_quantity && <Badge tone="amber">Cantidad distinta</Badge>}
                <span>
                  Precio: {formatDOP(m.external.unit_price)} vs {formatDOP(m.ours.unit_price)}
                </span>
                {m.price === 'mas_barato' && <Badge tone="blue">Ellos {Math.abs(m.price_diff_pct)}% más barato</Badge>}
                {m.price === 'mas_caro' && <Badge tone="amber">Ellos {m.price_diff_pct}% más caro</Badge>}
                {m.status === 'igual' && <Badge tone="green">Igual</Badge>}
              </div>
            </li>
          ))}
        </ul>
      </section>

      {data.only_external.length > 0 && (
        <section>
          <p className="mb-1 text-sm font-semibold text-gray-900 dark:text-gray-100">Solo en la otra cotización</p>
          <ul className="space-y-1 text-sm text-gray-700 dark:text-gray-300">
            {data.only_external.map((l, i) => (
              <li key={i}>
                {l.quantity} × {l.description} — {formatDOP(l.unit_price)}
              </li>
            ))}
          </ul>
        </section>
      )}
      {data.only_ours.length > 0 && (
        <section>
          <p className="mb-1 text-sm font-semibold text-gray-900 dark:text-gray-100">Solo en la tuya</p>
          <ul className="space-y-1 text-sm text-gray-700 dark:text-gray-300">
            {data.only_ours.map((l, i) => (
              <li key={i}>
                {l.quantity} × {l.description} — {formatDOP(l.unit_price)}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="space-y-2">
        {!editing ? (
          <Button
            variant="ghost"
            onClick={() => {
              setDraft(data.items.map((l) => ({ ...l })))
              setEditing(true)
            }}
          >
            Corregir lo que leyó la IA
          </Button>
        ) : (
          <div className="space-y-2" data-testid="comparison-edit">
            <p className="text-xs text-gray-500">La IA pudo equivocarse al leer. Corrige o quita líneas y guarda.</p>
            {draft.map((l, i) => (
              <div key={i} className="grid grid-cols-[1fr_4.5rem_6rem_2rem] items-center gap-2">
                <Input
                  aria-label={`Descripción de la línea ${i + 1}`}
                  value={l.description}
                  onChange={(e) => setDraft((d) => d.map((x, j) => (j === i ? { ...x, description: e.target.value } : x)))}
                />
                <Input
                  aria-label={`Cantidad de la línea ${i + 1}`}
                  type="number"
                  min={0}
                  value={l.quantity}
                  onChange={(e) => setDraft((d) => d.map((x, j) => (j === i ? { ...x, quantity: Number(e.target.value) } : x)))}
                />
                <Input
                  aria-label={`Precio de la línea ${i + 1}`}
                  type="number"
                  min={0}
                  value={l.unit_price}
                  onChange={(e) => setDraft((d) => d.map((x, j) => (j === i ? { ...x, unit_price: Number(e.target.value) } : x)))}
                />
                <button
                  type="button"
                  aria-label={`Quitar la línea ${i + 1}`}
                  className="text-gray-500"
                  onClick={() => setDraft((d) => d.filter((_, j) => j !== i))}
                >
                  ✕
                </button>
              </div>
            ))}
            <Button variant="ghost" onClick={() => setDraft((d) => [...d, { description: '', quantity: 1, unit_price: 0 }])}>
              + Agregar línea
            </Button>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <div className="flex gap-2">
              <Button variant="secondary" className="!w-auto flex-1" onClick={() => setEditing(false)}>
                Cancelar
              </Button>
              <Button
                className="!w-auto flex-1"
                disabled={save.isPending || draft.some((l) => !l.description.trim() || l.quantity <= 0)}
                onClick={() => save.mutate({ items: draft })}
              >
                Guardar y volver a comparar
              </Button>
            </div>
          </div>
        )}
      </section>
    </Card>
  )
}
