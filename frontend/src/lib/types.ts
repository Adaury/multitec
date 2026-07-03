export type Role = 'admin' | 'oficina' | 'tecnico'

export interface CurrentUser {
  id: number
  name: string
  email: string
  role: Role
}

export interface ManagedUser {
  id: number
  name: string
  email: string
  role: Role
  is_active: boolean
  created_by: number | null
  created_at: string
}

export interface Client {
  id: number
  name: string
  company: string | null
  rnc: string | null
  phone: string | null
  email: string | null
  address: string | null
  notes: string | null
}

export type ClientInput = Omit<Client, 'id'>

export interface Project {
  id: number
  code: string
  client_id: number
  responsible_id: number | null
  date: string
  status: string
  description: string | null
  created_at: string
}

export interface ProjectDetail extends Project {
  client: Client
}

export interface SurveyAsset {
  id: number
  kind: 'photo' | 'audio'
  file_path: string
  description: string | null
  created_at: string
}

export interface Survey {
  id: number
  project_id: number
  notes: string | null
  measurements: string | null
  observations: string | null
  ai_summary: string | null
  assets: SurveyAsset[]
}

export interface Engineering {
  id: number
  project_id: number
  recommended_equipment: string | null
  distribution: string | null
  conduits: string | null
  wiring: string | null
  technical_design: string | null
  observations: string | null
}

export interface Product {
  id: number
  code: string
  category: string
  name: string
  unit: string
  price: number
  notes: string | null
}

export interface BudgetItem {
  id: number
  description: string
  quantity: number
  product_id: number | null
}

export interface Budget {
  id: number
  code: string
  project_id: number
  notes: string | null
  total: number
  created_at: string
  items: BudgetItem[]
}

export interface LineItemInput {
  product_id: number | null
  description: string
  quantity: number
  unit_price: number
}

export interface QuoteItem {
  id: number
  product_id: number | null
  description: string
  quantity: number
  unit_price: number
  subtotal: number
}

export type QuoteStatus = 'pendiente' | 'aprobada' | 'no_aprobada' | 'archivada'

export interface Quote {
  id: number
  code: string
  project_id: number
  source_budget_id: number | null
  status: QuoteStatus
  notes: string | null
  subtotal: number
  itbis: number
  total: number
  created_at: string
  decided_at: string | null
  items: QuoteItem[]
}

export interface QuoteHistoryEntry {
  id: number
  action: string
  note: string | null
  created_at: string
}

export const QUOTE_STATUS_LABELS: Record<QuoteStatus, string> = {
  pendiente: 'Pendiente',
  aprobada: 'Aprobada',
  no_aprobada: 'No aprobada',
  archivada: 'Archivada',
}

export const QUOTE_HISTORY_LABELS: Record<string, string> = {
  creada: 'Creada',
  aprobada: 'Aprobada',
  rechazada: 'Rechazada',
  archivada: 'Archivada',
  reactivada: 'Reactivada',
  editada: 'Editada',
}

export type MaterialStatus = 'disponible' | 'pendiente_compra' | 'comprado' | 'instalado'

export interface Material {
  id: number
  project_id: number
  product_id: number | null
  source_quote_id: number | null
  description: string
  quantity: number
  status: MaterialStatus
  notes: string | null
  created_at: string
}

export const MATERIAL_STATUS_LABELS: Record<MaterialStatus, string> = {
  disponible: 'Disponible',
  pendiente_compra: 'Pendiente de compra',
  comprado: 'Comprado',
  instalado: 'Instalado',
}

export type StageName = 'inicio' | 'instalacion' | 'configuracion' | 'pruebas' | 'entrega'

export interface ProjectStage {
  id: number
  name: StageName
  order: number
  completed: boolean
  completed_at: string | null
}

export interface Execution {
  stages: ProjectStage[]
  progress_percent: number
}

export const STAGE_LABELS: Record<StageName, string> = {
  inicio: 'Inicio',
  instalacion: 'Instalación',
  configuracion: 'Configuración',
  pruebas: 'Pruebas',
  entrega: 'Entrega',
}

export interface LogEntryAsset {
  id: number
  file_path: string
  description: string | null
  created_at: string
}

export interface LogEntry {
  id: number
  project_id: number
  comment: string
  entry_date: string
  responsible_id: number | null
  created_at: string
  assets: LogEntryAsset[]
}

export const PROJECT_STATUS_LABELS: Record<string, string> = {
  levantamiento: 'Levantamiento',
  ingenieria: 'Ingeniería',
  presupuesto: 'Presupuesto',
  cotizacion: 'Cotización',
  ejecucion: 'Ejecución',
  cerrado: 'Cerrado',
}

export interface PreInvoiceItem {
  id: number
  product_id: number | null
  description: string
  quantity: number
  unit_price: number
  subtotal: number
}

export interface PreInvoice {
  id: number
  code: string
  project_id: number
  source_quote_id: number | null
  status: 'pendiente' | 'facturada'
  notes: string | null
  subtotal: number
  itbis: number
  total: number
  created_at: string
  items: PreInvoiceItem[]
}

export interface InvoiceItem {
  id: number
  product_id: number | null
  description: string
  quantity: number
  unit_price: number
  subtotal: number
}

export interface Invoice {
  id: number
  code: string
  project_id: number
  pre_invoice_id: number
  ncf: string | null
  ncf_type: string | null
  subtotal: number
  itbis: number
  total: number
  created_at: string
  items: InvoiceItem[]
}

export interface InvoiceHistoryEntry {
  id: number
  action: string
  note: string | null
  created_at: string
}

export const NCF_TYPES = ['B01', 'B02', 'B14', 'B15'] as const
export type NcfType = (typeof NCF_TYPES)[number]

export const NCF_TYPE_LABELS: Record<NcfType, string> = {
  B01: 'B01 — Crédito Fiscal',
  B02: 'B02 — Consumo',
  B14: 'B14 — Regímenes Especiales',
  B15: 'B15 — Gubernamental',
}

export interface NcfSequence {
  id: number
  ncf_type: NcfType
  description: string
  range_start: number
  range_end: number
  next_number: number
  expires_at: string
  active: boolean
  created_by: number | null
  created_at: string
}

export type ExtensionStatus = 'pendiente' | 'aprobada' | 'rechazada'

export interface Extension {
  id: number
  code: string
  project_id: number
  quote_id: number | null
  title: string
  description: string | null
  status: ExtensionStatus
  date: string
  created_at: string
}

export const EXTENSION_STATUS_LABELS: Record<ExtensionStatus, string> = {
  pendiente: 'Pendiente',
  aprobada: 'Aprobada',
  rechazada: 'Rechazada',
}

export type TicketStatus = 'abierto' | 'en_proceso' | 'resuelto' | 'cerrado'

export interface Ticket {
  id: number
  code: string
  project_id: number
  technician_id: number | null
  problem: string
  solution: string | null
  status: TicketStatus
  created_at: string
  resolved_at: string | null
}

export interface TicketHistoryEntry {
  id: number
  action: string
  note: string | null
  created_at: string
}

export const TICKET_STATUS_LABELS: Record<TicketStatus, string> = {
  abierto: 'Abierto',
  en_proceso: 'En proceso',
  resuelto: 'Resuelto',
  cerrado: 'Cerrado',
}

export interface EngineeringDraft {
  recommended_equipment: string
  distribution: string
  conduits: string
  wiring: string
  technical_design: string
  observations: string
}

export interface BudgetSuggestionItem {
  product_id: number | null
  description: string
  quantity: number
  unit_price: number
}

export interface BudgetSuggestionOut {
  items: BudgetSuggestionItem[]
}

export interface AskResponse {
  answer: string
  projects: string[]
}

export const PRODUCT_CATEGORY_LABELS: Record<string, string> = {
  camara: 'Cámara',
  nvr: 'NVR',
  cableado: 'Cableado',
  switch: 'Switch',
  control_acceso: 'Control de acceso',
  videoportero: 'Videoportero',
  barrera: 'Barrera vehicular',
  automatizacion: 'Automatización',
  otro: 'Otro',
}
