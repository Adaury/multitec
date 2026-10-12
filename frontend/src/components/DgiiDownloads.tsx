import { useState } from 'react'
import { downloadFile } from '../lib/api'
import { Button } from './ui'

type Form = '606' | '607' | '608'

/** Con format=txt, un RNC de empresa faltante vuelve como JSON dentro de un blob: se lee para
 * mostrar el motivo real en vez de un error genérico. */
async function errorMessage(err: unknown): Promise<string> {
  const data = (err as { response?: { data?: unknown } }).response?.data
  if (data instanceof Blob) {
    try {
      const parsed = JSON.parse(await data.text()) as { detail?: string }
      if (parsed.detail) return parsed.detail
    } catch {
      // cae al mensaje genérico
    }
  }
  return 'No se pudo generar el archivo.'
}

/** Descargas de un formato de la DGII: el CSV sirve para revisar en Excel; el .txt es el archivo
 * de envío (encabezado FORMATO|RNC|PERIODO|CANTIDAD y un registro por línea). */
export function DgiiDownloads({ form, year, month }: { form: Form; year: number; month: number }) {
  const [error, setError] = useState<string | null>(null)
  const period = `${year}${String(month).padStart(2, '0')}`

  const run = async (format: 'csv' | 'txt') => {
    setError(null)
    const path = `/reports/dgii-${form}?year=${year}&month=${month}&format=${format}`
    const filename = format === 'txt' ? `DGII_F_${form}_${period}.txt` : `${form}_${period}.csv`
    try {
      await downloadFile(path, filename)
    } catch (err) {
      setError(await errorMessage(err))
    }
  }

  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-gray-500 dark:text-gray-400">Reporte {form}</p>
      <div className="grid grid-cols-2 gap-3">
        <Button variant="secondary" onClick={() => run('csv')}>
          Revisar (CSV)
        </Button>
        <Button variant="secondary" onClick={() => run('txt')}>
          Archivo DGII (.txt)
        </Button>
      </div>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </div>
  )
}
