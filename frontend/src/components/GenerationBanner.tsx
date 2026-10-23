import { Link } from 'react-router-dom'
import { useGenerationStore } from '../lib/generationStore'
import { formatDOP } from '../lib/format'

/** Barra fija con las cotizaciones que la IA está armando (o acaba de armar). Se ve en todas las
 * pantallas: el técnico puede ir a tickets, al inicio o a otro proyecto sin perder de vista que la
 * IA sigue trabajando, y al terminar toca para abrir la cotización. */
export function GenerationBanner() {
  const jobs = useGenerationStore((state) => state.jobs)
  const dismiss = useGenerationStore((state) => state.dismiss)
  const list = Object.values(jobs)
  if (list.length === 0) return null

  return (
    <div className="space-y-2 px-5 pt-2 md:px-10" role="status" aria-live="polite">
      {list.map((job) => (
        <div
          key={job.projectId}
          className="flex items-center gap-3 rounded-2xl bg-blue-50 px-4 py-3 text-sm ring-1 ring-blue-100 dark:bg-blue-950 dark:ring-blue-900"
        >
          <div className="min-w-0 flex-1">
            {job.status === 'running' && (
              <>
                <p className="font-medium text-gray-900 dark:text-gray-100">🤖 Armando la cotización de {job.label}…</p>
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  Puedes seguir usando la app: la IA termina sola (1 a 3 minutos) y se agrega a la lista.
                </p>
              </>
            )}
            {job.status === 'done' && job.result && (
              <>
                <p className="font-medium text-gray-900 dark:text-gray-100">
                  ✅ Cotización lista: {job.label} · {formatDOP(job.result.quote.total)}
                </p>
                <Link
                  to={`/proyectos/${job.projectId}?tab=cotizacion`}
                  onClick={() => dismiss(job.projectId)}
                  className="text-xs font-medium text-brand-blue underline"
                >
                  Ver y ajustar la cotización
                </Link>
              </>
            )}
            {job.status === 'error' && (
              <>
                <p className="font-medium text-red-600 dark:text-red-400">No se pudo armar la cotización de {job.label}</p>
                <p className="text-xs text-gray-600 dark:text-gray-400">{job.error}</p>
              </>
            )}
          </div>
          {job.status !== 'running' && (
            <button
              type="button"
              aria-label="Cerrar aviso"
              onClick={() => dismiss(job.projectId)}
              className="px-2 text-gray-400"
            >
              ✕
            </button>
          )}
        </div>
      ))}
    </div>
  )
}
