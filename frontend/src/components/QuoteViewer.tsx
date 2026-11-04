import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, Link2, Mail, MessageCircle, Minus, Pencil, Plus, Send, Share2, X } from 'lucide-react'
import type { PDFDocumentProxy } from 'pdfjs-dist/legacy/build/pdf.mjs'
import { api, apiErrorMessage } from '../lib/api'
import { formatDOP } from '../lib/format'
import type { Client, Quote } from '../lib/types'
import { whatsappUrl } from '../lib/whatsapp'
import { Button, Field, Input, Textarea } from './ui'

export type QuoteVariant = 'detallada' | 'ejecutiva' | 'global'
type Photos = 'none' | 'marked'

const VARIANTS: { key: QuoteVariant; label: string; hint: string }[] = [
  { key: 'detallada', label: 'Con detalles', hint: 'Cada partida con cantidad, precio e importe.' },
  { key: 'ejecutiva', label: 'Por categoría', hint: 'Un subtotal por categoría (cámaras, cableado, mano de obra…).' },
  { key: 'global', label: 'Monto general', hint: 'Lo que se instala, con cantidades, y solo el total del servicio.' },
]

const SUFFIX: Record<QuoteVariant, string> = { detallada: '', ejecutiva: '-ejecutiva', global: '-monto-general' }

function fileName(quote: Quote, variant: QuoteVariant, photos: Photos) {
  return `${quote.code}${SUFFIX[variant]}${photos === 'marked' ? '-fotos' : ''}.pdf`
}

function clientMessage(quote: Quote, client: Client, variant: QuoteVariant) {
  const how =
    variant === 'global'
      ? `por un monto general de ${formatDOP(quote.total)}`
      : variant === 'ejecutiva'
        ? `resumida por categoría, por un total de ${formatDOP(quote.total)}`
        : `con el detalle de cada partida, por un total de ${formatDOP(quote.total)}`
  return `Hola ${client.name}, le comparto la cotización ${quote.code} ${how}.`
}

function download(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = name
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/** pdf.js se carga solo al abrir el visor (no pesa en el resto de la app). Versión "legacy": funciona también en
 * iPhones con iOS anterior al 17. */
async function loadPdf(blob: Blob): Promise<PDFDocumentProxy> {
  const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs')
  const worker = await import('pdfjs-dist/legacy/build/pdf.worker.min.mjs?url')
  pdfjs.GlobalWorkerOptions.workerSrc = worker.default
  const data = new Uint8Array(await blob.arrayBuffer())
  return pdfjs.getDocument({ data, isEvalSupported: false }).promise
}

function PdfPage({ doc, pageNumber, width }: { doc: PDFDocumentProxy; pageNumber: number; width: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    let cancelled = false
    let task: { cancel: () => void; promise: Promise<void> } | null = null
    // Un documento ya cerrado (se cambió de formato a mitad del dibujo) rechaza: se ignora, el nuevo lo reemplaza.
    doc.getPage(pageNumber).catch(() => null).then((page) => {
      if (!page || cancelled || !canvasRef.current || width <= 0) return
      const base = page.getViewport({ scale: 1 })
      const scale = width / base.width
      const ratio = Math.min(window.devicePixelRatio || 1, 2)
      const viewport = page.getViewport({ scale: scale * ratio })
      const canvas = canvasRef.current
      canvas.width = Math.floor(viewport.width)
      canvas.height = Math.floor(viewport.height)
      canvas.style.width = `${Math.floor(viewport.width / ratio)}px`
      canvas.style.height = `${Math.floor(viewport.height / ratio)}px`
      const context = canvas.getContext('2d')
      if (!context) return
      task = page.render({ canvasContext: context, viewport })
      task.promise.catch(() => {})
    })
    return () => {
      cancelled = true
      task?.cancel()
    }
  }, [doc, pageNumber, width])
  return <canvas ref={canvasRef} className="mx-auto block rounded bg-white shadow-lg" aria-label={`Página ${pageNumber}`} />
}

/** Visor grande de la cotización dentro de la app (sin descargar), con el formato elegible, edición y envío al
 * cliente por WhatsApp, correo, enlace del portal u otra app. Lo que se ve es exactamente lo que se envía. */
export function QuoteViewer({
  quote,
  client,
  projectId,
  publicToken,
  onClose,
  onEdit,
  initialVariant = 'detallada',
}: {
  quote: Quote
  client: Client
  projectId: number
  publicToken?: string | null
  onClose: () => void
  /** Solo si la cotización se puede editar (pendiente): cierra el visor y abre la edición. */
  onEdit?: () => void
  initialVariant?: QuoteVariant
}) {
  const queryClient = useQueryClient()
  const [variant, setVariant] = useState<QuoteVariant>(initialVariant)
  const [photos, setPhotos] = useState<Photos>('none')
  const [zoom, setZoom] = useState(1)
  const [panel, setPanel] = useState<'vista' | 'enviar'>('vista')
  const [doc, setDoc] = useState<PDFDocumentProxy | null>(null)
  const [renderError, setRenderError] = useState<string | null>(null)
  const [width, setWidth] = useState(0)
  const stageRef = useRef<HTMLDivElement>(null)

  // Cerrar con Escape y no dejar que la página de atrás se desplace mientras el visor está abierto.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = previous
    }
  }, [onClose])

  useEffect(() => {
    const el = stageRef.current
    if (!el) return
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width))
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const pdf = useQuery({
    queryKey: ['quote-pdf', quote.id, variant, photos, quote.updated_at ?? quote.created_at],
    queryFn: async () =>
      (
        await api.get<Blob>(`/quotes/${quote.id}/pdf`, {
          params: { variant, ...(photos === 'none' ? {} : { photos }) },
          responseType: 'blob',
        })
      ).data,
  })

  useEffect(() => {
    if (!pdf.data) return
    let cancelled = false
    let loaded: PDFDocumentProxy | null = null
    setRenderError(null)
    loadPdf(pdf.data)
      .then((d) => {
        loaded = d
        if (cancelled) d.destroy()
        else setDoc(d)
      })
      .catch(() => !cancelled && setRenderError('No se pudo mostrar el PDF. Descárgalo para verlo.'))
    return () => {
      cancelled = true
      // Primero se deja de mostrar, después se cierra: ninguna página intenta dibujar un documento cerrado.
      setDoc(null)
      const old = loaded
      if (old) setTimeout(() => old.destroy(), 0)
    }
  }, [pdf.data])

  const pageWidth = Math.max(0, Math.min(width - 16, 900) * zoom)
  const pages = useMemo(() => (doc ? Array.from({ length: doc.numPages }, (_, i) => i + 1) : []), [doc])
  const name = fileName(quote, variant, photos)
  const current = VARIANTS.find((v) => v.key === variant)!

  return (
    <div className="fixed inset-0 z-[70] flex flex-col bg-gray-950 text-gray-100" role="dialog" aria-modal="true" aria-label={`Cotización ${quote.code}`}>
      <header className="flex items-center gap-1.5 border-b border-white/10 px-3 py-2 pt-[max(0.5rem,env(safe-area-inset-top))] md:gap-2 md:px-5 md:py-3">
        <div className="mr-auto min-w-0 flex-1">
          <p className="truncate text-base font-semibold md:text-lg">Cotización {quote.code}</p>
          <p className="truncate text-xs text-gray-400 md:text-sm">
            {client.name} · {formatDOP(quote.total)}
          </p>
        </div>
        <div className="hidden items-center gap-1 md:flex">
          <button type="button" className="rounded-lg p-2 hover:bg-white/10" onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))} aria-label="Alejar">
            <Minus size={18} />
          </button>
          <span className="w-12 text-center text-sm tabular-nums text-gray-300">{Math.round(zoom * 100)}%</span>
          <button type="button" className="rounded-lg p-2 hover:bg-white/10" onClick={() => setZoom((z) => Math.min(2.5, z + 0.25))} aria-label="Acercar">
            <Plus size={18} />
          </button>
        </div>
        {onEdit && (
          <button type="button" onClick={onEdit} aria-label="Editar" className="flex items-center gap-1.5 rounded-xl bg-white/10 px-3 py-2 text-sm font-medium hover:bg-white/20">
            <Pencil size={16} /> <span className="hidden sm:inline">Editar</span>
          </button>
        )}
        <button
          type="button"
          onClick={() => pdf.data && download(pdf.data, name)}
          aria-label="Descargar"
          disabled={!pdf.data}
          className="flex items-center gap-1.5 rounded-xl bg-white/10 px-3 py-2 text-sm font-medium hover:bg-white/20 disabled:opacity-40"
        >
          <Download size={16} /> <span className="hidden sm:inline">Descargar</span>
        </button>
        <button type="button" onClick={onClose} className="rounded-xl p-2 hover:bg-white/10" aria-label="Cerrar visor">
          <X size={22} />
        </button>
      </header>

      {/* Teléfono: pestañas Vista / Enviar. Pantalla ancha: el panel va al lado. */}
      <div className="flex gap-1 border-b border-white/10 p-1 md:hidden" role="tablist">
        {(['vista', 'enviar'] as const).map((key) => (
          <button
            key={key}
            role="tab"
            aria-selected={panel === key}
            onClick={() => setPanel(key)}
            className={`flex-1 rounded-lg py-2 text-sm font-medium ${panel === key ? 'bg-white/15 text-white' : 'text-gray-400'}`}
          >
            {key === 'vista' ? 'Vista' : 'Formato y envío'}
          </button>
        ))}
      </div>

      <div className="flex min-h-0 flex-1">
        <div ref={stageRef} className={`min-h-0 flex-1 overflow-auto p-2 md:p-6 ${panel === 'vista' ? '' : 'hidden md:block'}`}>
          {(pdf.isLoading || (pdf.data && !doc && !renderError)) && <p className="mt-10 text-center text-sm text-gray-400">Preparando la vista…</p>}
          {pdf.isError && (
            <p className="mt-10 text-center text-sm text-red-300">{apiErrorMessage(pdf.error, 'No se pudo cargar la cotización.')}</p>
          )}
          {renderError && <p className="mt-10 text-center text-sm text-amber-300">{renderError}</p>}
          {doc && !pdf.isFetching && (
            <div className="space-y-4 pb-6" data-testid="quote-viewer-pages">
              {pages.map((n) => (
                <PdfPage key={n} doc={doc} pageNumber={n} width={pageWidth} />
              ))}
            </div>
          )}
          {/* Teléfono: acercar/alejar flotante (en pantalla ancha va en la cabecera). */}
          {panel === 'vista' && (
            <div className="fixed bottom-[max(1rem,env(safe-area-inset-bottom))] right-4 flex items-center gap-1 rounded-full bg-gray-800/90 p-1 shadow-lg ring-1 ring-white/10 md:hidden">
              <button type="button" className="rounded-full p-2.5" onClick={() => setZoom((z) => Math.max(1, z - 0.5))} aria-label="Alejar">
                <Minus size={18} />
              </button>
              <span className="w-10 text-center text-xs tabular-nums">{Math.round(zoom * 100)}%</span>
              <button type="button" className="rounded-full p-2.5" onClick={() => setZoom((z) => Math.min(3, z + 0.5))} aria-label="Acercar">
                <Plus size={18} />
              </button>
            </div>
          )}
        </div>

        <aside
          className={`min-h-0 w-full shrink-0 overflow-y-auto border-white/10 bg-gray-900 p-4 md:block md:w-[22rem] md:border-l lg:w-[26rem] ${
            panel === 'enviar' ? '' : 'hidden'
          }`}
        >
          <section className="space-y-2">
            <h3 className="text-sm font-semibold text-gray-200">¿Cómo la quieres mostrar al cliente?</h3>
            <div className="grid grid-cols-3 gap-1 rounded-xl bg-white/5 p-1" role="radiogroup" aria-label="Formato">
              {VARIANTS.map((v) => (
                <button
                  key={v.key}
                  role="radio"
                  aria-checked={variant === v.key}
                  onClick={() => setVariant(v.key)}
                  className={`rounded-lg px-2 py-2 text-xs font-medium sm:text-sm ${variant === v.key ? 'bg-brand-blue text-white' : 'text-gray-300 hover:bg-white/10'}`}
                >
                  {v.label}
                </button>
              ))}
            </div>
            <p className="text-xs text-gray-400">{current.hint}</p>
            <label className="flex items-center gap-2 text-sm text-gray-300">
              <input type="checkbox" checked={photos === 'marked'} onChange={(e) => setPhotos(e.target.checked ? 'marked' : 'none')} />
              Incluir fotos del levantamiento con los puntos marcados
            </label>
          </section>

          <SendPanel
            quote={quote}
            client={client}
            projectId={projectId}
            publicToken={publicToken}
            variant={variant}
            blob={pdf.data}
            name={name}
            photos={photos}
            onSent={() => queryClient.invalidateQueries({ queryKey: ['quote-history', quote.id] })}
          />
        </aside>
      </div>
    </div>
  )
}

function SendPanel({
  quote,
  client,
  projectId,
  publicToken,
  variant,
  photos,
  blob,
  name,
  onSent,
}: {
  quote: Quote
  client: Client
  projectId: number
  publicToken?: string | null
  variant: QuoteVariant
  photos: Photos
  blob: Blob | undefined
  name: string
  onSent: () => void
}) {
  const queryClient = useQueryClient()
  const [channel, setChannel] = useState<'whatsapp' | 'correo' | 'portal' | null>(null)
  const [to, setTo] = useState(client.email ?? '')
  const [message, setMessage] = useState('')
  const [notice, setNotice] = useState<{ tone: 'ok' | 'warn' | 'error'; text: string } | null>(null)
  const text = clientMessage(quote, client, variant)
  const file = blob ? new File([blob], name, { type: 'application/pdf' }) : null
  const canShareFile = !!file && typeof navigator.canShare === 'function' && navigator.canShare({ files: [file] })
  const isLocalOrigin = /localhost|127\.0\.0\.1|192\.168\.|\.test$/.test(window.location.hostname)

  const sendEmail = useMutation({
    mutationFn: async () =>
      (await api.post(`/quotes/${quote.id}/send-email`, { to, variant, photos, message: message.trim() || null })).data,
    onSuccess: () => {
      setNotice({ tone: 'ok', text: `Enviada por correo a ${to}.` })
      onSent()
    },
    onError: (err) => setNotice({ tone: 'error', text: apiErrorMessage(err, 'No se pudo enviar el correo.') }),
  })

  const portal = useMutation({
    mutationFn: async () => {
      let token = publicToken
      if (!token) {
        token = (await api.post<{ token: string }>(`/projects/${projectId}/public-link`)).data.token
        queryClient.invalidateQueries({ queryKey: ['projects'] })
      }
      return token
    },
    onSuccess: (token) => {
      const link = `${window.location.origin}/portal/${token}`
      const body = `${text} Puede verla y aprobarla aquí: ${link}`
      window.open(whatsappUrl(client.phone, body) ?? `https://wa.me/?text=${encodeURIComponent(body)}`, '_blank')
    },
    onError: () => setNotice({ tone: 'error', text: 'No se pudo preparar el enlace del cliente.' }),
  })

  async function shareFile() {
    if (!file) return
    try {
      await navigator.share({ files: [file], title: `Cotización ${quote.code}`, text })
      setNotice({ tone: 'ok', text: 'Listo. Elige WhatsApp (u otra app) y el chat del cliente para enviar el PDF.' })
    } catch (err) {
      if ((err as DOMException)?.name !== 'AbortError') setNotice({ tone: 'error', text: 'No se pudo abrir el menú de compartir.' })
    }
  }

  function whatsapp() {
    setNotice(null)
    if (canShareFile) return void shareFile()
    // Computadora: WhatsApp no deja adjuntar desde un enlace. Se descarga el PDF y se abre el chat con el mensaje.
    if (blob) download(blob, name)
    const body = `${text} Le envío el PDF adjunto.`
    window.open(whatsappUrl(client.phone, body) ?? `https://wa.me/?text=${encodeURIComponent(body)}`, '_blank')
    setNotice({ tone: 'warn', text: `Se descargó ${name}. Adjúntalo en el chat de WhatsApp que se abrió (clip → Documento).` })
  }

  const channelButton = (key: 'whatsapp' | 'correo' | 'portal', icon: ReactNode, label: string) => (
    <button
      type="button"
      onClick={() => {
        setChannel(key)
        setNotice(null)
      }}
      aria-pressed={channel === key}
      className={`flex flex-col items-center gap-1 rounded-xl px-2 py-3 text-xs font-medium sm:text-sm ${
        channel === key ? 'bg-brand-blue text-white' : 'bg-white/5 text-gray-200 hover:bg-white/10'
      }`}
    >
      {icon}
      {label}
    </button>
  )

  return (
    <section className="mt-6 space-y-3 border-t border-white/10 pt-4">
      <h3 className="text-sm font-semibold text-gray-200">¿Cómo se la envías?</h3>
      <div className="grid grid-cols-3 gap-2">
        {channelButton('whatsapp', <MessageCircle size={20} />, 'WhatsApp')}
        {channelButton('correo', <Mail size={20} />, 'Correo')}
        {channelButton('portal', <Link2 size={20} />, 'Enlace')}
      </div>

      {channel === 'whatsapp' && (
        <div className="space-y-2 text-sm text-gray-300">
          <p>
            Se envía el PDF <strong className="text-white">{name}</strong>
            {client.phone ? ` al ${client.phone}` : ' (el cliente no tiene teléfono: eliges el contacto en WhatsApp)'}.
          </p>
          <Button onClick={whatsapp} disabled={!blob} className="flex items-center justify-center gap-2 !py-3">
            <Send size={18} /> Enviar por WhatsApp
          </Button>
        </div>
      )}

      {channel === 'correo' && (
        <form
          className="space-y-2"
          onSubmit={(e) => {
            e.preventDefault()
            setNotice(null)
            sendEmail.mutate()
          }}
        >
          <Field label="Correo del cliente">
            <Input type="email" required value={to} onChange={(e) => setTo(e.target.value)} placeholder="cliente@correo.com" />
          </Field>
          <Field label="Mensaje (opcional)">
            <Textarea rows={3} value={message} onChange={(e) => setMessage(e.target.value)} placeholder={`${text} Adjuntamos el PDF.`} />
          </Field>
          <Button type="submit" disabled={sendEmail.isPending || !to} className="flex items-center justify-center gap-2 !py-3">
            <Mail size={18} /> {sendEmail.isPending ? 'Enviando…' : 'Enviar por correo'}
          </Button>
        </form>
      )}

      {channel === 'portal' && (
        <div className="space-y-2 text-sm text-gray-300">
          <p>
            Le llega por WhatsApp un enlace donde ve la cotización <strong className="text-white">con detalles</strong>, la
            descarga y la aprueba o pide cambios desde su teléfono.
          </p>
          {isLocalOrigin && (
            <p className="text-xs text-amber-300">
              Estás en una dirección local: el cliente no podrá abrir el enlace. Entra por la dirección pública (túnel o dominio).
            </p>
          )}
          <Button onClick={() => portal.mutate()} disabled={portal.isPending} className="flex items-center justify-center gap-2 !py-3">
            <Link2 size={18} /> {portal.isPending ? 'Preparando…' : 'Enviar enlace por WhatsApp'}
          </Button>
        </div>
      )}

      {canShareFile && (
        <button type="button" onClick={shareFile} className="flex w-full items-center justify-center gap-2 rounded-xl bg-white/5 py-2.5 text-sm text-gray-200 hover:bg-white/10">
          <Share2 size={16} /> Compartir el PDF con otra app
        </button>
      )}

      {notice && (
        <p
          role="status"
          className={`rounded-xl p-3 text-sm ${
            notice.tone === 'ok' ? 'bg-green-500/15 text-green-200' : notice.tone === 'warn' ? 'bg-amber-500/15 text-amber-200' : 'bg-red-500/15 text-red-200'
          }`}
        >
          {notice.text}
        </p>
      )}
    </section>
  )
}
