import { create } from 'zustand'
import { api, apiErrorMessage } from './api'
import { queryClient } from './queryClient'
import type { GenerateFromSurveyOut } from './types'

export interface GenerationJob {
  projectId: number
  label: string
  status: 'running' | 'done' | 'error'
  result?: GenerateFromSurveyOut
  error?: string
  /** Cuándo terminó en el servidor; sirve para no volver a mostrar un aviso que ya se cerró. */
  finishedAt?: string | null
}

/** Lo que responde el servidor (services/generation_jobs.py). */
interface ServerJob {
  project_id: number
  label?: string
  status: 'none' | 'running' | 'done' | 'error'
  finished_at?: string | null
  result?: GenerateFromSurveyOut | null
  error?: string | null
}

interface GenerationState {
  jobs: Record<number, GenerationJob>
  dismiss: (projectId: number) => void
}

const SEEN_KEY = 'multitec_gen_seen'

function readSeen(): Record<string, string> {
  try {
    return JSON.parse(localStorage.getItem(SEEN_KEY) ?? '{}') as Record<string, string>
  } catch {
    return {}
  }
}

function markSeen(projectId: number, finishedAt: string | null | undefined) {
  if (!finishedAt) return
  try {
    localStorage.setItem(SEEN_KEY, JSON.stringify({ ...readSeen(), [projectId]: finishedAt }))
  } catch {
    // sin almacenamiento: el aviso puede volver a aparecer una vez, nada más
  }
}

export const useGenerationStore = create<GenerationState>((set, get) => ({
  jobs: {},
  dismiss: (projectId) => {
    markSeen(projectId, get().jobs[projectId]?.finishedAt)
    set((state) => {
      const { [projectId]: _removed, ...rest } = state.jobs
      return { jobs: rest }
    })
  },
}))

function setJob(job: GenerationJob) {
  useGenerationStore.setState((state) => ({ jobs: { ...state.jobs, [job.projectId]: job } }))
}

const POLL_MS = 3000
const WAIT_NO_JOB_POLLS = 4 // consultas seguidas sin que el servidor conozca el trabajo antes de darlo por perdido

type Waiter = { resolve: (data: GenerateFromSurveyOut) => void; reject: (error: Error) => void }
const waiters = new Map<number, Waiter[]>()
const polling = new Set<number>()

function settle(projectId: number, outcome: { data: GenerateFromSurveyOut } | { error: Error }) {
  const list = waiters.get(projectId) ?? []
  waiters.delete(projectId)
  for (const w of list) {
    if ('data' in outcome) w.resolve(outcome.data)
    else w.reject(outcome.error)
  }
}

function onDone(projectId: number, label: string, data: GenerateFromSurveyOut, finishedAt: string | null | undefined) {
  for (const key of ['quotes', 'budgets', 'engineering']) {
    queryClient.invalidateQueries({ queryKey: [key, projectId] })
  }
  queryClient.invalidateQueries({ queryKey: ['projects'] })
  if (data.engineering_pending) {
    // El borrador llega solo; se refresca la pestaña Ingeniería un par de veces mientras tanto.
    for (const delay of [45_000, 90_000]) {
      window.setTimeout(() => queryClient.invalidateQueries({ queryKey: ['engineering', projectId] }), delay)
    }
  }
  setJob({ projectId, label, status: 'done', result: data, finishedAt })
  settle(projectId, { data })
}

const GENERIC_ERROR = 'No se pudo generar la cotización. Tu levantamiento quedó guardado; intenta de nuevo.'

/** Consulta al servidor hasta que la generación termine. Un fallo de red mientras tanto (la página suspendida por
 * el iPhone, sin señal) NO es un error de la IA: simplemente se vuelve a preguntar. */
function pollUntilDone(projectId: number, label: string, expectStart = false) {
  if (polling.has(projectId)) return
  polling.add(projectId)
  let missing = 0

  const tick = async () => {
    try {
      const { data } = await api.get<ServerJob>(`/projects/${projectId}/generate-from-survey/status`)
      if (data.status === 'running') {
        missing = 0
        setJob({ ...(useGenerationStore.getState().jobs[projectId] ?? { projectId, label }), projectId, label, status: 'running' })
      } else if (data.status === 'done' && data.result) {
        polling.delete(projectId)
        onDone(projectId, label, data.result, data.finished_at)
        return
      } else if (data.status === 'error') {
        polling.delete(projectId)
        const message = data.error ?? GENERIC_ERROR
        setJob({ projectId, label, status: 'error', error: message, finishedAt: data.finished_at })
        settle(projectId, { error: new Error(message) })
        return
      } else {
        // "none": el servidor no conoce el trabajo. Puede ser que aún no haya arrancado (la petición de inicio se cortó)
        // o que el servidor se reinició a mitad. Se da un margen y luego se explica.
        missing += 1
        if (missing >= (expectStart ? WAIT_NO_JOB_POLLS : 2)) {
          polling.delete(projectId)
          const message = expectStart
            ? 'No se pudo iniciar la generación (¿sin conexión?). Revisa tu señal e intenta de nuevo.'
            : 'El servidor se reinició mientras armaba la cotización. Intenta de nuevo: no se creó nada duplicado.'
          setJob({ projectId, label, status: 'error', error: message })
          settle(projectId, { error: new Error(message) })
          return
        }
      }
    } catch (error) {
      // Una respuesta del servidor con error de sesión o permisos sí es definitiva; la falta de respuesta, no.
      const status = (error as { response?: { status?: number } }).response?.status
      if (status === 403 || status === 404) {
        polling.delete(projectId)
        const message = apiErrorMessage(error, GENERIC_ERROR)
        setJob({ projectId, label, status: 'error', error: message })
        settle(projectId, { error: new Error(message) })
        return
      }
    }
    window.setTimeout(tick, POLL_MS)
  }
  window.setTimeout(tick, expectStart ? 1500 : 500)
}

/** Genera presupuesto + cotización con IA a partir del levantamiento. El trabajo corre en el SERVIDOR: la pantalla
 * solo lo arranca y consulta el avance. Si el técnico cambia de pantalla, de aplicación o cierra el navegador, la
 * generación sigue; al volver (`rehydrateJobs`) la barra `GenerationBanner` muestra el avance o el resultado. */
export function startGeneration(
  projectId: number,
  label: string,
  options: { backgroundEngineering?: boolean } = {},
): Promise<GenerateFromSurveyOut> {
  return new Promise<GenerateFromSurveyOut>((resolve, reject) => {
    const list = waiters.get(projectId) ?? []
    list.push({ resolve, reject })
    waiters.set(projectId, list)

    // Un segundo toque (o volver a la pantalla) se une a la que ya está en marcha: no crea otra cotización.
    if (polling.has(projectId)) return

    setJob({ projectId, label, status: 'running' })
    const query = options.backgroundEngineering ? '?background_engineering=true' : ''
    api
      .post<ServerJob>(`/projects/${projectId}/generate-from-survey/start${query}`)
      .then(() => pollUntilDone(projectId, label))
      .catch((error) => {
        if ((error as { response?: unknown }).response) {
          // El servidor contestó con un error (permisos, proyecto no encontrado, cuota de IA...): es definitivo.
          const message = apiErrorMessage(error, GENERIC_ERROR)
          setJob({ projectId, label, status: 'error', error: message })
          settle(projectId, { error: new Error(message) })
        } else {
          // Sin respuesta: la petición pudo haberse cortado después de llegar. Se consulta antes de rendirse.
          pollUntilDone(projectId, label, true)
        }
      })
  })
}

/** Al abrir la app o volver a ella: recupera del servidor las generaciones en marcha o terminadas, para mostrar el
 * avance o el resultado aunque la página se haya recargado o el iPhone la haya suspendido. */
export async function rehydrateJobs(): Promise<void> {
  try {
    const { data } = await api.get<ServerJob[]>('/ai/generation-jobs')
    const seen = readSeen()
    const current = useGenerationStore.getState().jobs
    for (const job of data) {
      const known = current[job.project_id]
      const label = job.label ?? known?.label ?? 'proyecto'
      if (job.status === 'running') {
        if (!known || known.status !== 'running') setJob({ projectId: job.project_id, label, status: 'running' })
        pollUntilDone(job.project_id, label)
      } else if (job.finished_at && seen[job.project_id] === job.finished_at) {
        continue // ya se vio y se cerró
      } else if (job.status === 'done' && job.result && known?.status !== 'done') {
        onDone(job.project_id, label, job.result, job.finished_at)
      } else if (job.status === 'error' && known?.status !== 'error') {
        setJob({ projectId: job.project_id, label, status: 'error', error: job.error ?? GENERIC_ERROR, finishedAt: job.finished_at })
      }
    }
  } catch {
    // sin señal o sesión vencida: se reintenta la próxima vez que la app se vea
  }
}

// Al volver a la app (iPhone) o recuperar la señal, se pregunta de nuevo al servidor sin esperar al siguiente tick.
if (typeof document !== 'undefined') {
  const refreshIfVisible = () => {
    if (document.visibilityState === 'visible') void rehydrateJobs()
  }
  document.addEventListener('visibilitychange', refreshIfVisible)
  window.addEventListener('online', refreshIfVisible)
}
