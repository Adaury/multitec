import { useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api, downloadFile } from '../lib/api'
import { Button, Modal } from './ui'

interface ImportRow {
  row: number
  action: 'create' | 'update' | 'skip' | 'error'
  name: string
  message: string
}

interface ImportResult {
  dry_run: boolean
  created: number
  updated: number
  skipped: number
  errors: number
  ignored_columns: string[]
  rows: ImportRow[]
}

const ACTION_LABEL: Record<ImportRow['action'], string> = {
  create: 'Nuevo',
  update: 'Actualiza',
  skip: 'Omitida',
  error: 'Error',
}

function errorText(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail
  return typeof detail === 'string' ? detail : fallback
}

/** Importación masiva de productos desde un CSV. Siempre se muestra primero una vista previa
 * (qué se crea, qué se actualiza, qué filas tienen error) y recién después se aplica. */
export function CatalogImport({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<ImportResult | null>(null)
  const [done, setDone] = useState<ImportResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function reset() {
    setFile(null)
    setPreview(null)
    setDone(null)
    setError(null)
    if (fileRef.current) fileRef.current.value = ''
  }

  async function send(dryRun: boolean) {
    if (!file) return
    setBusy(true)
    setError(null)
    try {
      const form = new FormData()
      form.append('file', file)
      const { data } = await api.post<ImportResult>(`/catalog/import?dry_run=${dryRun}`, form, { timeout: 120_000 })
      if (dryRun) setPreview(data)
      else {
        setDone(data)
        setPreview(null)
        queryClient.invalidateQueries({ queryKey: ['catalog'] })
      }
    } catch (err) {
      setError(errorText(err, 'No se pudo leer el archivo'))
    } finally {
      setBusy(false)
    }
  }

  const applicable = preview ? preview.created + preview.updated : 0
  const result = done ?? preview

  return (
    <Modal
      open={open}
      onClose={() => {
        reset()
        onClose()
      }}
      title="Importar productos"
    >
      <div className="space-y-4">
        <ol className="list-decimal space-y-1 pl-5 text-sm text-gray-600 dark:text-gray-400">
          <li>
            Descarga la plantilla y llénala en Excel (una fila por producto; solo <b>Nombre</b> y{' '}
            <b>Categoría</b> son obligatorios).
          </li>
          <li>
            Guárdala como <b>CSV</b> (Excel: Guardar como → "CSV UTF-8").
          </li>
          <li>Súbela aquí: primero ves una vista previa, y recién después se aplica.</li>
        </ol>
        <Button variant="secondary" onClick={() => downloadFile('/catalog/import-template', 'plantilla_catalogo.csv')}>
          ⬇ Descargar plantilla
        </Button>

        {!done && (
          <input
            ref={fileRef}
            type="file"
            accept=".csv,text/csv"
            aria-label="Archivo CSV"
            className="block w-full text-sm text-gray-600 file:mr-3 file:rounded-xl file:border-0 file:bg-brand-gray file:px-4 file:py-2 file:text-sm file:font-medium dark:text-gray-300 dark:file:bg-gray-800"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null)
              setPreview(null)
              setError(null)
            }}
          />
        )}

        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

        {!done && !preview && (
          <Button onClick={() => send(true)} disabled={!file || busy}>
            {busy ? 'Revisando…' : 'Revisar archivo'}
          </Button>
        )}

        {result && (
          <div className="space-y-3">
            <p role="status" className="text-sm font-medium text-gray-800 dark:text-gray-200">
              {done ? '✅ Importación terminada: ' : 'Vista previa: '}
              {result.created} nuevo(s) · {result.updated} actualizado(s) · {result.skipped} omitido(s) ·{' '}
              <span className={result.errors ? 'text-red-600 dark:text-red-400' : ''}>{result.errors} con error</span>
            </p>
            {result.ignored_columns.length > 0 && (
              <p className="text-xs text-amber-600 dark:text-amber-400">
                Columnas que no se reconocieron y se ignoraron: {result.ignored_columns.join(', ')}
              </p>
            )}
            <ul className="max-h-60 space-y-1 overflow-y-auto text-xs">
              {result.rows
                .filter((r) => r.action !== 'skip')
                .map((r) => (
                  <li
                    key={r.row}
                    className={`rounded-lg px-3 py-2 ${
                      r.action === 'error'
                        ? 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300'
                        : 'bg-brand-gray text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                    }`}
                  >
                    <b>Fila {r.row}</b> · {ACTION_LABEL[r.action]} · {r.name || '(sin nombre)'}
                    {r.message && <span className="block opacity-80">{r.message}</span>}
                  </li>
                ))}
            </ul>
          </div>
        )}

        {preview && (
          <div className="flex flex-col gap-2">
            <Button onClick={() => send(false)} disabled={busy || applicable === 0}>
              {busy ? 'Importando…' : `Importar ${applicable} producto(s)`}
            </Button>
            {preview.errors > 0 && applicable > 0 && (
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Las filas con error no se importan; corrígelas en el archivo y vuelve a subirlo.
              </p>
            )}
            <Button variant="ghost" onClick={reset} disabled={busy}>
              Elegir otro archivo
            </Button>
          </div>
        )}

        {done && (
          <Button
            onClick={() => {
              reset()
              onClose()
            }}
          >
            Listo
          </Button>
        )}
      </div>
    </Modal>
  )
}
