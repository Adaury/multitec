import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { Download, Mail, MessageCircle, Share2 } from 'lucide-react'
import { posterUrl, videoUrl, type Tutorial } from '../lib/tutoriales'

type VideoTutorialProps = {
  tutorial: Tutorial
  /** Muestra la descripción debajo del título (por defecto sí). */
  mostrarDescripcion?: boolean
  /** Nivel del título para no romper la jerarquía de la página (por defecto h3). */
  nivelTitulo?: 'h3' | 'h4' | 'h5'
}

type VideoConPantallaCompleta = HTMLVideoElement & {
  webkitEnterFullscreen?: () => void
  webkitRequestFullscreen?: () => Promise<void> | void
}

/** Espera a que el video conozca su tamaño y duración: el reproductor del iPhone solo abre la pantalla completa
 * cuando ya los sabe (y el video no se descarga hasta pulsar reproducir, para no gastar datos). */
function esperarMetadatos(video: HTMLVideoElement, maxMs = 2500): Promise<void> {
  if (video.readyState >= 1) return Promise.resolve()
  return new Promise((resolve) => {
    const terminar = () => {
      video.removeEventListener('loadedmetadata', terminar)
      resolve()
    }
    video.addEventListener('loadedmetadata', terminar)
    video.preload = 'metadata'
    video.load()
    setTimeout(terminar, maxMs)
  })
}

/** Reproductor de un video tutorial con su transcripción. Si el archivo no existe (o el navegador no lo puede
 * reproducir) muestra un aviso en vez de un reproductor roto, y la transcripción sigue disponible.
 *
 * Pantalla completa: el botón de los controles nativos no siempre funciona (la app dentro de un marco sin permiso,
 * algunos navegadores del iPhone), así que hay un botón propio que prueba la pantalla completa del navegador y, si no se
 * puede, ocupa toda la pantalla desde la propia página. En los dos casos el video sigue reproduciéndose. */
export function VideoTutorial({ tutorial, mostrarDescripcion = true, nivelTitulo = 'h3' }: VideoTutorialProps) {
  const [fallo, setFallo] = useState(false)
  const [ampliado, setAmpliado] = useState(false)
  const videoRef = useRef<VideoConPantallaCompleta>(null)
  const idTranscripcion = useId()
  const Titulo = nivelTitulo

  useEffect(() => setFallo(false), [tutorial.id])

  const cerrarAmpliado = useCallback(() => setAmpliado(false), [])

  // Pantalla completa de la propia página: sin scroll por detrás y se cierra con Escape
  useEffect(() => {
    if (!ampliado) return
    const anterior = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const alTeclear = (e: KeyboardEvent) => e.key === 'Escape' && cerrarAmpliado()
    window.addEventListener('keydown', alTeclear)
    return () => {
      document.body.style.overflow = anterior
      window.removeEventListener('keydown', alTeclear)
    }
  }, [ampliado, cerrarAmpliado])

  async function pantallaCompleta() {
    const video = videoRef.current
    if (!video) return
    try {
      if (video.requestFullscreen) {
        await video.requestFullscreen()
        return
      }
      // iPhone: el reproductor nativo (solo con el video ya preparado)
      if (video.webkitEnterFullscreen) {
        await esperarMetadatos(video)
        video.webkitEnterFullscreen()
        return
      }
      if (video.webkitRequestFullscreen) {
        await video.webkitRequestFullscreen()
        return
      }
    } catch {
      // el navegador no la permite aquí (marco sin permiso, restricciones): se usa la de la página
    }
    setAmpliado(true)
  }

  return (
    <figure
      className="m-0 overflow-hidden rounded-2xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900"
      data-testid={`video-${tutorial.id}`}
    >
      <div className={ampliado ? 'fixed inset-0 z-[100] flex bg-black' : 'relative aspect-video w-full bg-gray-900'}>
        {fallo ? (
          <div role="status" className="flex h-full w-full flex-col items-center justify-center gap-1 px-4 text-center text-sm text-gray-200">
            <span aria-hidden="true" className="text-2xl">
              🎬
            </span>
            <p className="font-medium">Este video aún no está disponible</p>
            <p className="text-xs text-gray-400">Mientras tanto, puedes leer los pasos que aparecen debajo.</p>
          </div>
        ) : (
          <>
            <video
              ref={videoRef}
              key={tutorial.id}
              className={ampliado ? 'h-full w-full object-contain' : 'h-full w-full'}
              src={videoUrl(tutorial.id)}
              poster={posterUrl(tutorial.id)}
              controls
              preload="none"
              playsInline
              aria-label={`Video: ${tutorial.titulo}`}
              onError={() => setFallo(true)}
            >
              Tu navegador no puede reproducir este video. Lee los pasos que aparecen debajo.
            </video>
            {ampliado ? (
              <button
                type="button"
                onClick={cerrarAmpliado}
                className="absolute right-3 top-[max(0.75rem,env(safe-area-inset-top))] rounded-full bg-black/70 px-4 py-2 text-sm font-semibold text-white"
              >
                ✕ Cerrar
              </button>
            ) : (
              <button
                type="button"
                onClick={pantallaCompleta}
                aria-label="Ver el video en pantalla completa"
                className="absolute right-2 top-2 rounded-full bg-black/60 px-3 py-1.5 text-xs font-medium text-white"
              >
                ⛶ Pantalla completa
              </button>
            )}
          </>
        )}
      </div>

      <figcaption className="p-4">
        <Titulo className="text-base font-semibold text-gray-900 dark:text-gray-100">
          {tutorial.titulo}{' '}
          <span className="ml-1 text-xs font-normal text-gray-500 dark:text-gray-400">({tutorial.duracion})</span>
        </Titulo>
        {mostrarDescripcion && <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">{tutorial.descripcion}</p>}

        {!fallo && <AccionesVideo tutorial={tutorial} />}

        <details className="mt-3 text-sm">
          <summary aria-controls={idTranscripcion} className="cursor-pointer font-medium text-brand-blue hover:underline">
            Ver los pasos en texto
          </summary>
          <ol id={idTranscripcion} className="mt-2 list-decimal space-y-1 pl-5 text-gray-700 dark:text-gray-300">
            {tutorial.transcripcion.map((linea) => (
              <li key={linea}>{linea}</li>
            ))}
          </ol>
        </details>
      </figcaption>
    </figure>
  )
}

function nombreArchivo(tutorial: Tutorial): string {
  return `Multitec - ${tutorial.titulo.replace(/[\\/:*?"<>|«»]/g, '')}.mp4`
}

/** Descargar el video y mandarlo a otra persona. En el teléfono se comparte el archivo con la hoja de compartir
 * (WhatsApp, correo, AirDrop…). En la computadora se descarga y se abre WhatsApp o el correo para adjuntarlo:
 * un enlace no le serviría a quien está fuera de la red de la oficina. */
function AccionesVideo({ tutorial }: { tutorial: Tutorial }) {
  const [estado, setEstado] = useState<'listo' | 'preparando' | 'descargado'>('listo')
  const mensaje = `Te comparto este video de Multitec: «${tutorial.titulo}». ${tutorial.descripcion}`

  async function descargar(): Promise<Blob> {
    const res = await fetch(videoUrl(tutorial.id))
    if (!res.ok) throw new Error('No se pudo bajar el video')
    return res.blob()
  }

  function guardar(blob: Blob) {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = nombreArchivo(tutorial)
    document.body.append(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 30_000)
  }

  async function enviar() {
    setEstado('preparando')
    try {
      const blob = await descargar()
      const archivo = new File([blob], nombreArchivo(tutorial), { type: 'video/mp4' })
      if (navigator.canShare?.({ files: [archivo] })) {
        await navigator.share({ files: [archivo], title: tutorial.titulo, text: mensaje }).catch(() => {})
        setEstado('listo')
        return
      }
      guardar(blob)
      setEstado('descargado')
    } catch {
      setEstado('listo')
    }
  }

  const boton =
    'inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition disabled:opacity-50'
  return (
    <div className="mt-3 space-y-2">
      <div className="flex flex-wrap gap-2">
        <a
          href={videoUrl(tutorial.id)}
          download={nombreArchivo(tutorial)}
          className={`${boton} bg-brand-gray text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700`}
        >
          <Download className="h-4 w-4" aria-hidden="true" /> Descargar
        </a>
        <button
          type="button"
          onClick={enviar}
          disabled={estado === 'preparando'}
          className={`${boton} bg-brand-blue text-white hover:bg-brand-blue-dark`}
        >
          <Share2 className="h-4 w-4" aria-hidden="true" />
          {estado === 'preparando' ? 'Preparando…' : 'Enviar a otra persona'}
        </button>
      </div>
      {estado === 'descargado' && (
        <div role="status" className="rounded-xl bg-blue-50 p-3 text-xs text-gray-700 dark:bg-blue-950 dark:text-gray-200">
          <p>Se descargó el video. Ábrelo en WhatsApp o en el correo y adjúntalo:</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <a
              href={`https://wa.me/?text=${encodeURIComponent(mensaje)}`}
              target="_blank"
              rel="noreferrer"
              className={`${boton} bg-emerald-600 text-white hover:bg-emerald-700`}
            >
              <MessageCircle className="h-4 w-4" aria-hidden="true" /> WhatsApp
            </a>
            <a
              href={`mailto:?subject=${encodeURIComponent(`Video de Multitec: ${tutorial.titulo}`)}&body=${encodeURIComponent(`${mensaje}\n\n(El video va adjunto.)`)}`}
              className={`${boton} bg-white text-gray-700 ring-1 ring-black/10 hover:bg-gray-50 dark:bg-gray-900 dark:text-gray-200`}
            >
              <Mail className="h-4 w-4" aria-hidden="true" /> Correo
            </a>
          </div>
        </div>
      )}
    </div>
  )
}
