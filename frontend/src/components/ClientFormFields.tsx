import type { ClientInput } from '../lib/types'
import { Field, Input, Textarea } from './ui'

export function ClientFormFields({
  form,
  setForm,
}: {
  form: ClientInput
  setForm: (form: ClientInput) => void
}) {
  return (
    <>
      <div className="grid gap-3 md:grid-cols-2">
        <Field label="Nombre">
          <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <Field label="Empresa">
          <Input value={form.company ?? ''} onChange={(e) => setForm({ ...form, company: e.target.value })} />
        </Field>
        <Field label="RNC">
          <Input value={form.rnc ?? ''} onChange={(e) => setForm({ ...form, rnc: e.target.value })} />
        </Field>
        <Field label="Teléfono">
          <Input value={form.phone ?? ''} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        </Field>
        <Field label="Correo">
          <Input
            type="email"
            value={form.email ?? ''}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
        </Field>
      </div>
      <Field label="Dirección">
        <div className="space-y-2">
          <Textarea value={form.address ?? ''} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          <button
            type="button"
            onClick={() => {
              const query = form.address?.trim() || form.name
              window.open(
                `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`,
                '_blank',
                'noopener,noreferrer',
              )
            }}
            className="rounded-full bg-brand-gray px-3 py-1.5 text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300"
          >
            📍 Marcar en Google Maps
          </button>
        </div>
      </Field>
      <Field label="Enlace de ubicación (Google Maps)">
        <Input
          placeholder="Pega aquí el enlace que copiaste de Google Maps"
          value={form.location_url ?? ''}
          onChange={(e) => setForm({ ...form, location_url: e.target.value })}
        />
        <p className="mt-1 text-xs text-gray-400">
          En Maps: toca el pin marcado → Compartir → Copiar enlace, y pégalo aquí.
        </p>
      </Field>
      <Field label="Observaciones">
        <Textarea value={form.notes ?? ''} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
      </Field>
    </>
  )
}
