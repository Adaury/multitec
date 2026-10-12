// Cola de levantamientos hechos sin conexión. Se guarda en IndexedDB (aguanta cerrar la app y
// admite las fotos como Blob; localStorage no sirve para eso). Un levantamiento pendiente es
// todo lo que el técnico pudo capturar sin servidor: datos del cliente, tipo, ubicación, notas
// y fotos. La cotización con IA se genera después, ya con señal.

export interface PendingSurvey {
  id: string
  createdAt: number
  clientName: string
  phone: string
  surveyType: string
  address: string
  locationUrl: string
  notes: string
  photos: Blob[]
  /** Se llena cuando el proyecto ya se creó en el servidor: un reintento no lo duplica. */
  projectId?: number
  lastError?: string
}

const DB_NAME = 'multitec-offline'
const STORE = 'pending-surveys'
const CHANGE_EVENT = 'multitec:pending-surveys-changed'

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1)
    request.onupgradeneeded = () => {
      request.result.createObjectStore(STORE, { keyPath: 'id' })
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

async function run<T>(mode: IDBTransactionMode, action: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await openDb()
  try {
    return await new Promise<T>((resolve, reject) => {
      const request = action(db.transaction(STORE, mode).objectStore(STORE))
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  } finally {
    db.close()
  }
}

function notifyChange() {
  window.dispatchEvent(new Event(CHANGE_EVENT))
}

export async function addPendingSurvey(data: Omit<PendingSurvey, 'id' | 'createdAt'>): Promise<PendingSurvey> {
  const record: PendingSurvey = { ...data, id: crypto.randomUUID(), createdAt: Date.now() }
  await run('readwrite', (store) => store.put(record))
  notifyChange()
  return record
}

export async function updatePendingSurvey(record: PendingSurvey): Promise<void> {
  await run('readwrite', (store) => store.put(record))
  notifyChange()
}

export async function removePendingSurvey(id: string): Promise<void> {
  await run('readwrite', (store) => store.delete(id))
  notifyChange()
}

export async function listPendingSurveys(): Promise<PendingSurvey[]> {
  const all = await run('readonly', (store) => store.getAll() as IDBRequest<PendingSurvey[]>)
  return all.sort((a, b) => a.createdAt - b.createdAt)
}

/** Avisa a quien muestre el contador cada vez que la cola cambia. Devuelve la función de baja. */
export function onPendingSurveysChange(callback: () => void): () => void {
  window.addEventListener(CHANGE_EVENT, callback)
  return () => window.removeEventListener(CHANGE_EVENT, callback)
}
