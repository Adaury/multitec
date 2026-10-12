import { useRef, useState } from 'react'
import { addPendingSurvey } from '../lib/offlineQueue'
import { shrinkImage } from '../lib/imageUpload'
import { useGeolocation } from '../lib/useGeolocation'
import { SURVEY_TYPES } from '../lib/surveyTypes'
import { Button, Card, Field, Input, Textarea } from './ui'

/** Levantamiento sin señal: lo esencial (cliente, tipo, notas, fotos, GPS) queda guardado en el
 * teléfono y se envía solo cuando vuelve la conexión. La cotización con IA se pide después. */
export function OfflineSurveyForm() {
  const photoInputRef = useRef<HTMLInputElement>(null)
  const [clientName, setClientName] = useState('')
  const [phone, setPhone] = useState('')
  const [surveyType, setSurveyType] = useState('')
  const [address, setAddress] = useState('')
  const [locationUrl, setLocationUrl] = useState('')
  const [notes, setNotes] = useState('')
  const [photos, setPhotos] = useState<Blob[]>([])
  const [saving, setSaving] = useState(false)
  const [savedCount, setSavedCount] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const gps = useGeolocation(setLocationUrl, { auto: true })

  const addPhoto = async (file: File) => {
    setPhotos((prev) => [...prev, file])
    // Se reduce en segundo plano: la foto original ya está guardada y se reemplaza por la liviana.
    const small = await shrinkImage(file)
    if (small !== file) setPhotos((prev) => prev.map((p) => (p === file ? small : p)))
  }

  const save = async () => {
    setSaving(true)
    setError(null)
    try {
      await addPendingSurvey({
        clientName: clientName.trim(),
        phone,
        surveyType,
        address,
        locationUrl,
        notes,
        photos,
      })
      setSavedCount((n) => n + 1)
      setClientName('')
      setPhone('')
      setSurveyType('')
      setAddress('')
      setNotes('')
      setPhotos([])
    } catch {
      setError('No se pudo guardar en este teléfono. Revisa que el navegador permita almacenamiento.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-3 py-3">
      <Card className="space-y-1 bg-amber-50 ring-amber-200 dark:bg-amber-950 dark:ring-amber-900">
        <p className="font-semibold text-gray-900 dark:text-gray-100">📴 Sin conexión</p>
        <p className="text-sm text-gray-700 dark:text-gray-300">
          Anota lo del levantamiento y toma las fotos. Se guarda en este teléfono y se envía solo cuando vuelva la
          señal. La cotización con IA la generas después, ya conectado.
        </p>
      </Card>

      {savedCount > 0 && (
        <p role="status" className="rounded-2xl bg-green-50 px-4 py-3 text-sm font-medium text-green-800 dark:bg-green-950 dark:text-green-300">
          ✅ Guardado en el teléfono ({savedCount}). Se enviará cuando haya conexión.
        </p>
      )}

      <Card className="space-y-3">
        <Field label="Cliente">
          <Input value={clientName} onChange={(e) => setClientName(e.target.value)} placeholder="Nombre del cliente" />
        </Field>
        <Field label="Teléfono">
          <Input value={phone} inputMode="tel" onChange={(e) => setPhone(e.target.value)} placeholder="809-000-0000" />
        </Field>
        <div className="flex flex-wrap gap-2">
          {SURVEY_TYPES.map((t) => (
            <button
              key={t}
              type="button"
              aria-pressed={surveyType === t}
              onClick={() => setSurveyType(surveyType === t ? '' : t)}
              className={`rounded-full px-4 py-2 text-sm font-medium ${
                surveyType === t
                  ? 'bg-brand-blue text-white'
                  : 'bg-brand-gray text-gray-800 dark:bg-gray-800 dark:text-gray-100'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
        <Field label="Dirección / referencia">
          <Input value={address} onChange={(e) => setAddress(e.target.value)} />
        </Field>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          {locationUrl ? gps.note ?? '📍 Ubicación capturada' : gps.locating ? 'Buscando ubicación…' : gps.note}
        </p>
        <Field label="Notas del levantamiento">
          <Textarea
            rows={5}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Ej.: 8 cámaras IP exteriores, un NVR, cable UTP cat 6, 40 m por cámara…"
          />
        </Field>

        <input
          ref={photoInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          data-testid="offline-photo-input"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) void addPhoto(file)
            e.target.value = ''
          }}
        />
        <Button variant="secondary" onClick={() => photoInputRef.current?.click()}>
          📷 Tomar foto {photos.length > 0 && `(${photos.length})`}
        </Button>

        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
        <Button onClick={() => void save()} disabled={saving || clientName.trim().length === 0}>
          {saving ? 'Guardando…' : 'Guardar para enviar después'}
        </Button>
      </Card>
    </div>
  )
}
