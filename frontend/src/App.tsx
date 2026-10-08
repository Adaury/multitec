import { lazy, Suspense, useEffect, type ComponentType } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { PageLoader } from './components/PageLoader'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Login } from './pages/Login'

// Cada pantalla se descarga solo cuando se visita (antes todo iba en un único archivo de ~540 KB).
// Login y Layout van en el paquete inicial: son lo primero que se ve.
function lazyPage<T extends Record<string, ComponentType<any>>>(load: () => Promise<T>, name: keyof T) {
  return lazy(async () => ({ default: (await load())[name] as ComponentType<any> }))
}

const loaders = {
  Dashboard: () => import('./pages/Dashboard'),
  Clients: () => import('./pages/Clients'),
  ClientDetail: () => import('./pages/ClientDetail'),
  Catalog: () => import('./pages/Catalog'),
  Categorias: () => import('./pages/Categorias'),
  Projects: () => import('./pages/Projects'),
  ProjectDetail: () => import('./pages/ProjectDetail'),
  Budgets: () => import('./pages/Budgets'),
  Quotes: () => import('./pages/Quotes'),
  Ask: () => import('./pages/Ask'),
  Profile: () => import('./pages/Profile'),
  QuickSurvey: () => import('./pages/QuickSurvey'),
  Users: () => import('./pages/Users'),
  Ncf: () => import('./pages/Ncf'),
  CalculationParameters: () => import('./pages/CalculationParameters'),
  AIFeedbackEvents: () => import('./pages/AIFeedbackEvents'),
  Calendario: () => import('./pages/Calendario'),
  PortalCliente: () => import('./pages/PortalCliente'),
  Proveedores: () => import('./pages/Proveedores'),
}

const Dashboard = lazyPage(loaders.Dashboard, 'Dashboard')
const Clients = lazyPage(loaders.Clients, 'Clients')
const ClientDetail = lazyPage(loaders.ClientDetail, 'ClientDetail')
const Catalog = lazyPage(loaders.Catalog, 'Catalog')
const Categorias = lazyPage(loaders.Categorias, 'Categorias')
const Projects = lazyPage(loaders.Projects, 'Projects')
const ProjectDetail = lazyPage(loaders.ProjectDetail, 'ProjectDetail')
const Budgets = lazyPage(loaders.Budgets, 'Budgets')
const Quotes = lazyPage(loaders.Quotes, 'Quotes')
const Ask = lazyPage(loaders.Ask, 'Ask')
const Profile = lazyPage(loaders.Profile, 'Profile')
const QuickSurvey = lazyPage(loaders.QuickSurvey, 'QuickSurvey')
const Users = lazyPage(loaders.Users, 'Users')
const Ncf = lazyPage(loaders.Ncf, 'Ncf')
const CalculationParameters = lazyPage(loaders.CalculationParameters, 'CalculationParameters')
const AIFeedbackEvents = lazyPage(loaders.AIFeedbackEvents, 'AIFeedbackEvents')
const Calendario = lazyPage(loaders.Calendario, 'Calendario')
const PortalCliente = lazyPage(loaders.PortalCliente, 'PortalCliente')
const Proveedores = lazyPage(loaders.Proveedores, 'Proveedores')

// Las pantallas de uso diario se descargan en segundo plano cuando el navegador está libre, para
// que al tocarlas abran al instante en vez de esperar la descarga.
const PREFETCH: Array<() => Promise<unknown>> = [
  loaders.Dashboard,
  loaders.Projects,
  loaders.ProjectDetail,
  loaders.Clients,
  loaders.QuickSurvey,
  loaders.Calendario,
]

function usePrefetchCommonPages() {
  useEffect(() => {
    const run = () => PREFETCH.forEach((load) => void load().catch(() => {}))
    const idle = (window as unknown as { requestIdleCallback?: (cb: () => void) => number }).requestIdleCallback
    if (idle) idle(run)
    else setTimeout(run, 2000)
  }, [])
}

function App() {
  usePrefetchCommonPages()

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/portal/:token"
        element={
          <Suspense fallback={<PageLoader />}>
            <PortalCliente />
          </Suspense>
        }
      />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/clientes" element={<Clients />} />
          <Route path="/clientes/:id" element={<ClientDetail />} />
          <Route path="/proyectos" element={<Projects />} />
          <Route path="/proyectos/:id" element={<ProjectDetail />} />
          <Route path="/catalogo" element={<Catalog />} />
          <Route path="/clasificaciones" element={<Categorias />} />
          <Route path="/presupuestos" element={<Budgets />} />
          <Route path="/cotizaciones" element={<Quotes />} />
          <Route path="/preguntar" element={<Ask />} />
          <Route path="/perfil" element={<Profile />} />
          <Route path="/nuevo" element={<QuickSurvey />} />
          <Route path="/usuarios" element={<Users />} />
          <Route path="/ncf" element={<Ncf />} />
          <Route path="/parametros-calculo" element={<CalculationParameters />} />
          <Route path="/aprendizaje-ia" element={<AIFeedbackEvents />} />
          <Route path="/calendario" element={<Calendario />} />
          <Route path="/proveedores" element={<Proveedores />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
