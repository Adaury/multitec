// localStorage que nunca tumba la aplicación. En Safari con las cookies bloqueadas, en modo privado o con restricciones
// del dispositivo, tocar localStorage LANZA un error; si eso pasa mientras arranca la app, queda una pantalla vacía sin
// ningún mensaje. Aquí un fallo de almacenamiento solo significa «no se recuerda»: la sesión dura hasta recargar.
export const safeStorage = {
  get(key: string): string | null {
    try {
      return localStorage.getItem(key)
    } catch {
      return null
    }
  },
  set(key: string, value: string): void {
    try {
      localStorage.setItem(key, value)
    } catch {
      // sin almacenamiento: no se recuerda, pero la app sigue
    }
  },
  remove(key: string): void {
    try {
      localStorage.removeItem(key)
    } catch {
      // ídem
    }
  },
}
