import { QueryClient } from '@tanstack/react-query'

/** Cliente de consultas compartido: también lo usan tareas que viven fuera de los componentes
 * (ver generationStore), para refrescar las listas aunque la pantalla que las pidió ya se cerró. */
export const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 10_000 } },
})
