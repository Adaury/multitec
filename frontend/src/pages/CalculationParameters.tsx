import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { CalculationParameter } from '../lib/types'
import { useAuthStore } from '../lib/authStore'
import { Badge, Button, Card, Field, Input } from '../components/ui'

export function CalculationParameters() {
  const currentUser = useAuthStore((s) => s.user)
  const isAdmin = currentUser?.role === 'admin'
  const queryClient = useQueryClient()

  const { data: parameters, isLoading } = useQuery({
    queryKey: ['calculation-parameters'],
    queryFn: async () => (await api.get<CalculationParameter[]>('/calculation-parameters')).data,
    enabled: isAdmin,
  })

  if (!isAdmin) {
    return (
      <div className="py-4">
        <Card>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Solo un administrador puede configurar los parámetros de cálculo.
          </p>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-4 py-4 md:space-y-6 md:py-8">
      <h1 className="text-xl font-semibold text-gray-900 md:text-2xl dark:text-gray-100">Parámetros de cálculo</h1>
      <p className="text-sm text-gray-500 dark:text-gray-400">
        Valores que usa la IA (Motor 5) al generar presupuestos automáticamente — margen de
        desperdicio de cable, tarifa de mano de obra, estimación de almacenamiento. Un
        parámetro sin configurar usa su valor por defecto; una regla técnica de tipo
        "Ajustar cálculo" puede subirlo para un producto específico sin tocar este default.
      </p>

      {isLoading && <p className="text-sm text-gray-500">Cargando…</p>}

      <div className="grid gap-3 md:grid-cols-2">
        {parameters?.map((parameter) => (
          <ParameterCard
            key={parameter.key}
            parameter={parameter}
            onSaved={() => queryClient.invalidateQueries({ queryKey: ['calculation-parameters'] })}
          />
        ))}
      </div>
    </div>
  )
}

function ParameterCard({ parameter, onSaved }: { parameter: CalculationParameter; onSaved: () => void }) {
  const [value, setValue] = useState(String(parameter.value))
  const [error, setError] = useState<string | null>(null)

  const save = useMutation({
    mutationFn: async () =>
      (await api.put(`/calculation-parameters/${parameter.key}`, { value: Number(value) })).data,
    onSuccess: () => {
      setError(null)
      onSaved()
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? 'No se pudo guardar'),
  })

  const dirty = value !== '' && Number(value) !== parameter.value

  return (
    <Card className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <p className="font-mono text-xs text-gray-400">{parameter.key}</p>
        <Badge tone={parameter.is_default ? 'gray' : 'green'}>
          {parameter.is_default ? 'Valor por defecto' : 'Configurado'}
        </Badge>
      </div>
      <p className="text-sm text-gray-600 dark:text-gray-400">{parameter.description}</p>
      <Field label="Valor">
        <Input type="number" step="0.0001" value={value} onChange={(e) => setValue(e.target.value)} />
      </Field>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      <Button onClick={() => save.mutate()} disabled={save.isPending || !dirty}>
        {save.isPending ? 'Guardando…' : 'Guardar'}
      </Button>
      {parameter.updated_at && (
        <p className="text-xs text-gray-400">
          Última actualización: {new Date(parameter.updated_at).toLocaleString('es-DO')}
        </p>
      )}
    </Card>
  )
}
