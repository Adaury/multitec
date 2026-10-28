import { useAuthStore } from '../lib/authStore'
import { PASOS_AYUDA, PREGUNTAS_FRECUENTES } from '../lib/contenidoAyuda'
import { tutorialPorId } from '../lib/tutoriales'
import type { CurrentUser } from '../lib/types'
import { VideoTutorial } from '../components/VideoTutorial'
import { Card } from '../components/ui'

const TITULO_SECCION = 'text-base font-semibold text-gray-900 dark:text-gray-100'

function puedeVer(user: CurrentUser | null, roles?: string[], soloPlataforma?: boolean): boolean {
  if (soloPlataforma) return Boolean(user?.is_platform_admin)
  if (!roles) return true
  return user ? roles.includes(user.role) : false
}

/** Ayuda para todos los roles: la guía completa en video, el paso a paso (cada paso con su video corto y sus pasos en
 * texto) y las preguntas frecuentes. Cada persona ve lo que le corresponde según su rol. */
export function Ayuda() {
  const user = useAuthStore((s) => s.user)
  const guia = tutorialPorId('00-guia-completa')
  const pasos = PASOS_AYUDA.filter((p) => puedeVer(user, p.roles, p.soloPlataforma))
  const preguntas = PREGUNTAS_FRECUENTES.filter((q) => puedeVer(user, q.roles))

  return (
    <div className="mx-auto max-w-5xl pb-6">
      <h1 className="mb-1 text-xl font-semibold text-gray-900 dark:text-gray-100">Ayuda</h1>
      <p className="mb-4 text-sm text-gray-600 dark:text-gray-300">
        Aprende a usar Multitec paso a paso, con videos cortos. Si prefieres leer, cada video trae sus pasos en texto.
      </p>

      <nav aria-label="Contenido de la ayuda" className="mb-6 flex flex-wrap gap-2 text-sm">
        {[
          { href: '#guia', texto: 'Guía completa' },
          { href: '#paso-a-paso', texto: 'Paso a paso' },
          { href: '#preguntas', texto: 'Preguntas frecuentes' },
        ].map((enlace) => (
          <a
            key={enlace.href}
            href={enlace.href}
            className="rounded-full border border-gray-300 px-3 py-1 text-brand-blue hover:bg-gray-100 dark:border-gray-600 dark:hover:bg-gray-800"
          >
            {enlace.texto}
          </a>
        ))}
      </nav>

      {guia && (
        <section id="guia" aria-labelledby="titulo-guia" className="mb-10 scroll-mt-4">
          <h2 id="titulo-guia" className={`mb-3 ${TITULO_SECCION}`}>
            Guía completa (4 minutos)
          </h2>
          <div className="max-w-3xl">
            <VideoTutorial tutorial={guia} nivelTitulo="h3" />
          </div>
        </section>
      )}

      <section id="paso-a-paso" aria-labelledby="titulo-paso-a-paso" className="mb-10 scroll-mt-4">
        <h2 id="titulo-paso-a-paso" className={`mb-3 ${TITULO_SECCION}`}>
          Cómo funciona, paso a paso
        </h2>
        <div className="space-y-4">
          {pasos.map((paso, indice) => {
            const tutorial = paso.tutorialId ? tutorialPorId(paso.tutorialId) : undefined
            return (
              <Card key={paso.id} testId={`ayuda-paso-${paso.id}`}>
                <section aria-labelledby={`paso-${paso.id}`}>
                  <div className={`grid gap-4 ${tutorial ? 'md:grid-cols-2' : ''}`}>
                    <div>
                      <h3
                        id={`paso-${paso.id}`}
                        className="flex items-start gap-2 font-semibold text-gray-900 dark:text-gray-100"
                      >
                        <span
                          aria-hidden="true"
                          className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand-blue text-xs text-white"
                        >
                          {indice + 1}
                        </span>
                        <span>{paso.titulo}</span>
                      </h3>
                      <p className="mb-2 ml-8 text-xs text-gray-500 dark:text-gray-400">{paso.donde}</p>
                      <ol className="ml-8 list-decimal space-y-1.5 pl-4 text-sm text-gray-700 dark:text-gray-300">
                        {paso.pasos.map((texto) => (
                          <li key={texto}>{texto}</li>
                        ))}
                      </ol>
                      {paso.consejo && (
                        <p className="ml-8 mt-3 rounded-xl bg-gray-50 p-3 text-sm text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                          <strong>Consejo: </strong>
                          {paso.consejo}
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

      <section id="preguntas" aria-labelledby="titulo-preguntas" className="mb-6 scroll-mt-4">
        <h2 id="titulo-preguntas" className={`mb-3 ${TITULO_SECCION}`}>
          Preguntas frecuentes
        </h2>
        <div className="space-y-2">
          {preguntas.map((item) => (
            <details
              key={item.pregunta}
              className="rounded-2xl border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-900"
            >
              <summary className="cursor-pointer text-sm font-medium text-gray-900 dark:text-gray-100">
                {item.pregunta}
              </summary>
              <p className="mt-2 text-sm text-gray-700 dark:text-gray-300">{item.respuesta}</p>
            </details>
          ))}
        </div>
      </section>
    </div>
  )
}
