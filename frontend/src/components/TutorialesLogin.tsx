import { useState } from 'react'
import { tutorialPorId, type Tutorial } from '../lib/tutoriales'
import { VideoTutorial } from './VideoTutorial'

// Videos que se ven en la pantalla de entrada, sin iniciar sesión.
const IDS_LOGIN = ['01-entrar-al-sistema', '08-el-tecnico-en-el-iphone']

/** Sección plegable: los videos recién se cargan cuando la persona la abre, para no gastar datos ni ralentizar el inicio
 * de sesión (importante en el celular, en la obra). */
export function TutorialesLogin() {
  const [abierto, setAbierto] = useState(false)
  const tutoriales = IDS_LOGIN.map(tutorialPorId).filter((t): t is Tutorial => t !== undefined)

  return (
    <details
      className="mt-6 border-t border-gray-200 pt-4 text-sm dark:border-gray-700"
      onToggle={(e) => setAbierto(e.currentTarget.open)}
    >
      <summary className="cursor-pointer text-center font-medium text-brand-blue hover:underline">
        Aprende a usar el sistema
      </summary>
      {abierto && (
        <div className="mt-3 space-y-3">
          {tutoriales.map((tutorial) => (
            <VideoTutorial key={tutorial.id} tutorial={tutorial} mostrarDescripcion={false} nivelTitulo="h4" />
          ))}
          <p className="text-center text-xs text-gray-500 dark:text-gray-400">
            Al entrar encontrarás más videos y la guía completa en el menú <strong>Ayuda</strong>.
          </p>
        </div>
      )}
    </details>
  )
}
