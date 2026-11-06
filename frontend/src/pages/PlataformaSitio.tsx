import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Copy, ExternalLink, MessageCircle, Plus, Star } from 'lucide-react'
import { api, apiErrorMessage } from '../lib/api'
import { platformMoney, type SitePartner, type SitePlan, type SiteTestimonial } from '../lib/platformMoney'
import { Badge, Button, Card, Field, Input, Textarea } from '../components/ui'

interface SiteAdmin {
  currency: string
  plans: SitePlan[]
  testimonials: SiteTestimonial[]
  partners: SitePartner[]
}

const EMPTY_PLAN: Omit<SitePlan, 'id'> = {
  name: '',
  description: '',
  monthly_price: 0,
  setup_price: 0,
  max_users: null,
  features: [],
  highlighted: false,
  active: true,
  sort: 9,
}

const EMPTY_TESTIMONIAL: Omit<SiteTestimonial, 'id' | 'is_example'> = {
  author: '',
  role: '',
  company: '',
  quote: '',
  rating: 5,
  published: false,
  sort: 9,
}

/** Panel de plataforma → Página web: planes con precios y testimonios de la página pública (/web). */
export function PlataformaSitio() {
  const { data } = useQuery({
    queryKey: ['platform-site'],
    queryFn: async () => (await api.get<SiteAdmin>('/platform/site')).data,
  })
  const [newPlan, setNewPlan] = useState(false)
  const [newTestimonial, setNewTestimonial] = useState(false)
  const [newPartner, setNewPartner] = useState(false)
  if (!data) return <p className="py-8 text-center text-gray-500">Cargando…</p>

  return (
    <div className="space-y-6 py-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link to="/plataforma" className="text-sm text-brand-blue">
          ← Todas las empresas
        </Link>
        <a href="/web" target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-blue">
          Ver la página pública <ExternalLink className="h-4 w-4" aria-hidden="true" />
        </a>
      </div>
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Página web y planes</h1>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Planes y precios ({data.currency})</h2>
          <Button variant="secondary" className="!w-auto !px-4 !py-2 text-sm" onClick={() => setNewPlan((v) => !v)}>
            <span className="inline-flex items-center gap-1.5">
              <Plus className="h-4 w-4" aria-hidden="true" /> Nuevo plan
            </span>
          </Button>
        </div>
        {newPlan && <PlanForm currency={data.currency} plan={{ ...EMPTY_PLAN, id: 0 }} onDone={() => setNewPlan(false)} />}
        <div className="grid gap-3 lg:grid-cols-3">
          {data.plans.map((plan) => (
            <PlanForm key={plan.id} currency={data.currency} plan={plan} />
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Empresas aliadas</h2>
          <Button variant="secondary" className="!w-auto !px-4 !py-2 text-sm" onClick={() => setNewPartner((v) => !v)}>
            <span className="inline-flex items-center gap-1.5">
              <Plus className="h-4 w-4" aria-hidden="true" /> Nuevo aliado
            </span>
          </Button>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Empresas que trabajan con Multitec. Pide su permiso para mostrarlas; si te dan su logo, ponlo en la web y escribe su
          ruta (por ejemplo /brand/aliado.png).
        </p>
        {newPartner && (
          <PartnerForm partner={{ id: 0, name: '', description: '', url: '', logo_url: '', published: true, sort: 9 }} onDone={() => setNewPartner(false)} />
        )}
        <div className="grid gap-3 lg:grid-cols-3">
          {data.partners.map((p) => (
            <PartnerForm key={p.id} partner={p} />
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Testimonios</h2>
          <Button variant="secondary" className="!w-auto !px-4 !py-2 text-sm" onClick={() => setNewTestimonial((v) => !v)}>
            <span className="inline-flex items-center gap-1.5">
              <Plus className="h-4 w-4" aria-hidden="true" /> Nuevo testimonio
            </span>
          </Button>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Solo salen en la página los <b>publicados</b>. Los de <b>ejemplo</b> son borradores: escribe la opinión real de un
          cliente (con su permiso) antes de publicarlos.
        </p>
        <AskForReviews />
        {newTestimonial && (
          <TestimonialForm testimonial={{ ...EMPTY_TESTIMONIAL, id: 0, is_example: false }} onDone={() => setNewTestimonial(false)} />
        )}
        <div className="grid gap-3 lg:grid-cols-3">
          {data.testimonials.map((t) => (
            <TestimonialForm key={t.id} testimonial={t} />
          ))}
        </div>
      </section>
    </div>
  )
}

function PlanForm({ plan, currency, onDone }: { plan: SitePlan; currency: string; onDone?: () => void }) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({
    ...plan,
    description: plan.description ?? '',
    featuresText: plan.features.join('\n'),
    maxUsersText: plan.max_users ? String(plan.max_users) : '',
  })
  const [msg, setMsg] = useState<string | null>(null)
  const isNew = plan.id === 0
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['platform-site'] })
    queryClient.invalidateQueries({ queryKey: ['public-site'] })
  }
  const save = useMutation({
    mutationFn: async () => {
      const body = {
        name: form.name,
        description: form.description || null,
        monthly_price: Number(form.monthly_price),
        setup_price: Number(form.setup_price),
        max_users: form.maxUsersText ? Number(form.maxUsersText) : null,
        features: form.featuresText.split('\n'),
        highlighted: form.highlighted,
        active: form.active,
        sort: Number(form.sort),
      }
      return isNew ? api.post('/platform/site/plans', body) : api.put(`/platform/site/plans/${plan.id}`, body)
    },
    onSuccess: () => {
      setMsg('Guardado')
      refresh()
      onDone?.()
    },
    onError: (e) => setMsg(apiErrorMessage(e, 'No se pudo guardar')),
  })
  const remove = useMutation({
    mutationFn: async () => api.delete(`/platform/site/plans/${plan.id}`),
    onSuccess: refresh,
  })

  return (
    <Card testId={`plan-${plan.id}`}>
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate()
        }}
      >
        <div className="flex items-center gap-2">
          <Input aria-label="Nombre del plan" required minLength={2} value={form.name} placeholder="Nombre del plan" onChange={(e) => setForm({ ...form, name: e.target.value })} />
          {!form.active && <Badge tone="gray">Oculto</Badge>}
        </div>
        <Field label="Frase corta">
          <Input value={form.description} maxLength={200} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>
        <div className="grid grid-cols-3 gap-2">
          <Field label={`Mes (${currency})`}>
            <Input type="number" min={0} step="0.01" value={form.monthly_price} onChange={(e) => setForm({ ...form, monthly_price: Number(e.target.value) })} />
          </Field>
          <Field label="Instalación">
            <Input type="number" min={0} step="0.01" value={form.setup_price} onChange={(e) => setForm({ ...form, setup_price: Number(e.target.value) })} />
          </Field>
          <Field label="Usuarios">
            <Input type="number" min={1} placeholder="∞" value={form.maxUsersText} onChange={(e) => setForm({ ...form, maxUsersText: e.target.value })} />
          </Field>
        </div>
        <Field label="Qué incluye (uno por línea)">
          <Textarea rows={6} value={form.featuresText} onChange={(e) => setForm({ ...form, featuresText: e.target.value })} />
        </Field>
        <div className="flex flex-wrap gap-4 text-sm text-gray-700 dark:text-gray-300">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={form.highlighted} onChange={(e) => setForm({ ...form, highlighted: e.target.checked })} /> Más popular
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} /> Se ofrece
          </label>
          <label className="flex items-center gap-2">
            Orden
            <input type="number" min={0} className="w-14 rounded-lg border border-gray-200 px-2 py-1 dark:border-gray-700 dark:bg-gray-900" value={form.sort} onChange={(e) => setForm({ ...form, sort: Number(e.target.value) })} />
          </label>
        </div>
        <p className="text-xs text-gray-500">
          Se verá: {platformMoney(Number(form.monthly_price), currency)}/mes + {platformMoney(Number(form.setup_price), currency)} de instalación
        </p>
        <div className="flex flex-wrap gap-2">
          <Button type="submit" className="!w-auto !px-4 !py-2 text-sm" disabled={save.isPending}>
            {isNew ? 'Crear plan' : 'Guardar'}
          </Button>
          {!isNew && (
            <Button
              type="button"
              variant="ghost"
              className="!w-auto !px-4 !py-2 text-sm !text-red-600"
              onClick={() => window.confirm(`¿Quitar el plan «${plan.name}»? Si alguna empresa lo tiene, solo se oculta.`) && remove.mutate()}
            >
              Quitar
            </Button>
          )}
          {msg && <span className="self-center text-sm text-gray-600 dark:text-gray-400" role="status">{msg}</span>}
        </div>
      </form>
    </Card>
  )
}

function TestimonialForm({ testimonial, onDone }: { testimonial: SiteTestimonial; onDone?: () => void }) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({ ...testimonial, role: testimonial.role ?? '', company: testimonial.company ?? '' })
  const [msg, setMsg] = useState<string | null>(null)
  const isNew = testimonial.id === 0
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['platform-site'] })
    queryClient.invalidateQueries({ queryKey: ['public-site'] })
  }
  const save = useMutation({
    mutationFn: async () => {
      const body = {
        author: form.author,
        role: form.role || null,
        company: form.company || null,
        quote: form.quote,
        rating: Number(form.rating),
        published: form.published,
        sort: Number(form.sort),
      }
      return isNew ? api.post('/platform/site/testimonials', body) : api.put(`/platform/site/testimonials/${testimonial.id}`, body)
    },
    onSuccess: () => {
      setMsg('Guardado')
      refresh()
      onDone?.()
    },
    onError: (e) => setMsg(apiErrorMessage(e, 'No se pudo guardar')),
  })
  const remove = useMutation({
    mutationFn: async () => api.delete(`/platform/site/testimonials/${testimonial.id}`),
    onSuccess: refresh,
  })

  return (
    <Card testId={`testimonial-${testimonial.id}`}>
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate()
        }}
      >
        <div className="flex flex-wrap gap-1.5">
          {testimonial.is_example && <Badge tone="amber">Ejemplo</Badge>}
          {testimonial.source === 'cliente' && <Badge tone="blue">Enviado por cliente</Badge>}
          <Badge tone={testimonial.published ? 'green' : 'gray'}>{testimonial.published ? 'Publicado' : 'Borrador'}</Badge>
        </div>
        {testimonial.contact && (
          <p className="text-xs text-gray-500">
            Contacto (no se publica): <b>{testimonial.contact}</b> — confírmalo con la persona antes de publicar.
          </p>
        )}
        <Field label="Quién lo dice">
          <Input required minLength={2} value={form.author} onChange={(e) => setForm({ ...form, author: e.target.value })} />
        </Field>
        <div className="grid grid-cols-2 gap-2">
          <Field label="Cargo">
            <Input value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} />
          </Field>
          <Field label="Empresa">
            <Input value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} />
          </Field>
        </div>
        <Field label="Opinión">
          <Textarea rows={4} required minLength={10} maxLength={600} value={form.quote} onChange={(e) => setForm({ ...form, quote: e.target.value })} />
        </Field>
        <div className="flex flex-wrap items-center gap-4 text-sm text-gray-700 dark:text-gray-300">
          <span className="flex items-center gap-0.5" aria-label="Estrellas">
            {[1, 2, 3, 4, 5].map((n) => (
              <button key={n} type="button" onClick={() => setForm({ ...form, rating: n })} aria-label={`${n} estrellas`}>
                <Star className={`h-5 w-5 ${n <= form.rating ? 'fill-amber-400 text-amber-400' : 'text-gray-300'}`} aria-hidden="true" />
              </button>
            ))}
          </span>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={form.published} onChange={(e) => setForm({ ...form, published: e.target.checked })} /> Publicar
          </label>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="submit" className="!w-auto !px-4 !py-2 text-sm" disabled={save.isPending}>
            {isNew ? 'Crear' : 'Guardar'}
          </Button>
          {!isNew && (
            <Button
              type="button"
              variant="ghost"
              className="!w-auto !px-4 !py-2 text-sm !text-red-600"
              onClick={() => window.confirm('¿Borrar este testimonio?') && remove.mutate()}
            >
              Borrar
            </Button>
          )}
          {msg && <span className="self-center text-sm text-gray-600 dark:text-gray-400" role="status">{msg}</span>}
        </div>
      </form>
    </Card>
  )
}


/** Enlace para pedirle su opinión a un cliente (abre el formulario de la página pública directamente). */
function AskForReviews() {
  const [copied, setCopied] = useState(false)
  const link = `${window.location.origin}/web#opinar`
  const message = `Hola, gracias por confiar en Multitec. ¿Nos regalas un minuto para contar tu experiencia? ${link}`
  return (
    <Card>
      <p className="font-medium text-gray-900 dark:text-gray-100">Pide opiniones a tus clientes</p>
      <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
        Mándales este enlace. Lo que escriban te llega aquí como borrador y a la campanita; tú decides qué publicar.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <code className="min-w-0 flex-1 truncate rounded-xl bg-brand-gray px-3 py-2 text-sm dark:bg-gray-800">{link}</code>
        <Button
          variant="secondary"
          className="!w-auto !px-4 !py-2 text-sm"
          onClick={() => {
            void navigator.clipboard?.writeText(link).then(() => setCopied(true))
          }}
        >
          <span className="inline-flex items-center gap-1.5">
            <Copy className="h-4 w-4" aria-hidden="true" /> {copied ? 'Copiado' : 'Copiar enlace'}
          </span>
        </Button>
        <a
          href={`https://wa.me/?text=${encodeURIComponent(message)}`}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 rounded-2xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
        >
          <MessageCircle className="h-4 w-4" aria-hidden="true" /> Enviar por WhatsApp
        </a>
      </div>
    </Card>
  )
}


function PartnerForm({ partner, onDone }: { partner: SitePartner; onDone?: () => void }) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({
    ...partner,
    description: partner.description ?? '',
    url: partner.url ?? '',
    logo_url: partner.logo_url ?? '',
  })
  const [msg, setMsg] = useState<string | null>(null)
  const isNew = partner.id === 0
  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['platform-site'] })
    queryClient.invalidateQueries({ queryKey: ['public-site'] })
  }
  const save = useMutation({
    mutationFn: async () => {
      const body = {
        name: form.name,
        description: form.description || null,
        url: form.url || null,
        logo_url: form.logo_url || null,
        published: form.published,
        sort: Number(form.sort),
      }
      return isNew ? api.post('/platform/site/partners', body) : api.put(`/platform/site/partners/${partner.id}`, body)
    },
    onSuccess: () => {
      setMsg('Guardado')
      refresh()
      onDone?.()
    },
    onError: (e) => setMsg(apiErrorMessage(e, 'No se pudo guardar')),
  })
  const remove = useMutation({
    mutationFn: async () => api.delete(`/platform/site/partners/${partner.id}`),
    onSuccess: refresh,
  })
  return (
    <Card testId={`partner-${partner.id}`}>
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate()
        }}
      >
        <Field label="Empresa">
          <Input required minLength={2} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <Field label="A qué se dedica">
          <Input maxLength={200} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>
        <Field label="Sitio web">
          <Input value={form.url} placeholder="www.empresa.com.do" onChange={(e) => setForm({ ...form, url: e.target.value })} />
        </Field>
        <Field label="Logo (opcional, imagen de esta web)">
          <Input value={form.logo_url} placeholder="/brand/aliado.png" onChange={(e) => setForm({ ...form, logo_url: e.target.value })} />
        </Field>
        <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
          <input type="checkbox" checked={form.published} onChange={(e) => setForm({ ...form, published: e.target.checked })} /> Mostrar en la página
        </label>
        <div className="flex flex-wrap gap-2">
          <Button type="submit" className="!w-auto !px-4 !py-2 text-sm" disabled={save.isPending}>
            {isNew ? 'Agregar' : 'Guardar'}
          </Button>
          {!isNew && (
            <Button type="button" variant="ghost" className="!w-auto !px-4 !py-2 text-sm !text-red-600" onClick={() => window.confirm(`¿Quitar a «${partner.name}»?`) && remove.mutate()}>
              Quitar
            </Button>
          )}
          {msg && <span className="self-center text-sm text-gray-600 dark:text-gray-400" role="status">{msg}</span>}
        </div>
      </form>
    </Card>
  )
}
