/** Relleno mientras se descarga la pantalla (cada pantalla es un archivo aparte). Se muestra
 * dentro del Layout, así que la barra de navegación no desaparece ni parpadea. */
export function PageLoader() {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-sm text-gray-500 dark:text-gray-400" role="status">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-brand-blue" />
      Cargando…
    </div>
  )
}
