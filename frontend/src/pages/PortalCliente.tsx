import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { PROJECT_STATUS_LABELS, QUOTE_STATUS_LABELS, TICKET_STATUS_LABELS, type PublicProject } from '../lib/types'
import { formatDOP } from '../lib/format'
import { Badge, Card } from '../components/ui'

export function PortalCliente() {
  const { token } = useParams()
  const [project, setProject] = useState<PublicProject | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [approvingId, setApprovingId] = useState<number | null>(null)
  const [approveError, setApproveError] = useState<string | null>(null)

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

  const approveQuote = async (quoteId: number) => {
    if (!token || !window.confirm('¿Confirmas que apruebas esta cotización?')) return
    setApproveError(null)
    setApprovingId(quoteId)
    try {
      const res = await fetch(`/api/public/projects/${token}/quotes/${quoteId}/approve`, { method: 'POST' })
      if (!res.ok) throw new Error('approve-failed')
      setProject(await res.json())
    } catch {
      setApproveError('No se pudo aprobar la cotización. Intenta de nuevo.')
    } finally {
      setApprovingId(null)
    }
  }

  const visibleSections = project
    ? [project.quotes.length > 0, project.invoices.length > 0, project.tickets.length > 0].filter(Boolean).length
    : 0
  // Con varias secciones, cada una ocupa su propia columna (aprovecha el ancho sin
  // depender de cuántas tarjetas tenga). Con una sola sección, esa sección reparte sus
  // propias tarjetas en columnas para no dejar la mitad de la pantalla vacía.
  const sectionsGridClass = visibleSections === 3 ? 'md:grid-cols-3' : visibleSections === 2 ? 'md:grid-cols-2' : 'md:grid-cols-1'
  const cardsGridClass = (count: number) => {
    if (visibleSections > 1 || count <= 1) return ''
    if (count === 2) return 'sm:grid-cols-2'
    return 'sm:grid-cols-2 xl:grid-cols-3'
  }

  return (
    <div className="mx-auto min-h-screen max-w-lg bg-brand-bg px-5 py-6 md:max-w-none md:px-10 md:py-10 lg:px-16 xl:px-24">
      <p className="text-lg font-semibold text-gray-900 md:text-xl">Multitec</p>
      <p className="mb-6 text-xs text-gray-500 md:text-sm">Portal de seguimiento del proyecto</p>

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

          <div className={`grid items-start gap-4 ${sectionsGridClass}`}>
            {project.quotes.length > 0 && (
              <div className="space-y-3">
                <h2 className="text-sm font-semibold text-gray-800">Cotizaciones</h2>
                <div className={`grid gap-3 ${cardsGridClass(project.quotes.length)}`}>
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
                      {quote.status === 'pendiente' && (
                        <button
                          type="button"
                          onClick={() => approveQuote(quote.id)}
                          disabled={approvingId === quote.id}
                          className="mt-3 block w-full rounded-2xl bg-brand-blue px-5 py-3 text-center text-sm font-medium text-white disabled:opacity-60"
                        >
                          {approvingId === quote.id ? 'Aprobando…' : 'Aprobar cotización'}
                        </button>
                      )}
                    </Card>
                  ))}
                </div>
                {approveError && <p className="text-sm text-red-600">{approveError}</p>}
              </div>
            )}

            {project.invoices.length > 0 && (
              <div className="space-y-3">
                <h2 className="text-sm font-semibold text-gray-800">Facturas</h2>
                <div className={`grid gap-3 ${cardsGridClass(project.invoices.length)}`}>
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
              </div>
            )}

            {project.tickets.length > 0 && (
              <div className="space-y-3">
                <h2 className="text-sm font-semibold text-gray-800">Tickets de soporte</h2>
                <div className={`grid gap-3 ${cardsGridClass(project.tickets.length)}`}>
                  {project.tickets.map((ticket) => (
                    <Card key={ticket.code}>
                      <div className="flex items-center justify-between">
                        <p className="font-medium text-gray-900">{ticket.code}</p>
                        <Badge>{TICKET_STATUS_LABELS[ticket.status] ?? ticket.status}</Badge>
                      </div>
                      <p className="mt-1 text-sm text-gray-600">{ticket.problem}</p>
                      <p className="mt-1 text-xs text-gray-400">
                        Técnico: {ticket.technician_name ?? 'Sin asignar'}
                      </p>
                      {ticket.solution && (
                        <p className="mt-2 text-sm text-gray-600">
                          <span className="font-medium text-gray-800">Solución:</span> {ticket.solution}
                        </p>
                      )}
                    </Card>
                  ))}
                </div>
              </div>
            )}
          </div>

          {project.quotes.length === 0 && project.invoices.length === 0 && project.tickets.length === 0 && (
            <p className="text-sm text-gray-500">Aún no hay cotizaciones, facturas ni tickets para este proyecto.</p>
          )}
        </div>
      )}
    </div>
  )
}
