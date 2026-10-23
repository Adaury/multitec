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
}

interface GenerationState {
  jobs: Record<number, GenerationJob>
  dismiss: (projectId: number) => void
}

export const useGenerationStore = create<GenerationState>((set) => ({
  jobs: {},
  dismiss: (projectId) =>
    set((state) => {
      const { [projectId]: _removed, ...rest } = state.jobs
      return { jobs: rest }
    }),
}))

function setJob(job: GenerationJob) {
  useGenerationStore.setState((state) => ({ jobs: { ...state.jobs, [job.projectId]: job } }))
}

// Una sola generación por proyecto a la vez: un segundo toque (o volver a la pantalla) se une a la
// que ya está en marcha en vez de crear otra cotización.
const inFlight = new Map<number, Promise<GenerateFromSurveyOut>>()

/** Genera presupuesto + cotización con IA a partir del levantamiento. Vive fuera de los
 * componentes: si el técnico cambia de pantalla (tickets, inicio…) la generación sigue, la barra
 * `GenerationBanner` lo muestra y, al terminar, las listas se refrescan solas. */
export function startGeneration(
  projectId: number,
  label: string,
  options: { backgroundEngineering?: boolean } = {},
): Promise<GenerateFromSurveyOut> {
  const existing = inFlight.get(projectId)
  if (existing) return existing

  setJob({ projectId, label, status: 'running' })
  const query = options.backgroundEngineering ? '?background_engineering=true' : ''
  const promise = api
    .post<GenerateFromSurveyOut>(`/projects/${projectId}/generate-from-survey${query}`)
    .then((response) => {
      const data = response.data
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
      setJob({ projectId, label, status: 'done', result: data })
      return data
    })
    .catch((error) => {
      setJob({
        projectId,
        label,
        status: 'error',
        error: apiErrorMessage(error, 'No se pudo generar la cotización. Tu levantamiento quedó guardado; intenta de nuevo.'),
      })
      throw error
    })
    .finally(() => inFlight.delete(projectId))
  inFlight.set(projectId, promise)
  return promise
}
