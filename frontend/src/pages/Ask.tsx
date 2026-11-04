import { useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Bot, Lightbulb, Send } from 'lucide-react'
import { api, apiErrorMessage } from '../lib/api'
import type { AskResponse, Client, Project } from '../lib/types'
import { Card, Field } from '../components/ui'

const ALL_PROJECTS = '__all__'

// Preguntas de ejemplo: un toque las escribe en la caja.
const EXAMPLES_ALL = [
  '¿Qué proyectos tienen cámaras IP cotizadas?',
  '¿Qué clientes tienen proyectos en ejecución?',
  '¿En qué proyectos se usó un NVR de 8 canales?',
]
const EXAMPLES_ONE = [
  '¿Cuántas cámaras se cotizaron y cuál es el estado del proyecto?',
  '¿Qué materiales faltan por comprar?',
  '¿Qué se anotó en la bitácora?',
]

export function Ask() {
  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => (await api.get<Project[]>('/projects')).data,
  })
  const { data: clients } = useQuery({
    queryKey: ['clients'],
    queryFn: async () => (await api.get<Client[]>('/clients')).data,
  })
  const clientNames = useMemo(() => new Map((clients ?? []).map((c) => [c.id, c.name])), [clients])

  const [projectId, setProjectId] = useState(ALL_PROJECTS)
  const [question, setQuestion] = useState('')
  const [error, setError] = useState<string | null>(null)

  const ask = useMutation({
    mutationFn: async () =>
      (
        await api.post<AskResponse>('/ai/ask', {
          project_id: projectId === ALL_PROJECTS ? null : Number(projectId),
          question,
        })
      ).data,
    onSuccess: () => setError(null),
    onError: (err: unknown) => setError(apiErrorMessage(err, 'Error al consultar la IA')),
  })

  const examples = projectId === ALL_PROJECTS ? EXAMPLES_ALL : EXAMPLES_ONE
  const canAsk = !ask.isPending && !!projectId && !!question.trim()

  return (
    <div className="mx-auto w-full max-w-3xl space-y-4 py-4 md:space-y-6 md:py-8">
      <h1 className="text-xl font-semibold text-gray-900 sr-only dark:text-gray-100">Preguntar a la IA</h1>
      <p className="text-center text-sm text-gray-500 dark:text-gray-400">
        Pregunta como le hablarías a un compañero. Elige un proyecto para preguntar sobre él, o «Todos los proyectos» para
        buscar en todo el historial.
      </p>

      <Card className="space-y-4 md:p-6">
        <Field label="Proyecto">
          <select
            className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
          >
            <option value={ALL_PROJECTS}>🔎 Todos los proyectos</option>
            {projects?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.code}
                {clientNames.get(p.client_id) ? ` · ${clientNames.get(p.client_id)}` : ''}
              </option>
            ))}
          </select>
        </Field>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            if (canAsk) ask.mutate()
          }}
        >
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-gray-600 dark:text-gray-400">Pregunta</span>
            <div className="relative">
              <textarea
                rows={3}
                placeholder="Ej. ¿Cuántas cámaras se cotizaron y cuál es el estado del proyecto?"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  // Enter envía; Shift+Enter hace un salto de línea.
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    if (canAsk) ask.mutate()
                  }
                }}
                className="w-full resize-none rounded-2xl border border-gray-200 bg-white px-4 py-3 pr-16 text-base text-gray-900 outline-none focus:border-brand-blue focus:ring-2 focus:ring-brand-blue/20 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
              />
              <button
                type="submit"
                disabled={!canAsk}
                aria-label="Preguntar"
                className="absolute bottom-3 right-3 flex h-11 w-11 items-center justify-center rounded-full bg-brand-blue text-white shadow-sm transition hover:bg-brand-blue-dark active:scale-95 disabled:opacity-40"
              >
                <Send className="h-5 w-5" aria-hidden="true" />
              </button>
            </div>
          </label>
        </form>
        <div className="space-y-2">
          <p className="flex items-center gap-1.5 text-xs font-medium text-gray-500 dark:text-gray-400">
            <Lightbulb className="h-4 w-4" aria-hidden="true" /> Prueba con
          </p>
          <div className="flex flex-wrap gap-2">
            {examples.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => setQuestion(example)}
                className="rounded-full bg-brand-gray px-3 py-1.5 text-left text-sm text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {ask.isPending && (
        <Card className="flex items-center gap-3">
          <Bot className="h-6 w-6 animate-pulse text-fuchsia-600" aria-hidden="true" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Consultando…</p>
        </Card>
      )}

      {error && (
        <Card>
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </Card>
      )}

      {ask.data && !ask.isPending && (
        <Card className="flex gap-3 md:p-6">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-fuchsia-50 text-fuchsia-700 dark:bg-fuchsia-950 dark:text-fuchsia-300">
            <Bot className="h-6 w-6" aria-hidden="true" />
          </span>
          <div className="min-w-0 space-y-2">
            {ask.data.projects.length > 0 && (
              <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Basado en: {ask.data.projects.join(', ')}</p>
            )}
            <p className="whitespace-pre-line text-base text-gray-800 dark:text-gray-200">{ask.data.answer}</p>
          </div>
        </Card>
      )}
    </div>
  )
}
