import { Lightbulb, MapPin, PlayCircle, Video } from 'lucide-react'
import { useAuthStore } from '../lib/authStore'
import { PASOS_AYUDA, PREGUNTAS_FRECUENTES } from '../lib/contenidoAyuda'
import { posterUrl, tutorialPorId } from '../lib/tutoriales'
import type { CurrentUser } from '../lib/types'
import { VideoTutorial } from '../components/VideoTutorial'
import { Card } from '../components/ui'

const TITULO_SECCION = 'flex items-center gap-2 text-lg font-bold text-gray-900 md:text-xl dark:text-gray-100'

function puedeVer(user: CurrentUser | null, roles?: string[], soloPlataforma?: boolean): boolean {
  if (soloPlataforma) return Boolean(user?.is_platform_admin)
  if (!roles) return true
  return user ? roles.includes(user.role) : false
}

/** Ayuda para todos los roles: la guía completa en video, una videoteca con la vista previa de cada tema, el paso a paso
 * (cada paso con su video corto y sus pasos en texto) y las preguntas frecuentes. Cada persona ve lo que le corresponde
 * según su rol. Cada video se puede descargar o enviar a otra persona. */
export function Ayuda() {
  const user = useAuthStore((s) => s.user)
  const guia = tutorialPorId('00-guia-completa')
  const pasos = PASOS_AYUDA.filter((p) => puedeVer(user, p.roles, p.soloPlataforma))
  const preguntas = PREGUNTAS_FRECUENTES.filter((q) => puedeVer(user, q.roles))
  const conVideo = pasos.filter((p) => p.tutorialId && tutorialPorId(p.tutorialId))

  return (
    <div className="mx-auto max-w-6xl space-y-8 py-4 md:space-y-10 md:py-8">
      <h1 className="sr-only">Ayuda</h1>

      <nav aria-label="Contenido de la ayuda" className="flex flex-wrap justify-center gap-2 text-sm">
        {[
          { href: '#guia', texto: 'Guía completa' },
          { href: '#videoteca', texto: 'Todos los videos' },
          { href: '#paso-a-paso', texto: 'Paso a paso' },
          { href: '#preguntas', texto: 'Preguntas frecuentes' },
        ].map((enlace) => (
          <a
            key={enlace.href}
            href={enlace.href}
            className="rounded-full bg-white px-4 py-2 font-medium text-brand-blue shadow-sm ring-1 ring-black/5 hover:bg-blue-50 dark:bg-gray-900 dark:text-blue-300 dark:ring-white/10 dark:hover:bg-gray-800"
          >
            {enlace.texto}
          </a>
        ))}
      </nav>

      {guia && (
        <section id="guia" aria-labelledby="titulo-guia" className="scroll-mt-24">
          <h2 id="titulo-guia" className={`mb-3 ${TITULO_SECCION}`}>
            <PlayCircle className="h-6 w-6 text-brand-blue" aria-hidden="true" />
            Guía completa ({guia.duracion})
          </h2>
          <p className="mb-4 text-sm text-gray-600 dark:text-gray-300">
            Aprende a usar Multitec de principio a fin. Si prefieres leer, cada video trae sus pasos en texto.
          </p>
          <div className="mx-auto max-w-4xl">
            <VideoTutorial tutorial={guia} nivelTitulo="h3" />
          </div>
        </section>
      )}

      {conVideo.length > 0 && (
        <section id="videoteca" aria-labelledby="titulo-videoteca" className="scroll-mt-24">
          <h2 id="titulo-videoteca" className={`mb-4 ${TITULO_SECCION}`}>
            <Video className="h-6 w-6 text-brand-blue" aria-hidden="true" />
            Todos los videos
          </h2>
          {/* Vista previa de cada tema: la portada lleva al paso con su video, sus pasos y los botones para enviarlo. */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:gap-4 lg:grid-cols-4">
            {conVideo.map((paso) => {
              const tutorial = tutorialPorId(paso.tutorialId!)!
              return (
                <a
                  key={paso.id}
                  href={`#paso-${paso.id}`}
                  className="group overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-black/5 transition hover:-translate-y-0.5 hover:shadow-md dark:bg-gray-900 dark:ring-white/10"
                >
                  <span className="relative block aspect-video bg-gray-900">
                    <img
                      src={posterUrl(tutorial.id)}
                      alt=""
                      loading="lazy"
                      className="h-full w-full object-cover opacity-90 transition group-hover:opacity-100"
                    />
                    <span className="absolute inset-0 flex items-center justify-center">
                      <span className="flex h-11 w-11 items-center justify-center rounded-full bg-white/90 text-brand-blue shadow-lg transition group-hover:scale-110">
                        <PlayCircle className="h-7 w-7" aria-hidden="true" />
                      </span>
                    </span>
                    <span className="absolute bottom-1.5 right-1.5 rounded-md bg-black/75 px-1.5 py-0.5 text-[0.65rem] font-semibold text-white">
                      {tutorial.duracion}
                    </span>
                  </span>
                  <span className="block p-3">
                    <span className="line-clamp-2 text-sm font-semibold leading-snug text-gray-900 dark:text-gray-100">
                      {tutorial.titulo}
                    </span>
                  </span>
                </a>
              )
            })}
          </div>
        </section>
      )}

      <section id="paso-a-paso" aria-labelledby="titulo-paso-a-paso" className="scroll-mt-24">
        <h2 id="titulo-paso-a-paso" className={`mb-4 ${TITULO_SECCION}`}>
          <Lightbulb className="h-6 w-6 text-brand-blue" aria-hidden="true" />
          Cómo funciona, paso a paso
        </h2>
        <div className="space-y-4">
          {pasos.map((paso, indice) => {
            const tutorial = paso.tutorialId ? tutorialPorId(paso.tutorialId) : undefined
            return (
              <Card key={paso.id} testId={`ayuda-paso-${paso.id}`} className="md:p-6">
                <section id={`paso-${paso.id}`} aria-labelledby={`titulo-paso-${paso.id}`} className="scroll-mt-24">
                  <div className={`grid gap-5 ${tutorial ? 'lg:grid-cols-[1fr_1.1fr]' : ''}`}>
                    <div>
                      <h3
                        id={`titulo-paso-${paso.id}`}
                        className="flex items-start gap-3 text-base font-bold text-gray-900 md:text-lg dark:text-gray-100"
                      >
                        <span
                          aria-hidden="true"
                          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-blue to-blue-800 text-sm text-white shadow-sm"
                        >
                          {indice + 1}
                        </span>
                        <span className="pt-0.5">{paso.titulo}</span>
                      </h3>
                      <p className="mb-3 ml-11 mt-1 inline-flex items-center gap-1 rounded-full bg-brand-gray px-2.5 py-1 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-400">
                        <MapPin className="h-3.5 w-3.5" aria-hidden="true" />
                        {paso.donde}
                      </p>
                      <ol className="ml-11 list-decimal space-y-2 pl-4 text-sm leading-relaxed text-gray-700 marker:font-semibold marker:text-brand-blue dark:text-gray-300">
                        {paso.pasos.map((texto) => (
                          <li key={texto}>{texto}</li>
                        ))}
                      </ol>
                      {paso.consejo && (
                        <p className="ml-11 mt-4 flex gap-2 rounded-xl bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
                          <Lightbulb className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                          <span>
                            <strong>Consejo: </strong>
                            {paso.consejo}
                          </span>
                        </p>
                      )}
                    </div>
                    {tutorial && <VideoTutorial tutorial={tutorial} mostrarDescripcion={false} nivelTitulo="h4" />}
                  </div>
                </section>
              </Card>
            )
          })}
        </div>
      </section>

      <section id="preguntas" aria-labelledby="titulo-preguntas" className="scroll-mt-24">
        <h2 id="titulo-preguntas" className={`mb-4 ${TITULO_SECCION}`}>
          <span aria-hidden="true" className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-blue text-sm text-white">
            ?
          </span>
          Preguntas frecuentes
        </h2>
        <div className="grid gap-3 md:grid-cols-2">
          {preguntas.map((item) => (
            <details
              key={item.pregunta}
              className="group rounded-2xl bg-white p-4 shadow-sm ring-1 ring-black/5 open:ring-brand-blue/30 dark:bg-gray-900 dark:ring-white/10"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-semibold text-gray-900 dark:text-gray-100 [&::-webkit-details-marker]:hidden">
                {item.pregunta}
                <span aria-hidden="true" className="text-brand-blue transition group-open:rotate-45">
                  +
                </span>
              </summary>
              <p className="mt-2 text-sm leading-relaxed text-gray-700 dark:text-gray-300">{item.respuesta}</p>
            </details>
          ))}
        </div>
      </section>
    </div>
  )
}
