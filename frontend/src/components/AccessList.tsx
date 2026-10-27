import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api, apiErrorMessage } from '../lib/api'
import { Button, Input } from './ui'

export interface AccessAccount {
  user_id: number
  name: string
  email: string
  role: string
  temporary_password: string
}

const small = '!w-auto !px-3 !py-1.5 text-xs'

function fileName(company: string): string {
  const slug = company
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
  return `acceso-${slug || 'empresa'}.txt`
}

/** Cuentas recién creadas con su clave temporal (se ven solo ahora): editar la clave, descargar todo en un archivo y
 * mandar el enlace de acceso por WhatsApp o correo. */
export function AccessList({
  companyId,
  companyName,
  accounts,
  validity,
}: {
  companyId: number
  companyName: string
  accounts: AccessAccount[]
  /** «Vence en 14 días», para ponerlo en el archivo y en los mensajes. */
  validity?: string | null
}) {
  const [items, setItems] = useState(accounts)
  const [editing, setEditing] = useState<number | null>(null)
  const [draft, setDraft] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const loginUrl = `${window.location.origin}/login`

  const message = (a: AccessAccount) =>
    [
      `Hola ${a.name}, ya tienes acceso a ${companyName} en Multitec.`,
      `Entra aquí: ${loginUrl}`,
      `Correo: ${a.email}`,
      `Clave temporal: ${a.temporary_password}`,
      'Al entrar te pedirá cambiar la clave.',
      validity ? `${validity}.` : '',
    ]
      .filter(Boolean)
      .join('\n')

  const save = useMutation({
    mutationFn: async (a: AccessAccount) =>
      (
        await api.post<{ temporary_password: string }>(`/platform/companies/${companyId}/users/${a.user_id}/password`, {
          password: draft.trim() || null,
        })
      ).data.temporary_password,
    onSuccess: (password, a) => {
      setItems((list) => list.map((x) => (x.user_id === a.user_id ? { ...x, temporary_password: password } : x)))
      setEditing(null)
      setDraft('')
      setError(null)
    },
    onError: (e) => setError(apiErrorMessage(e, 'No se pudo cambiar la clave')),
  })

  const download = () => {
    const text = [
      `Acceso a ${companyName} (Multitec)`,
      validity ?? '',
      '',
      `Enlace: ${loginUrl}`,
      'Cada persona debe cambiar su clave al entrar.',
      '',
      ...items.map((a) => `${a.name} (${a.role})\n  Correo: ${a.email}\n  Clave temporal: ${a.temporary_password}\n`),
    ].join('\n')
    const url = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = fileName(companyName)
    link.click()
    URL.revokeObjectURL(url)
  }

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(loginUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      window.prompt('Copia el enlace:', loginUrl)
    }
  }

  return (
    <div className="mt-3 space-y-3">
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" className={small} onClick={download}>
          Descargar archivo
        </Button>
        <Button variant="secondary" className={small} onClick={copyLink}>
          {copied ? 'Enlace copiado' : 'Copiar enlace de acceso'}
        </Button>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <ul className="space-y-2 text-sm">
        {items.map((a) => (
          <li key={a.user_id} className="rounded-xl bg-gray-50 px-3 py-2 dark:bg-gray-800/60" data-testid="demo-account">
            <p className="font-medium text-gray-900 dark:text-gray-100">
              {a.name} <span className="text-xs font-normal text-gray-500">({a.role})</span>
            </p>
            <p className="font-mono text-xs">{a.email}</p>
            <p className="font-mono text-xs" data-testid="temporary-password">
              {a.temporary_password}
            </p>
            {editing === a.user_id ? (
              <form
                className="mt-2 flex flex-wrap items-center gap-2"
                onSubmit={(e) => {
                  e.preventDefault()
                  save.mutate(a)
                }}
              >
                <Input
                  aria-label={`Nueva clave de ${a.name}`}
                  placeholder="Escribe la clave (vacío = al azar)"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  className="!w-64 !py-1.5 !text-sm"
                />
                <Button type="submit" className={small} disabled={save.isPending}>
                  Guardar
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  className={small}
                  onClick={() => {
                    setEditing(null)
                    setDraft('')
                    setError(null)
                  }}
                >
                  Cancelar
                </Button>
              </form>
            ) : (
              <div className="mt-2 flex flex-wrap gap-2">
                <Button
                  variant="secondary"
                  className={small}
                  onClick={() => {
                    setEditing(a.user_id)
                    setDraft('')
                    setError(null)
                  }}
                >
                  Editar clave
                </Button>
                <a
                  className="rounded-2xl bg-brand-gray px-3 py-1.5 text-xs font-medium text-gray-800 dark:bg-gray-800 dark:text-gray-100"
                  href={`https://wa.me/?text=${encodeURIComponent(message(a))}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Enviar por WhatsApp
                </a>
                <a
                  className="rounded-2xl bg-brand-gray px-3 py-1.5 text-xs font-medium text-gray-800 dark:bg-gray-800 dark:text-gray-100"
                  href={`mailto:?subject=${encodeURIComponent(`Acceso a ${companyName}`)}&body=${encodeURIComponent(message(a))}`}
                >
                  Enviar por correo
                </a>
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
