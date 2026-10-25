import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, apiErrorMessage } from '../lib/api'
import { Button, Card, Field, Input, Textarea } from '../components/ui'

interface Company {
  name: string
  tagline: string
  representative: string
  rnc: string
  cedula: string
  address: string
  phone: string
  email: string
  website: string
  bank_info: string
  invoice_notes: string
  has_logo: boolean
}

type CompanyForm = Omit<Company, 'has_logo'>

/** Datos de la empresa y logo: lo que sale en el membrete de cotizaciones y facturas. */
export function Empresa() {
  const queryClient = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [form, setForm] = useState<CompanyForm | null>(null)
  const [logoVersion, setLogoVersion] = useState(0)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const { data: company } = useQuery({
    queryKey: ['company'],
    queryFn: async () => (await api.get<Company>('/company')).data,
  })

  useEffect(() => {
    if (company && form === null) {
      const { has_logo: _hasLogo, ...fields } = company
      setForm(fields)
    }
  }, [company, form])

  // La vista previa se pide con la sesión (el logo no es público): se baja como imagen y se muestra.
  const { data: logoUrl } = useQuery({
    queryKey: ['company-logo', company?.has_logo, logoVersion],
    queryFn: async () => URL.createObjectURL((await api.get('/company/logo', { responseType: 'blob' })).data),
    enabled: !!company?.has_logo,
    staleTime: Infinity,
  })

  const save = useMutation({
    mutationFn: async (fields: CompanyForm) => (await api.put<Company>('/company', fields)).data,
    onSuccess: (saved) => {
      queryClient.setQueryData(['company'], saved)
      setError(null)
      setMessage('Datos guardados. Los PDF nuevos ya salen con ellos.')
    },
    onError: (err) => setError(apiErrorMessage(err, 'No se pudieron guardar los datos')),
  })

  const uploadLogo = useMutation({
    mutationFn: async (file: File) => {
      const body = new FormData()
      body.append('file', file)
      return (await api.post<Company>('/company/logo', body)).data
    },
    onSuccess: (saved) => {
      queryClient.setQueryData(['company'], saved)
      setLogoVersion((v) => v + 1)
      setError(null)
      setMessage('Logo actualizado.')
    },
    onError: (err) => setError(apiErrorMessage(err, 'No se pudo subir el logo')),
  })

  const removeLogo = useMutation({
    mutationFn: async () => (await api.delete<Company>('/company/logo')).data,
    onSuccess: (saved) => {
      queryClient.setQueryData(['company'], saved)
      setLogoVersion((v) => v + 1)
      setError(null)
      setMessage('Logo quitado: los PDF salen con el nombre de la empresa.')
    },
    onError: (err) => setError(apiErrorMessage(err, 'No se pudo quitar el logo')),
  })

  if (!form || !company) return <p className="text-sm text-gray-500">Cargando…</p>

  const text = (key: keyof CompanyForm, label: string, placeholder?: string) => (
    <Field label={label}>
      <Input value={form[key]} placeholder={placeholder} onChange={(e) => setForm({ ...form, [key]: e.target.value })} />
    </Field>
  )

  return (
    <div className="space-y-4 md:space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Mi empresa</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Estos datos y el logo salen en el membrete de las cotizaciones, facturas y presupuestos.
        </p>
      </div>

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      {message && !error && (
        <p role="status" className="text-sm text-green-700 dark:text-green-400">
          {message}
        </p>
      )}

      {/* Pantalla ancha (xl): el logo a la izquierda y el formulario a la derecha; antes quedaba una sola
          columna angosta con un tercio de la pantalla vacío. */}
      <div className="space-y-4 md:space-y-6 xl:grid xl:grid-cols-[22rem_minmax(0,1fr)] xl:items-start xl:gap-8 xl:space-y-0">
      <Card className="space-y-3 md:max-w-2xl xl:max-w-none">
        <p className="font-medium text-gray-800 dark:text-gray-200">Logo</p>
        <div className="flex h-28 items-center justify-center rounded-xl bg-white p-3 ring-1 ring-gray-200 dark:ring-gray-700">
          {company.has_logo && logoUrl ? (
            <img src={logoUrl} alt="Logo de la empresa" className="max-h-full max-w-full object-contain" />
          ) : (
            <p className="text-sm text-gray-400">Sin logo: se imprime el nombre de la empresa.</p>
          )}
        </div>
        <input
          ref={fileRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          aria-label="Archivo del logo"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) uploadLogo.mutate(file)
            e.target.value = ''
          }}
        />
        <div className="flex gap-2">
          <Button type="button" className="!w-auto flex-1" onClick={() => fileRef.current?.click()} disabled={uploadLogo.isPending}>
            {uploadLogo.isPending ? 'Subiendo…' : company.has_logo ? 'Cambiar logo' : 'Subir logo'}
          </Button>
          {company.has_logo && (
            <Button
              type="button"
              variant="secondary"
              className="!w-auto"
              onClick={() => removeLogo.mutate()}
              disabled={removeLogo.isPending}
            >
              Quitar
            </Button>
          )}
        </div>
        <p className="text-xs text-gray-400">
          PNG, JPG o WebP. El margen en blanco se recorta solo para que el logo no salga pequeño en el PDF.
        </p>
      </Card>

      <Card className="md:max-w-2xl xl:max-w-3xl">
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault()
            setMessage(null)
            save.mutate(form)
          }}
        >
          {text('name', 'Nombre de la empresa')}
          {text('tagline', 'Lema (opcional)', 'Servicios de calidad')}
          {text('representative', 'Responsable', 'Ing. Nombre Apellido')}
          <div className="grid gap-3 sm:grid-cols-2">
            {text('rnc', 'RNC')}
            {text('cedula', 'Cédula (si factura una persona)')}
          </div>
          {text('address', 'Dirección')}
          <div className="grid gap-3 sm:grid-cols-2">
            {text('phone', 'Teléfono')}
            {text('email', 'Correo')}
          </div>
          {text('website', 'Sitio web (opcional)')}
          <Field label="Cuentas para depósito o transferencia (una por línea)">
            <Textarea
              rows={3}
              value={form.bank_info}
              onChange={(e) => setForm({ ...form, bank_info: e.target.value })}
            />
          </Field>
          <Field label="Mensaje al pie de la factura (opcional)">
            <Textarea
              rows={2}
              value={form.invoice_notes}
              placeholder="Gracias por su preferencia."
              onChange={(e) => setForm({ ...form, invoice_notes: e.target.value })}
            />
          </Field>
          <Button type="submit" disabled={save.isPending}>
            {save.isPending ? 'Guardando…' : 'Guardar datos'}
          </Button>
        </form>
      </Card>
      </div>
    </div>
  )
}
