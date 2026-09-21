/**
 * Configuración de rutas de la aplicación
 * 
 * Estructura:
 * - /: Landing page con animación
 * - /login: Página de autenticación
 * - /app: Layout principal con navegación
 *   - /app/instrumentos: Visualización y descarga
 *   - /app/cargar: Carga de instrumentos (wizard 5 pasos)
 *   - /app/chatbot: Chatbot con IA (placeholder)
 *   - /app/kpis: Visualización de KPIs (placeholder)
 */

import { createBrowserRouter, Navigate } from 'react-router-dom';

// Páginas
import LandingPage from '../pages/LandingPage';
import LoginPage from '../pages/LoginPage';
import CargaInstrumentosPage from '../pages/CargaInstrumentosPage';
import VisualizacionInstrumentosPage from '../pages/VisualizacionInstrumentosPage';
import ChatbotPage from '../pages/ChatbotPage';
import KpiPage from '../pages/KpiPage';

// Layout
import MainLayout from '../components/layout/MainLayout';

/**
 * Guard simple para rutas protegidas
 * TODO: Implementar lógica de autenticación real
 */
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const isAuthenticated = localStorage.getItem('indagata_user');
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

/**
 * Configuración del router
 */
export const router = createBrowserRouter([
  {
    path: '/',
    element: <LandingPage />,
  },
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/app',
    element: (
      <ProtectedRoute>
        <MainLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <Navigate to="/app/instrumentos" replace />,
      },
      {
        path: 'instrumentos',
        element: <VisualizacionInstrumentosPage />,
      },
      {
        path: 'cargar',
        element: <CargaInstrumentosPage />,
      },
      {
        path: 'chatbot',
        element: <ChatbotPage />,
      },
      {
        path: 'kpis',
        element: <KpiPage />,
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);

export default router;
