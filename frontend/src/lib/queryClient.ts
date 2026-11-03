import { MutationCache, QueryClient } from '@tanstack/react-query'
import { apiErrorMessage } from './api'
import { useToastStore } from './toastStore'

/** Cliente de consultas compartido: también lo usan tareas que viven fuera de los componentes
 * (ver generationStore), para refrescar las listas aunque la pantalla que las pidió ya se cerró. */
export const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 10_000 } },
  mutationCache: new MutationCache({
    // Red de seguridad: una acción (guardar, aprobar, subir…) que falla y cuya pantalla no lo cuenta dejaba a la persona
    // sin saber si se hizo o no. Si la acción ya maneja su propio error (onError) no se duplica el aviso.
    onError: (error, _variables, _context, mutation) => {
      if (mutation.options.onError || mutation.meta?.silent) return
      const status = (error as { response?: { status?: number } }).response?.status
      if (status === 401) return // la sesión venció: la app ya la cierra y lleva al inicio
      useToastStore
        .getState()
        .push(apiErrorMessage(error, 'No se pudo completar la acción. Revisa tu conexión e intenta de nuevo.'))
    },
  }),
})
