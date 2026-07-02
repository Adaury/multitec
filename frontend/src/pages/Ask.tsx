import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { AskResponse, Project } from '../lib/types'
import { Button, Card, Field, Textarea } from '../components/ui'

export function Ask() {
  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => (await api.get<Project[]>('/projects')).data,
  })

  const [projectId, setProjectId] = useState('')
  const [question, setQuestion] = useState('')
  const [error, setError] = useState<string | null>(null)

  const ask = useMutation({
    mutationFn: async () =>
      (await api.post<AskResponse>('/ai/ask', { project_id: Number(projectId), question })).data,
    onSuccess: () => setError(null),
    onError: (err: any) => setError(err?.response?.data?.detail ?? 'Error al consultar la IA'),
  })

  return (
    <div className="space-y-4 py-4">
      <h1 className="text-xl font-semibold text-gray-900">Preguntar a la IA</h1>
      <p className="text-sm text-gray-500">
        Elige un proyecto y pregunta en lenguaje natural sobre su expediente completo.
      </p>

      <Card className="space-y-3">
        <Field label="Proyecto">
          <select
            className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
          >
            <option value="">Selecciona un proyecto…</option>
            {projects?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.code}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Pregunta">
          <Textarea
            rows={3}
            placeholder="Ej. ¿Cuántas cámaras se cotizaron y cuál es el estado del proyecto?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
        </Field>
        <Button onClick={() => ask.mutate()} disabled={ask.isPending || !projectId || !question}>
          {ask.isPending ? 'Consultando…' : '🤖 Preguntar'}
        </Button>
      </Card>

      {error && (
        <Card>
          <p className="text-sm text-red-600">{error}</p>
        </Card>
      )}

      {ask.data && (
        <Card>
          <p className="whitespace-pre-line text-sm text-gray-800">{ask.data.answer}</p>
        </Card>
      )}
    </div>
  )
}
