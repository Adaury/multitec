import { useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Download, FileSpreadsheet, Siren, Wrench } from 'lucide-react'
import { api, downloadFile } from '../lib/api'
import { Button, Modal } from './ui'

interface ImportRow {
  row: number
  action: 'create' | 'update' | 'skip' | 'error'
  name: string
  message: string
  file?: string
}

interface ImportResult {
  dry_run: boolean
  created: number
  updated: number
  skipped: number
  errors: number
  ignored_columns: string[]
  new_categories?: string[]
  files?: string[]
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

// Plantillas listas para llenar: la general (con filas de ejemplo) y listas de materiales de alarma y de
// ferretería con los nombres y las categorías ya puestos (solo falta el precio).
const KITS = [
  { kind: 'alarma', label: 'Materiales de alarma', icon: Siren, file: 'plantilla_materiales_alarma' },
  { kind: 'ferreteria', label: 'Materiales de ferretería', icon: Wrench, file: 'plantilla_materiales_ferreteria' },
] as const

/** Importación masiva de productos desde uno o varios archivos CSV o Excel. Siempre se muestra primero una
 * vista previa (qué se crea, qué se actualiza, qué filas tienen error) y recién después se aplica. */
export function CatalogImport({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<File[]>([])
  // Apagado por defecto: un nombre mal escrito no debe crear una categoría nueva sin que nadie lo note.
  const [createCategories, setCreateCategories] = useState(false)
  const [preview, setPreview] = useState<ImportResult | null>(null)
  const [done, setDone] = useState<ImportResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function reset() {
    setFiles([])
    setPreview(null)
    setDone(null)
    setError(null)
    if (fileRef.current) fileRef.current.value = ''
  }

  async function send(dryRun: boolean, withCategories = createCategories) {
    if (files.length === 0) return
    setBusy(true)
    setError(null)
    try {
      const form = new FormData()
      for (const f of files) form.append('files', f)
      const { data } = await api.post<ImportResult>(
        `/catalog/import?dry_run=${dryRun}&create_categories=${withCategories}`,
        form,
        { timeout: 120_000 },
      )
      if (dryRun) setPreview(data)
      else {
        setDone(data)
        setPreview(null)
        queryClient.invalidateQueries({ queryKey: ['catalog'] })
        queryClient.invalidateQueries({ queryKey: ['categories'] })
      }
    } catch (err) {
      setError(errorText(err, 'No se pudo leer el archivo'))
    } finally {
      setBusy(false)
    }
  }

  const applicable = preview ? preview.created + preview.updated : 0
  const missingCategories =
    !createCategories && (preview?.rows.some((r) => r.action === 'error' && /categoría .* no existe/i.test(r.message)) ?? false)
  const result = done ?? preview
  const several = (result?.files?.length ?? 0) > 1

  return (
    <Modal
      open={open}
      onClose={() => {
        reset()
        onClose()
      }}
      title="Importar productos"
      wide
    >
      <div className="space-y-4">
        <ol className="list-decimal space-y-1 pl-5 text-sm text-gray-600 dark:text-gray-400">
          <li>
            Descarga una plantilla y llénala en Excel (una fila por producto; solo <b>Nombre</b> y <b>Categoría</b>{' '}
            son obligatorios).
          </li>
          <li>
            Súbela tal cual en <b>Excel (.xlsx)</b> o como <b>CSV</b>. Puedes subir <b>varios archivos a la vez</b>.
          </li>
          <li>Primero ves una vista previa, y recién después se aplica.</li>
        </ol>

        <div className="grid gap-2 sm:grid-cols-3">
          <div className="rounded-2xl bg-brand-gray p-3 dark:bg-gray-800">
            <p className="flex items-center gap-1.5 text-sm font-semibold text-gray-800 dark:text-gray-100">
              <FileSpreadsheet className="h-4 w-4 text-brand-blue" aria-hidden="true" /> General
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              <button
                type="button"
                onClick={() => downloadFile('/catalog/import-template?kind=general&format=csv', 'plantilla_catalogo.csv')}
                className="rounded-full bg-white px-3 py-1 text-xs font-medium text-gray-700 ring-1 ring-black/5 hover:bg-gray-50 dark:bg-gray-900 dark:text-gray-200"
              >
                ⬇ Descargar plantilla
              </button>
              <button
                type="button"
                onClick={() => downloadFile('/catalog/import-template?kind=general&format=xlsx', 'plantilla_catalogo.xlsx')}
                className="rounded-full bg-white px-3 py-1 text-xs font-medium text-gray-700 ring-1 ring-black/5 hover:bg-gray-50 dark:bg-gray-900 dark:text-gray-200"
              >
                Excel
              </button>
            </div>
          </div>
          {KITS.map((kit) => (
            <div key={kit.kind} className="rounded-2xl bg-brand-gray p-3 dark:bg-gray-800">
              <p className="flex items-center gap-1.5 text-sm font-semibold text-gray-800 dark:text-gray-100">
                <kit.icon className="h-4 w-4 text-brand-blue" aria-hidden="true" /> {kit.label}
              </p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {(['xlsx', 'csv'] as const).map((format) => (
                  <button
                    key={format}
                    type="button"
                    onClick={() => downloadFile(`/catalog/import-template?kind=${kit.kind}&format=${format}`, `${kit.file}.${format}`)}
                    className="rounded-full bg-white px-3 py-1 text-xs font-medium text-gray-700 ring-1 ring-black/5 hover:bg-gray-50 dark:bg-gray-900 dark:text-gray-200"
                    aria-label={`Descargar lista de ${kit.label.toLowerCase()} en ${format === 'xlsx' ? 'Excel' : 'CSV'}`}
                  >
                    {format === 'xlsx' ? '⬇ Excel' : 'CSV'}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={() => downloadFile('/catalog/export?format=xlsx', 'catalogo.xlsx')}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-brand-blue hover:underline"
        >
          <Download className="h-4 w-4" aria-hidden="true" /> Descargar todo mi catálogo en Excel (para editarlo y volver a subirlo)
        </button>

        {!done && (
          <>
            <input
              ref={fileRef}
              type="file"
              multiple
              accept=".csv,text/csv,.xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              aria-label="Archivo CSV o Excel (puedes elegir varios)"
              className="block w-full text-sm text-gray-600 file:mr-3 file:rounded-xl file:border-0 file:bg-brand-gray file:px-4 file:py-2 file:text-sm file:font-medium dark:text-gray-300 dark:file:bg-gray-800"
              onChange={(e) => {
                setFiles(Array.from(e.target.files ?? []))
                setPreview(null)
                setError(null)
              }}
            />
            {files.length > 1 && (
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {files.length} archivos: {files.map((f) => f.name).join(', ')}
              </p>
            )}
            <label className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
              <input
                type="checkbox"
                checked={createCategories}
                onChange={(e) => {
                  setCreateCategories(e.target.checked)
                  setPreview(null)
                }}
                className="mt-0.5 h-4 w-4 rounded"
              />
              Crear las categorías que no existan (por ejemplo «Alarmas &gt; Sirenas» o «Ferretería &gt; Anclajes»)
            </label>
          </>
        )}

        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

        {!done && !preview && (
          <Button onClick={() => send(true)} disabled={files.length === 0 || busy}>
            {busy ? 'Revisando…' : files.length > 1 ? `Revisar ${files.length} archivos` : 'Revisar archivo'}
          </Button>
        )}

        {result && (
          <div className="space-y-3">
            <p role="status" className="text-sm font-medium text-gray-800 dark:text-gray-200">
              {done ? '✅ Importación terminada: ' : 'Vista previa: '}
              {result.created} nuevo(s) · {result.updated} actualizado(s) · {result.skipped} omitido(s) ·{' '}
              <span className={result.errors ? 'text-red-600 dark:text-red-400' : ''}>{result.errors} con error</span>
            </p>
            {(result.new_categories?.length ?? 0) > 0 && (
              <p className="text-xs text-emerald-700 dark:text-emerald-400">
                {done ? 'Categorías creadas' : 'Se crearán estas categorías'}: {result.new_categories!.join(', ')}
              </p>
            )}
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
                    key={`${r.file ?? ''}-${r.row}`}
                    className={`rounded-lg px-3 py-2 ${
                      r.action === 'error'
                        ? 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300'
                        : 'bg-brand-gray text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                    }`}
                  >
                    <b>
                      {several && r.file ? `${r.file} · ` : ''}Fila {r.row}
                    </b>{' '}
                    · {ACTION_LABEL[r.action]} · {r.name || '(sin nombre)'}
                    {r.message && <span className="block opacity-80">{r.message}</span>}
                  </li>
                ))}
            </ul>
          </div>
        )}

        {preview && missingCategories && (
          <div className="rounded-2xl bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
            <p>Hay categorías que todavía no existen en tu catálogo.</p>
            <Button
              variant="secondary"
              className="mt-2 !w-auto !py-2 px-4 text-sm"
              disabled={busy}
              onClick={() => {
                setCreateCategories(true)
                void send(true, true)
              }}
            >
              Crearlas y revisar de nuevo
            </Button>
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
              Elegir otros archivos
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
