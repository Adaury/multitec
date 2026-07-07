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
        <Textarea value={form.address ?? ''} onChange={(e) => setForm({ ...form, address: e.target.value })} />
      </Field>
      <Field label="Observaciones">
        <Textarea value={form.notes ?? ''} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
      </Field>
    </>
  )
}
