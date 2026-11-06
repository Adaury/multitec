import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  BadgeCheck,
  Bell,
  CalendarCheck2,
  Camera,
  Check,
  ChevronDown,
  ClipboardList,
  FileText,
  Mic,
  Package,
  Play,
  ShieldCheck,
  Smartphone,
  Star,
  Users,
  Wand2,
  MessageCircle,
  ExternalLink,
  Handshake,
} from 'lucide-react'
import { api, apiErrorMessage } from '../lib/api'
import { platformMoney, whatsappLink, type SiteInfo } from '../lib/platformMoney'

const PROBLEMS = [
  {
    before: 'Cotizaciones a mano que tardan un día',
    after: 'La IA arma la cotización con tu catálogo y tus precios en minutos',
    icon: Wand2,
  },
  {
    before: 'Levantamientos en papel o en notas de voz sueltas',
    after: 'El técnico dicta el levantamiento con fotos desde el celular',
    icon: Mic,
  },
  {
    before: 'No sabes qué técnico está dónde ni qué falta por cobrar',
    after: 'Calendario, visitas con ubicación, tickets y cuentas por cobrar en un solo lugar',
    icon: CalendarCheck2,
  },
]

const FEATURES = [
  { icon: ClipboardList, title: 'Levantamientos', text: 'Fotos, puntos en el plano y notas de voz que se convierten en texto.' },
  { icon: Wand2, title: 'Cotización con IA', text: 'Propone equipos, cable, ferretería y mano de obra a partir del levantamiento.' },
  { icon: Camera, title: 'Catálogo listo', text: 'Cámaras, alarmas, cerco eléctrico, domótica y redes: más de 290 artículos de base.' },
  { icon: FileText, title: 'Facturas con NCF', text: 'Comprobantes fiscales, reportes 606 y 607 listos para la DGII.' },
  { icon: Users, title: 'Técnicos en el iPhone', text: 'Cada técnico ve solo lo suyo: visitas, tickets y cómo llegar.' },
  { icon: Bell, title: 'Portal del cliente', text: 'Tu cliente ve su cotización, la aprueba y sigue el avance de su obra.' },
  { icon: Package, title: 'Inventario y compras', text: 'Existencias, suplidores y facturas de compra.' },
  { icon: ShieldCheck, title: 'Seguro y respaldado', text: 'Cada empresa con sus datos separados, auditoría y copia diaria.' },
]

const VIDEOS = [
  { file: '04-cotizacion-con-ia', title: 'Cotización con IA' },
  { file: '03-levantamiento-y-puntos', title: 'Levantamiento con fotos y puntos' },
  { file: '08-el-tecnico-en-el-iphone', title: 'El técnico en el iPhone' },
]

const FAQ = [
  ['¿Tengo que instalar algo?', 'No. Multitec funciona en el navegador de la computadora y del celular (iPhone y Android). Si quieres, lo agregas a la pantalla de inicio del celular como una app.'],
  ['¿Qué pasa cuando terminan los días gratis?', 'Te contactamos para la instalación y explicación con tu equipo. Si decides seguir, pagas la instalación una sola vez y luego la mensualidad de tu plan. Tus datos de la prueba se quedan.'],
  ['¿Puedo pagar en pesos?', 'Sí. Los precios están en dólares y puedes pagar en pesos dominicanos por transferencia o depósito a la tasa del día.'],
  ['¿Qué incluye la instalación?', 'Configuramos tu empresa (datos, logo, NCF, usuarios), cargamos tu catálogo y precios, y le explicamos el sistema a tu equipo.'],
  ['¿Mis datos están seguros?', 'Cada empresa tiene sus datos separados, con copia de seguridad diaria. Nadie de otra empresa puede verlos. El soporte solo entra para ayudarte y queda registrado en tu auditoría.'],
  ['¿Puedo cancelar?', 'Sí, cuando quieras. No hay contrato de permanencia. Si te vas, te entregamos una copia de tus datos.'],
]

function Logo({ className = 'h-10' }: { className?: string }) {
  return (
    <>
      <img src="/brand/multitec-logo-negro.png" alt="Multitec — Servicios de calidad" className={`${className} w-auto dark:hidden`} />
      <img src="/brand/multitec-logo-blanco.png" alt="Multitec — Servicios de calidad" className={`${className} hidden w-auto dark:block`} />
    </>
  )
}

function VideoCard({ file, title }: { file: string; title: string }) {
  const [playing, setPlaying] = useState(false)
  return (
    <figure className="overflow-hidden rounded-3xl bg-white shadow-sm ring-1 ring-black/5 dark:bg-gray-900 dark:ring-white/10">
      <div className="relative aspect-video bg-gray-900">
        {playing ? (
          <video src={`/videos/${file}.mp4`} poster={`/videos/${file}.jpg`} controls autoPlay playsInline className="h-full w-full" />
        ) : (
          <button type="button" onClick={() => setPlaying(true)} className="group h-full w-full" aria-label={`Ver video: ${title}`}>
            <img src={`/videos/${file}.jpg`} alt="" loading="lazy" className="h-full w-full object-cover" />
            <span className="absolute inset-0 flex items-center justify-center bg-black/20 transition group-hover:bg-black/30">
              <span className="flex h-14 w-14 items-center justify-center rounded-full bg-white/95 text-brand-blue shadow-lg">
                <Play className="ml-1 h-6 w-6" aria-hidden="true" />
              </span>
            </span>
          </button>
        )}
      </div>
      <figcaption className="px-4 py-3 text-sm font-semibold text-gray-900 dark:text-gray-100">{title}</figcaption>
    </figure>
  )
}

/** Página pública de Multitec: qué es, cómo funciona, precios (como los planes de ZuraPOS), preguntas y contacto. */
export function Web() {
  const { data: site } = useQuery({
    queryKey: ['public-site'],
    queryFn: async () => (await api.get<SiteInfo>('/site')).data,
  })
  const days = site?.trial_days ?? 45
  const currency = site?.currency ?? 'USD'
  const phone = site?.phones[0] ?? '829-283-1336'
  const wa = whatsappLink(phone, 'Hola, quiero saber más de Multitec para mi empresa.')

  return (
    <div className="min-h-dvh bg-white text-gray-900 dark:bg-gray-950 dark:text-gray-100">
      <header className="sticky top-0 z-30 border-b border-gray-100 bg-white/90 backdrop-blur dark:border-gray-800 dark:bg-gray-950/90">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-5 py-3">
          <Link to="/web" aria-label="Multitec — inicio">
            <Logo className="h-9 md:h-11" />
          </Link>
          <nav className="ml-auto hidden items-center gap-6 text-sm font-medium text-gray-600 md:flex dark:text-gray-300">
            <a href="#funciones" className="hover:text-brand-blue">Funciones</a>
            <a href="#videos" className="hover:text-brand-blue">Videos</a>
            <a href="#precios" className="hover:text-brand-blue">Precios</a>
            <a href="#experiencias" className="hover:text-brand-blue">Experiencias</a>
            <a href="#preguntas" className="hover:text-brand-blue">Preguntas</a>
          </nav>
          <div className="ml-auto flex items-center gap-2 md:ml-0">
            <Link to="/login" className="rounded-full px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-brand-gray dark:text-gray-200 dark:hover:bg-gray-800">
              Entrar
            </Link>
            <Link to="/registro" className="rounded-full bg-brand-blue px-4 py-2 text-sm font-semibold text-white hover:bg-brand-blue-dark">
              Prueba gratis
            </Link>
          </div>
        </div>
      </header>

      {/* Portada */}
      <section className="mx-auto grid max-w-6xl items-center gap-10 px-5 py-12 md:py-20 lg:grid-cols-2">
        <div>
          <p className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-sm font-semibold text-brand-blue dark:bg-blue-950/50">
            <BadgeCheck className="h-4 w-4" aria-hidden="true" /> {days} días gratis · sin tarjeta
          </p>
          <h1 className="mt-4 text-4xl font-extrabold leading-tight tracking-tight md:text-5xl">
            El sistema para empresas de <span className="text-brand-blue">cámaras, alarmas y cercos eléctricos</span>
          </h1>
          <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
            Levantamientos desde el celular, cotizaciones con inteligencia artificial, técnicos, facturas con NCF y tus
            clientes, todo en un solo lugar. Hecho en República Dominicana.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link to="/registro" className="rounded-2xl bg-brand-blue px-6 py-4 text-base font-semibold text-white shadow-md hover:bg-brand-blue-dark">
              Empezar mis {days} días gratis
            </Link>
            <a href={wa} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-2xl bg-emerald-600 px-6 py-4 text-base font-semibold text-white hover:bg-emerald-700">
              <MessageCircle className="h-5 w-5" aria-hidden="true" /> Hablar por WhatsApp
            </a>
          </div>
          <p className="mt-4 flex items-center gap-2 text-sm text-gray-500">
            <Smartphone className="h-4 w-4" aria-hidden="true" /> Funciona en computadora, iPhone y Android.
          </p>
        </div>
        <div className="relative">
          <div className="absolute -inset-4 -z-10 rounded-[2.5rem] bg-gradient-to-br from-blue-100 to-indigo-100 dark:from-blue-950/60 dark:to-indigo-950/60" />
          <div className="overflow-hidden rounded-3xl bg-white shadow-2xl ring-1 ring-black/10 dark:bg-gray-900">
            <div className="flex items-center gap-1.5 border-b border-gray-100 px-4 py-2.5 dark:border-gray-800">
              <span className="h-2.5 w-2.5 rounded-full bg-red-400" />
              <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
            </div>
            <img src="/videos/09-ver-y-enviar-cotizacion.jpg" alt="Pantalla de Multitec con una cotización lista para enviar" className="w-full" />
          </div>
        </div>
      </section>

      {/* Antes y ahora */}
      <section className="bg-brand-bg py-14 dark:bg-gray-900/40">
        <div className="mx-auto max-w-6xl px-5">
          <h2 className="text-center text-3xl font-extrabold tracking-tight">Lo que cambia en tu empresa</h2>
          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {PROBLEMS.map((p) => (
              <div key={p.before} className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-black/5 dark:bg-gray-900 dark:ring-white/10">
                <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-blue to-blue-800 text-white">
                  <p.icon className="h-6 w-6" aria-hidden="true" />
                </span>
                <p className="mt-4 text-sm text-gray-500 line-through decoration-red-400">{p.before}</p>
                <p className="mt-1 font-semibold">{p.after}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Funciones */}
      <section id="funciones" className="mx-auto max-w-6xl scroll-mt-20 px-5 py-14">
        <h2 className="text-center text-3xl font-extrabold tracking-tight">Todo lo que necesita tu empresa</h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((f) => (
            <div key={f.title} className="rounded-3xl p-5 ring-1 ring-black/5 dark:ring-white/10">
              <f.icon className="h-7 w-7 text-brand-blue" aria-hidden="true" />
              <p className="mt-3 font-semibold">{f.title}</p>
              <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{f.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Videos */}
      <section id="videos" className="scroll-mt-20 bg-brand-bg py-14 dark:bg-gray-900/40">
        <div className="mx-auto max-w-6xl px-5">
          <h2 className="text-center text-3xl font-extrabold tracking-tight">Míralo funcionando</h2>
          <p className="mt-2 text-center text-gray-600 dark:text-gray-400">Videos cortos con el sistema real.</p>
          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {VIDEOS.map((v) => (
              <VideoCard key={v.file} {...v} />
            ))}
          </div>
        </div>
      </section>

      {/* Precios */}
      <section id="precios" className="mx-auto max-w-6xl scroll-mt-20 px-5 py-14">
        <h2 className="text-center text-3xl font-extrabold tracking-tight">Precios claros</h2>
        <p className="mt-2 text-center text-gray-600 dark:text-gray-400">
          {days} días gratis en cualquier plan. Precios en dólares; puedes pagar en pesos a la tasa del día.
        </p>
        <div className="mt-8 grid gap-4 md:grid-cols-3" data-testid="pricing">
          {(site?.plans ?? []).map((plan) => (
            <div
              key={plan.id}
              className={`relative flex flex-col rounded-3xl p-6 ${
                plan.highlighted
                  ? 'bg-gradient-to-b from-brand-blue to-blue-800 text-white shadow-xl md:-my-3 md:py-9'
                  : 'bg-white shadow-sm ring-1 ring-black/5 dark:bg-gray-900 dark:ring-white/10'
              }`}
            >
              {plan.highlighted && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-amber-400 px-3 py-1 text-xs font-bold text-amber-950">
                  Más popular
                </span>
              )}
              <p className="text-lg font-bold">{plan.name}</p>
              {plan.description && <p className={`text-sm ${plan.highlighted ? 'text-white/80' : 'text-gray-500'}`}>{plan.description}</p>}
              <p className="mt-4">
                <span className="text-4xl font-extrabold">{platformMoney(plan.monthly_price, currency)}</span>
                <span className={plan.highlighted ? 'text-white/80' : 'text-gray-500'}>/mes</span>
              </p>
              <p className={`text-sm ${plan.highlighted ? 'text-white/80' : 'text-gray-500'}`}>
                + {platformMoney(plan.setup_price, currency)} de instalación y explicación (una vez)
              </p>
              <ul className="mt-5 flex-1 space-y-2 text-sm">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2">
                    <Check className={`mt-0.5 h-4 w-4 shrink-0 ${plan.highlighted ? 'text-amber-300' : 'text-emerald-600'}`} aria-hidden="true" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                to={`/registro?plan=${plan.id}`}
                className={`mt-6 rounded-2xl px-5 py-3 text-center font-semibold ${
                  plan.highlighted ? 'bg-white text-brand-blue hover:bg-blue-50' : 'bg-brand-blue text-white hover:bg-brand-blue-dark'
                }`}
              >
                Probar {days} días gratis
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* Empresas aliadas (las que publicó el dueño). */}
      {site && site.partners.length > 0 && (
        <section id="aliados" className="mx-auto max-w-6xl scroll-mt-20 px-5 py-14" data-testid="partners">
          <h2 className="flex items-center justify-center gap-2 text-center text-3xl font-extrabold tracking-tight">
            <Handshake className="h-8 w-8 text-brand-blue" aria-hidden="true" /> Empresas aliadas
          </h2>
          <p className="mt-2 text-center text-gray-600 dark:text-gray-400">Trabajamos junto a empresas de tecnología de República Dominicana.</p>
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            {site.partners.map((p) => (
              <div key={p.id} className="flex w-full max-w-sm items-center gap-4 rounded-3xl bg-white p-5 shadow-sm ring-1 ring-black/5 dark:bg-gray-900 dark:ring-white/10">
                {p.logo_url ? (
                  // Fondo blanco siempre: los logos de los aliados vienen pensados para fondo claro (también en modo oscuro).
                  <span className="flex h-16 w-32 shrink-0 items-center justify-center rounded-2xl bg-white p-2 ring-1 ring-black/5">
                    <img src={p.logo_url} alt={p.name} className="max-h-full max-w-full object-contain" />
                  </span>
                ) : (
                  <span aria-hidden="true" className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-slate-700 to-slate-900 text-lg font-extrabold text-white">
                    {p.name.replace(/[^A-Za-zÁÉÍÓÚÑ]/g, '').slice(0, 2).toUpperCase()}
                  </span>
                )}
                <div className="min-w-0">
                  <p className="font-semibold">{p.name}</p>
                  {p.description && <p className="text-sm text-gray-600 dark:text-gray-400">{p.description}</p>}
                  {p.url && (
                    <a href={p.url} target="_blank" rel="noopener noreferrer" className="mt-1 inline-flex items-center gap-1 text-sm font-semibold text-brand-blue hover:underline">
                      Visitar sitio <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Experiencias: solo las que el dueño publicó (opiniones reales); siempre con el formulario para contar la suya. */}
      <section id="experiencias" className="scroll-mt-20 bg-brand-bg py-14 dark:bg-gray-900/40">
        <div className="mx-auto max-w-6xl px-5">
          <h2 className="text-center text-3xl font-extrabold tracking-tight">Experiencias de nuestros clientes</h2>
          {site && site.testimonials.length === 0 && (
            <p className="mx-auto mt-2 max-w-xl text-center text-gray-600 dark:text-gray-400">
              Estamos reuniendo las opiniones de las empresas que ya trabajan con Multitec. ¿Eres una de ellas? Sé de los
              primeros en contar tu experiencia.
            </p>
          )}
          {site && site.testimonials.length > 0 && (
            <div className="mt-8 grid gap-4 md:grid-cols-3">
              {site.testimonials.map((t) => (
                <figure key={t.id} className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-black/5 dark:bg-gray-900 dark:ring-white/10">
                  <div className="flex gap-0.5 text-amber-400" aria-label={`${t.rating} de 5 estrellas`}>
                    {Array.from({ length: t.rating }, (_, i) => (
                      <Star key={i} className="h-4 w-4 fill-current" aria-hidden="true" />
                    ))}
                  </div>
                  <blockquote className="mt-3 text-gray-700 dark:text-gray-300">“{t.quote}”</blockquote>
                  <figcaption className="mt-4 text-sm">
                    <span className="font-semibold">{t.author}</span>
                    <span className="block text-gray-500">{[t.role, t.company].filter(Boolean).join(' · ')}</span>
                  </figcaption>
                </figure>
              ))}
            </div>
          )}
          <ExperienceForm />
        </div>
      </section>

      {/* Preguntas */}
      <section id="preguntas" className="mx-auto max-w-3xl scroll-mt-20 px-5 py-14">
        <h2 className="text-center text-3xl font-extrabold tracking-tight">Preguntas frecuentes</h2>
        <div className="mt-8 space-y-3">
          {FAQ.map(([q, a]) => (
            <details key={q} className="group rounded-2xl bg-white p-5 shadow-sm ring-1 ring-black/5 dark:bg-gray-900 dark:ring-white/10">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 font-semibold">
                {q}
                <ChevronDown className="h-5 w-5 shrink-0 text-gray-400 transition group-open:rotate-180" aria-hidden="true" />
              </summary>
              <p className="mt-3 text-gray-600 dark:text-gray-400">{a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* Llamado final */}
      <section className="px-5 pb-16">
        <div className="mx-auto max-w-6xl rounded-[2rem] bg-gradient-to-br from-brand-blue to-indigo-800 px-6 py-12 text-center text-white">
          <h2 className="text-3xl font-extrabold tracking-tight">Pruébalo {days} días con tu equipo</h2>
          <p className="mt-2 text-white/85">Sin tarjeta. Te ayudamos a empezar.</p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Link to="/registro" className="rounded-2xl bg-white px-6 py-4 font-semibold text-brand-blue hover:bg-blue-50">
              Crear mi cuenta gratis
            </Link>
            <a href={wa} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-2xl bg-emerald-500 px-6 py-4 font-semibold text-white hover:bg-emerald-600">
              <MessageCircle className="h-5 w-5" aria-hidden="true" /> {phone}
            </a>
          </div>
        </div>
      </section>

      <footer className="border-t border-gray-100 py-10 dark:border-gray-800">
        <div className="mx-auto flex max-w-6xl flex-col gap-6 px-5 md:flex-row md:items-center md:justify-between">
          <div>
            <Logo className="h-12" />
            <p className="mt-2 text-sm text-gray-500">Seguridad electrónica · República Dominicana</p>
          </div>
          <div className="flex flex-col gap-1 text-sm text-gray-600 dark:text-gray-400">
            {(site?.phones ?? [phone]).map((p) => (
              <a key={p} href={whatsappLink(p)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 hover:text-brand-blue">
                <MessageCircle className="h-4 w-4" aria-hidden="true" /> {p}
              </a>
            ))}
            <Link to="/terminos" className="hover:text-brand-blue">
              Términos y privacidad
            </Link>
          </div>
        </div>
        <p className="mt-6 text-center text-xs text-gray-400">© {new Date().getFullYear()} Multitec. Todos los derechos reservados.</p>
      </footer>

      <a
        href={wa}
        target="_blank"
        rel="noreferrer"
        aria-label="Escribir por WhatsApp"
        className="fixed bottom-5 right-5 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500 text-white shadow-xl hover:bg-emerald-600"
      >
        <MessageCircle className="h-7 w-7" aria-hidden="true" />
      </a>
    </div>
  )
}


/** «Cuéntanos tu experiencia»: la opinión llega al panel sin publicar; el dueño la revisa y la publica. Con el enlace
 * /web#opinar (para mandarlo por WhatsApp) el formulario se abre solo. */
function ExperienceForm() {
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ author: '', company: '', role: '', quote: '', contact: '', website: '' })
  const [rating, setRating] = useState(5)
  const [consent, setConsent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (window.location.hash === '#opinar') {
      setOpen(true)
      setTimeout(() => document.getElementById('experiencias')?.scrollIntoView({ behavior: 'smooth' }), 300)
    }
  }, [])

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [key]: e.target.value })

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api.post('/site/experiences', { ...form, rating, consent })
      setSent(true)
    } catch (err) {
      setError(apiErrorMessage(err, 'No se pudo enviar. Intenta de nuevo.'))
    } finally {
      setBusy(false)
    }
  }

  const input =
    'w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-900 outline-none focus:border-brand-blue focus:ring-2 focus:ring-brand-blue/20 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100'

  if (sent) {
    return (
      <p role="status" className="mx-auto mt-8 max-w-xl rounded-3xl bg-emerald-50 p-5 text-center text-emerald-900 ring-1 ring-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-200 dark:ring-emerald-900">
        ¡Gracias por contarnos tu experiencia! La revisamos y, con tu permiso, la publicamos aquí.
      </p>
    )
  }
  if (!open) {
    return (
      <div className="mt-8 text-center">
        <button type="button" onClick={() => setOpen(true)} className="rounded-2xl bg-white px-6 py-3 font-semibold text-brand-blue shadow-sm ring-1 ring-black/5 hover:bg-blue-50 dark:bg-gray-900 dark:ring-white/10">
          Cuéntanos tu experiencia
        </button>
      </div>
    )
  }
  return (
    <form onSubmit={submit} className="mx-auto mt-8 max-w-2xl space-y-3 rounded-3xl bg-white p-6 shadow-sm ring-1 ring-black/5 dark:bg-gray-900 dark:ring-white/10" aria-label="Cuéntanos tu experiencia">
      <p className="text-lg font-semibold">Cuéntanos tu experiencia</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-sm font-medium">
          Tu nombre
          <input required minLength={2} maxLength={120} value={form.author} onChange={set('author')} className={`${input} mt-1`} />
        </label>
        <label className="block text-sm font-medium">
          Tu empresa (opcional)
          <input maxLength={120} value={form.company} onChange={set('company')} className={`${input} mt-1`} />
        </label>
      </div>
      <label className="block text-sm font-medium">
        ¿Cómo te ha ido con Multitec?
        <textarea required minLength={15} maxLength={600} rows={4} value={form.quote} onChange={set('quote')} className={`${input} mt-1`} />
      </label>
      <div className="flex flex-wrap items-center gap-4">
        <span className="flex items-center gap-1" role="radiogroup" aria-label="Calificación">
          {[1, 2, 3, 4, 5].map((n) => (
            <button key={n} type="button" role="radio" aria-checked={rating === n} aria-label={`${n} estrellas`} onClick={() => setRating(n)}>
              <Star className={`h-7 w-7 ${n <= rating ? 'fill-amber-400 text-amber-400' : 'text-gray-300'}`} aria-hidden="true" />
            </button>
          ))}
        </span>
        <label className="block min-w-[14rem] flex-1 text-sm font-medium">
          Teléfono o correo (no se publica)
          <input required minLength={5} maxLength={160} value={form.contact} onChange={set('contact')} className={`${input} mt-1`} />
        </label>
      </div>
      <div className="hidden" aria-hidden="true">
        <input tabIndex={-1} autoComplete="off" value={form.website} onChange={set('website')} />
      </div>
      <label className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
        <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5 h-4 w-4 rounded" />
        Autorizo a Multitec a publicar mi opinión con mi nombre y el de mi empresa.
      </label>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      <button type="submit" disabled={busy || !consent} className="w-full rounded-2xl bg-brand-blue px-5 py-3 font-semibold text-white hover:bg-brand-blue-dark disabled:opacity-50">
        {busy ? 'Enviando…' : 'Enviar mi experiencia'}
      </button>
    </form>
  )
}
