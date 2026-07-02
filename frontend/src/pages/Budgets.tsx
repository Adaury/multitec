import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import type { Budget, Project } from '../lib/types'
import { formatDOP } from '../lib/format'
import { Card } from '../components/ui'

export function Budgets() {
  const { data: budgets, isLoading } = useQuery({
    queryKey: ['all-budgets'],
    queryFn: async () => (await api.get<Budget[]>('/budgets')).data,
  })

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => (await api.get<Project[]>('/projects')).data,
  })

  function projectCode(projectId: number) {
    return projects?.find((p) => p.id === projectId)?.code ?? `#${projectId}`
  }

  return (
    <div className="space-y-4 py-4">
      <h1 className="text-xl font-semibold text-gray-900">Presupuestos</h1>

      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}

      <div className="space-y-3">
        {budgets?.map((budget) => (
          <Link key={budget.id} to={`/proyectos/${budget.project_id}`}>
            <Card className="active:scale-[0.98]">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">{budget.code}</p>
                  <p className="text-xs text-gray-400">Proyecto {projectCode(budget.project_id)}</p>
                </div>
                <p className="text-sm font-semibold text-gray-800">{formatDOP(budget.total)}</p>
              </div>
              {budget.notes && <p className="mt-1 text-sm text-gray-500">{budget.notes}</p>}
            </Card>
          </Link>
        ))}
        {budgets?.length === 0 && <p className="text-sm text-gray-500">Aún no hay presupuestos.</p>}
      </div>
    </div>
  )
}
