import { api } from './api'
import { listPendingSurveys, removePendingSurvey, updatePendingSurvey, type PendingSurvey } from './offlineQueue'
import { surveyDescription } from './surveyTypes'
import type { Client, Project } from './types'

let syncing = false

function isNetworkError(err: unknown): boolean {
  // axios: sin `response` = no hubo respuesta del servidor (sin señal, servidor caído, túnel cerrado).
  return typeof err === 'object' && err !== null && !(err as { response?: unknown }).response
}

async function sendOne(item: PendingSurvey): Promise<void> {
  let record = item

  let projectId = record.projectId
  if (projectId === undefined) {
    const clients = (await api.get<Client[]>('/clients')).data
    const wanted = record.clientName.trim().toLowerCase()
    let client = clients.find((c) => c.name.trim().toLowerCase() === wanted)
    if (!client) {
      client = (
        await api.post<Client>('/clients', {
          name: record.clientName.trim(),
          company: null,
          rnc: null,
          phone: record.phone.trim() || null,
          email: null,
          notes: null,
          address: record.address.trim() || null,
          location_url: record.locationUrl.trim() || null,
        })
      ).data
    }
    const project = (
      await api.post<Project>('/projects', {
        client_id: client.id,
        description: surveyDescription(record.surveyType || null),
        survey_type: record.surveyType || null,
        address: record.address.trim() || null,
        location_url: record.locationUrl.trim() || null,
      })
    ).data
    projectId = project.id
    if (record.notes.trim()) {
      await api.put(`/projects/${projectId}/survey`, {
        notes: record.notes.trim(),
        measurements: '',
        observations: '',
      })
    }
    // Se anota enseguida: si una foto falla, el reintento no vuelve a crear el proyecto.
    record = { ...record, projectId }
    await updatePendingSurvey(record)
  }

  while (record.photos.length > 0) {
    const form = new FormData()
    form.append('kind', 'photo')
    form.append('file', record.photos[0], `foto-${Date.now()}.jpg`)
    await api.post(`/projects/${projectId}/survey/assets`, form)
    record = { ...record, photos: record.photos.slice(1) }
    await updatePendingSurvey(record)
  }

  await removePendingSurvey(record.id)
}

/** Envía al servidor los levantamientos guardados sin conexión. Se detiene en el primer fallo de
 * red (sigue sin señal); un error del servidor en un registro lo deja marcado y sigue con los demás. */
export async function syncPendingSurveys(): Promise<{ sent: number; failed: number; offline: boolean }> {
  if (syncing) return { sent: 0, failed: 0, offline: false }
  syncing = true
  let sent = 0
  let failed = 0
  try {
    for (const item of await listPendingSurveys()) {
      try {
        await sendOne(item)
        sent += 1
      } catch (err) {
        if (isNetworkError(err)) return { sent, failed, offline: true }
        failed += 1
        const detail = (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
        // Se relee el registro: sendOne pudo haber avanzado (proyecto creado, fotos enviadas).
        const fresh = (await listPendingSurveys()).find((p) => p.id === item.id) ?? item
        await updatePendingSurvey({
          ...fresh,
          lastError: typeof detail === 'string' ? detail : 'El servidor rechazó este levantamiento.',
        })
      }
    }
    return { sent, failed, offline: false }
  } finally {
    syncing = false
  }
}
