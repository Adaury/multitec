import { useEffect, useId, useState } from 'react'
import { posterUrl, videoUrl, type Tutorial } from '../lib/tutoriales'

type VideoTutorialProps = {
  tutorial: Tutorial
  /** Muestra la descripción debajo del título (por defecto sí). */
  mostrarDescripcion?: boolean
  /** Nivel del título para no romper la jerarquía de la página (por defecto h3). */
  nivelTitulo?: 'h3' | 'h4' | 'h5'
}

/** Reproductor de un video tutorial con su transcripción. Si el archivo no existe (o el navegador no lo puede
 * reproducir) muestra un aviso en vez de un reproductor roto, y la transcripción sigue disponible. */
export function VideoTutorial({ tutorial, mostrarDescripcion = true, nivelTitulo = 'h3' }: VideoTutorialProps) {
  const [fallo, setFallo] = useState(false)
  const idTranscripcion = useId()
  const Titulo = nivelTitulo

  useEffect(() => setFallo(false), [tutorial.id])

  return (
    <figure
      className="m-0 overflow-hidden rounded-2xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900"
      data-testid={`video-${tutorial.id}`}
    >
      <div className="aspect-video w-full bg-gray-900">
        {fallo ? (
          <div role="status" className="flex h-full w-full flex-col items-center justify-center gap-1 px-4 text-center text-sm text-gray-200">
            <span aria-hidden="true" className="text-2xl">
              🎬
            </span>
            <p className="font-medium">Este video aún no está disponible</p>
            <p className="text-xs text-gray-400">Mientras tanto, puedes leer los pasos que aparecen debajo.</p>
          </div>
        ) : (
          <video
            key={tutorial.id}
            className="h-full w-full"
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
        )}
      </div>

      <figcaption className="p-4">
        <Titulo className="text-base font-semibold text-gray-900 dark:text-gray-100">
          {tutorial.titulo}{' '}
          <span className="ml-1 text-xs font-normal text-gray-500 dark:text-gray-400">({tutorial.duracion})</span>
        </Titulo>
        {mostrarDescripcion && <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">{tutorial.descripcion}</p>}

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
