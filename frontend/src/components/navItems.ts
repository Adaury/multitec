import { Building2, Eraser, Hash, Settings, ShieldCheck, SlidersHorizontal, type LucideIcon } from 'lucide-react'

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  end?: boolean
}

/** Configuración del negocio (solo admin). En el menú van juntas bajo «Administración». */
export const ADMIN_ITEMS: NavItem[] = [
  { to: '/usuarios', label: 'Usuarios', icon: Settings },
  { to: '/ncf', label: 'NCF', icon: Hash },
  { to: '/empresa', label: 'Mi empresa', icon: Building2 },
  { to: '/auditoria', label: 'Auditoría', icon: ShieldCheck },
  { to: '/aprendizaje-ia', label: 'Ajustes de IA', icon: SlidersHorizontal },
  { to: '/borrar-pruebas', label: 'Borrar datos de prueba', icon: Eraser },
]

export const ADMIN_PATHS = new Set(ADMIN_ITEMS.map((item) => item.to))
