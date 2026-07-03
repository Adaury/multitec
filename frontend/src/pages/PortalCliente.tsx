import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { PROJECT_STATUS_LABELS, QUOTE_STATUS_LABELS, type PublicProject } from '../lib/types'
import { formatDOP } from '../lib/format'
import { Badge, Card } from '../components/ui'

export function PortalCliente() {
  const { token } = useParams()
  const [project, setProject] = useState<PublicProject | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) return
    fetch(`/api/public/projects/${token}`)
      .then(async (res) => {
        if (!res.ok) throw new Error('not-found')
        return res.json()
      })
      .then((data) => setProject(data))
      .catch(() => setError('Este enlace no es válido o fue desactivado.'))
      .finally(() => setLoading(false))
  }, [token])

  return (
    <div className="mx-auto min-h-screen max-w-lg bg-brand-bg px-5 py-6">
      <p className="text-lg font-semibold text-gray-900">Multitec</p>
      <p className="mb-6 text-xs text-gray-500">Portal de seguimiento del proyecto</p>

      {loading && <p className="text-sm text-gray-500">Cargando…</p>}

      {error && (
        <Card>
          <p className="text-sm text-red-600">{error}</p>
        </Card>
      )}

      {project && (
        <div className="space-y-4">
          <Card>
            <div className="flex items-center justify-between">
              <p className="text-lg font-semibold text-gray-900">{project.code}</p>
              <Badge>{PROJECT_STATUS_LABELS[project.status] ?? project.status}</Badge>
            </div>
            <p className="mt-1 text-sm text-gray-500">{project.client_name}</p>
            <p className="mt-1 text-xs text-gray-400">{project.date}</p>
            {project.description && <p className="mt-2 text-sm text-gray-600">{project.description}</p>}
          </Card>

          {project.quotes.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-sm font-semibold text-gray-800">Cotizaciones</h2>
              {project.quotes.map((quote) => (
                <Card key={quote.code}>
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-gray-900">{quote.code}</p>
                    <Badge>{QUOTE_STATUS_LABELS[quote.status] ?? quote.status}</Badge>
                  </div>
                  <ul className="mt-2 space-y-1 text-sm text-gray-600">
                    {quote.items.map((item, idx) => (
                      <li key={idx} className="flex justify-between">
                        <span>
                          {item.quantity} × {item.description}
                        </span>
                        <span>{formatDOP(item.subtotal)}</span>
                      </li>
                    ))}
                  </ul>
                  <div className="mt-2 space-y-1 rounded-xl bg-brand-gray p-3 text-sm">
                    <div className="flex justify-between text-gray-500">
                      <span>Subtotal</span>
                      <span>{formatDOP(quote.subtotal)}</span>
                    </div>
                    <div className="flex justify-between text-gray-500">
                      <span>ITBIS (18%)</span>
                      <span>{formatDOP(quote.itbis)}</span>
                    </div>
                    <div className="flex justify-between font-semibold text-gray-900">
                      <span>Total</span>
                      <span>{formatDOP(quote.total)}</span>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}

          {project.invoices.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-sm font-semibold text-gray-800">Facturas</h2>
              {project.invoices.map((invoice) => (
                <Card key={invoice.id}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">{invoice.code}</p>
                      {invoice.ncf && <p className="text-xs text-gray-500">NCF: {invoice.ncf}</p>}
                    </div>
                    <p className="text-sm font-semibold text-gray-800">{formatDOP(invoice.total)}</p>
                  </div>
                  <a
                    href={`/api/public/projects/${token}/invoices/${invoice.id}/pdf`}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-3 block w-full rounded-2xl bg-brand-blue px-5 py-3 text-center text-sm font-medium text-white"
                  >
                    Descargar PDF
                  </a>
                </Card>
              ))}
            </div>
          )}

          {project.quotes.length === 0 && project.invoices.length === 0 && (
            <p className="text-sm text-gray-500">Aún no hay cotizaciones ni facturas para este proyecto.</p>
          )}
        </div>
      )}
    </div>
  )
}
