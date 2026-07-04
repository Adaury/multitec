import { useEffect, useState, type ReactNode } from 'react'
import { useParams } from 'react-router-dom'
import {
  PROJECT_STATUS_LABELS,
  QUOTE_STATUS_LABELS,
  TICKET_STATUS_LABELS,
  type PublicProject,
  type QuoteStatus,
  type TicketStatus,
} from '../lib/types'
import { formatDOP } from '../lib/format'
import { Badge, Button, Card } from '../components/ui'

const PROJECT_STAGES = ['levantamiento', 'ingenieria', 'presupuesto', 'cotizacion', 'ejecucion', 'cerrado']

const QUOTE_STATUS_TONE: Record<QuoteStatus, 'blue' | 'green' | 'red' | 'gray'> = {
  pendiente: 'blue',
  aprobada: 'green',
  no_aprobada: 'red',
  archivada: 'gray',
}

const TICKET_STATUS_TONE: Record<TicketStatus, 'blue' | 'amber' | 'green' | 'gray'> = {
  abierto: 'blue',
  en_proceso: 'amber',
  resuelto: 'green',
  cerrado: 'gray',
}

function ShieldIcon({ className = 'h-5 w-5' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className={className}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
      />
    </svg>
  )
}

function DocumentIcon({ className = 'h-4 w-4' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className={className}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
      />
    </svg>
  )
}

function BanknotesIcon({ className = 'h-4 w-4' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className={className}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M2.25 8.25h19.5M2.25 15.75h19.5M3.75 6h16.5a1.5 1.5 0 011.5 1.5v9a1.5 1.5 0 01-1.5 1.5H3.75a1.5 1.5 0 01-1.5-1.5v-9a1.5 1.5 0 011.5-1.5zM15 12a3 3 0 11-6 0 3 3 0 016 0z"
      />
    </svg>
  )
}

function WrenchIcon({ className = 'h-4 w-4' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className={className}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75"
      />
    </svg>
  )
}

function ExclamationIcon({ className = 'h-6 w-6' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className={className}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
      />
    </svg>
  )
}

function SectionHeading({ icon, title, count }: { icon: ReactNode; title: string; count: number }) {
  return (
    <div className="flex items-center gap-2">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-brand-blue dark:bg-blue-950 dark:text-blue-300">
        {icon}
      </span>
      <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-200">{title}</h2>
      <span className="text-xs text-gray-400">{count}</span>
    </div>
  )
}

function ProjectProgress({ status }: { status: string }) {
  const currentIndex = PROJECT_STAGES.indexOf(status)
  if (currentIndex === -1) return null

  return (
    <div className="mt-5">
      <div className="flex items-start">
        {PROJECT_STAGES.map((stage, idx) => (
          <div key={stage} className="flex flex-1 items-start last:flex-none">
            <div className="flex flex-col items-center gap-1.5">
              <div
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold ${
                  idx < currentIndex
                    ? 'bg-brand-blue text-white'
                    : idx === currentIndex
                      ? 'bg-brand-blue text-white ring-4 ring-blue-100 dark:ring-blue-950'
                      : 'bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500'
                }`}
              >
                {idx < currentIndex ? '✓' : idx + 1}
              </div>
              <span
                className={`hidden w-16 text-center text-[11px] sm:block ${
                  idx === currentIndex ? 'font-semibold text-gray-900 dark:text-gray-100' : 'text-gray-400'
                }`}
              >
                {PROJECT_STATUS_LABELS[stage]}
              </span>
            </div>
            {idx < PROJECT_STAGES.length - 1 && (
              <div
                className={`mx-1 mt-3 h-0.5 flex-1 rounded ${idx < currentIndex ? 'bg-brand-blue' : 'bg-gray-100 dark:bg-gray-800'}`}
              />
            )}
          </div>
        ))}
      </div>
      <p className="mt-2 text-sm font-medium text-gray-700 sm:hidden dark:text-gray-300">
        {PROJECT_STATUS_LABELS[status]}
      </p>
    </div>
  )
}

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
    <div className="min-h-screen bg-brand-bg dark:bg-gray-950">
      <div className="mx-auto max-w-lg px-5 py-6 md:max-w-none md:px-10 md:py-10 lg:px-16 xl:px-24 2xl:px-32">
        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-blue text-white">
            <ShieldIcon className="h-5 w-5" />
          </span>
          <div>
            <p className="text-base font-semibold leading-tight text-gray-900 md:text-lg dark:text-gray-100">
              Multitec
            </p>
            <p className="text-xs text-gray-500">Portal de seguimiento del proyecto</p>
          </div>
        </div>

        <div className="mt-6">
          {loading && (
            <Card>
              <div className="flex items-center gap-3">
                <span className="h-5 w-5 animate-spin rounded-full border-2 border-gray-200 border-t-brand-blue dark:border-gray-700" />
                <p className="text-sm text-gray-500">Cargando…</p>
              </div>
            </Card>
          )}

          {error && (
            <Card>
              <div className="flex items-start gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-50 text-red-500 dark:bg-red-950 dark:text-red-400">
                  <ExclamationIcon className="h-5 w-5" />
                </span>
                <p className="pt-2 text-sm text-red-600 dark:text-red-400">{error}</p>
              </div>
            </Card>
          )}

          {project && (
            <div className="space-y-5">
              <Card>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">{project.client_name}</p>
                    <p className="mt-0.5 font-mono text-xs text-gray-400">{project.code}</p>
                  </div>
                  <Badge>{PROJECT_STATUS_LABELS[project.status] ?? project.status}</Badge>
                </div>
                <p className="mt-1 text-xs text-gray-400">{project.date}</p>
                {project.description && (
                  <p className="mt-3 text-sm text-gray-600 dark:text-gray-400">{project.description}</p>
                )}
                <ProjectProgress status={project.status} />
              </Card>

              <div className={`grid items-start gap-4 ${sectionsGridClass}`}>
                {project.quotes.length > 0 && (
                  <div className="space-y-3">
                    <SectionHeading
                      icon={<DocumentIcon />}
                      title="Cotizaciones"
                      count={project.quotes.length}
                    />
                    <div className={`grid gap-3 ${cardsGridClass(project.quotes.length)}`}>
                      {project.quotes.map((quote) => (
                        <Card key={quote.code}>
                          <div className="flex items-center justify-between">
                            <p className="font-medium text-gray-900 dark:text-gray-100">{quote.code}</p>
                            <Badge tone={QUOTE_STATUS_TONE[quote.status] ?? 'blue'}>
                              {QUOTE_STATUS_LABELS[quote.status] ?? quote.status}
                            </Badge>
                          </div>
                          <ul className="mt-2 space-y-1 text-sm text-gray-600 dark:text-gray-400">
                            {quote.items.map((item, idx) => (
                              <li key={idx} className="flex justify-between">
                                <span>
                                  {item.quantity} × {item.description}
                                </span>
                                <span>{formatDOP(item.subtotal)}</span>
                              </li>
                            ))}
                          </ul>
                          <div className="mt-2 space-y-1 rounded-xl bg-brand-gray p-3 text-sm dark:bg-gray-800">
                            <div className="flex justify-between text-gray-500 dark:text-gray-400">
                              <span>Subtotal</span>
                              <span>{formatDOP(quote.subtotal)}</span>
                            </div>
                            <div className="flex justify-between text-gray-500 dark:text-gray-400">
                              <span>ITBIS (18%)</span>
                              <span>{formatDOP(quote.itbis)}</span>
                            </div>
                            <div className="flex justify-between font-semibold text-gray-900 dark:text-gray-100">
                              <span>Total</span>
                              <span>{formatDOP(quote.total)}</span>
                            </div>
                          </div>
                          {quote.status === 'pendiente' && (
                            <Button
                              className="mt-3"
                              onClick={() => approveQuote(quote.id)}
                              disabled={approvingId === quote.id}
                            >
                              {approvingId === quote.id ? 'Aprobando…' : 'Aprobar cotización'}
                            </Button>
                          )}
                        </Card>
                      ))}
                    </div>
                    {approveError && <p className="text-sm text-red-600 dark:text-red-400">{approveError}</p>}
                  </div>
                )}

                {project.invoices.length > 0 && (
                  <div className="space-y-3">
                    <SectionHeading
                      icon={<BanknotesIcon />}
                      title="Facturas"
                      count={project.invoices.length}
                    />
                    <div className={`grid gap-3 ${cardsGridClass(project.invoices.length)}`}>
                      {project.invoices.map((invoice) => (
                        <Card key={invoice.id}>
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="font-medium text-gray-900 dark:text-gray-100">{invoice.code}</p>
                              {invoice.ncf && <p className="text-xs text-gray-500">NCF: {invoice.ncf}</p>}
                            </div>
                            <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">
                              {formatDOP(invoice.total)}
                            </p>
                          </div>
                          <a
                            href={`/api/public/projects/${token}/invoices/${invoice.id}/pdf`}
                            target="_blank"
                            rel="noreferrer"
                            className="mt-3 block w-full rounded-2xl bg-brand-blue px-5 py-4 text-center text-base font-medium text-white transition hover:bg-brand-blue-dark active:scale-[0.98]"
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
                    <SectionHeading
                      icon={<WrenchIcon />}
                      title="Tickets de soporte"
                      count={project.tickets.length}
                    />
                    <div className={`grid gap-3 ${cardsGridClass(project.tickets.length)}`}>
                      {project.tickets.map((ticket) => (
                        <Card key={ticket.code}>
                          <div className="flex items-center justify-between">
                            <p className="font-medium text-gray-900 dark:text-gray-100">{ticket.code}</p>
                            <Badge tone={TICKET_STATUS_TONE[ticket.status] ?? 'blue'}>
                              {TICKET_STATUS_LABELS[ticket.status] ?? ticket.status}
                            </Badge>
                          </div>
                          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{ticket.problem}</p>
                          <p className="mt-1 text-xs text-gray-400">
                            Técnico: {ticket.technician_name ?? 'Sin asignar'}
                          </p>
                          {ticket.solution && (
                            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                              <span className="font-medium text-gray-800 dark:text-gray-200">Solución:</span>{' '}
                              {ticket.solution}
                            </p>
                          )}
                        </Card>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {project.quotes.length === 0 && project.invoices.length === 0 && project.tickets.length === 0 && (
                <Card className="text-center">
                  <span className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-brand-gray text-gray-400 dark:bg-gray-800">
                    <DocumentIcon className="h-5 w-5" />
                  </span>
                  <p className="mt-3 text-sm text-gray-500">
                    Aún no hay cotizaciones, facturas ni tickets para este proyecto.
                  </p>
                </Card>
              )}
            </div>
          )}
        </div>

        <p className="mt-10 text-center text-xs text-gray-400">Multitec · seguimiento generado automáticamente</p>
      </div>
    </div>
  )
}
