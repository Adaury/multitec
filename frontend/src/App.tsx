import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { Clients } from './pages/Clients'
import { ClientDetail } from './pages/ClientDetail'
import { Catalog } from './pages/Catalog'
import { Categorias } from './pages/Categorias'
import { Projects } from './pages/Projects'
import { ProjectDetail } from './pages/ProjectDetail'
import { Budgets } from './pages/Budgets'
import { Quotes } from './pages/Quotes'
import { Ask } from './pages/Ask'
import { Users } from './pages/Users'
import { Ncf } from './pages/Ncf'
import { CalculationParameters } from './pages/CalculationParameters'
import { Calendario } from './pages/Calendario'
import { PortalCliente } from './pages/PortalCliente'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/portal/:token" element={<PortalCliente />} />
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
          <Route path="/usuarios" element={<Users />} />
          <Route path="/ncf" element={<Ncf />} />
          <Route path="/parametros-calculo" element={<CalculationParameters />} />
          <Route path="/calendario" element={<Calendario />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
