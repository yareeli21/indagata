/**
 * Página de Visualización y Análisis de KPIs (PLACEHOLDER)
 * 
 * Esta página NO está implementada todavía.
 * Placeholder preparado para desarrollo futuro.
 */
import { Link } from 'react-router-dom';

export default function KpiPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
      <div className="max-w-2xl w-full bg-white rounded-lg shadow-lg p-12 text-center">
        <div className="mb-6">
          <div className="w-24 h-24 bg-purple-100 rounded-full mx-auto flex items-center justify-center mb-4">
            <svg className="w-12 h-12 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Visualización y Análisis de KPIs
          </h1>
          <p className="text-gray-500">
            Funcionalidad pendiente de implementación
          </p>
        </div>

        <div className="bg-purple-50 border border-purple-200 rounded-lg p-6 mb-6">
          <h2 className="text-lg font-semibold text-purple-900 mb-2">
            Próximamente
          </h2>
          <p className="text-purple-700 text-sm">
            Esta pantalla permitirá visualizar y analizar los KPIs (Indicadores Clave de Desempeño) 
            asociados a los instrumentos de investigación educativa.
          </p>
        </div>

        <div className="text-left space-y-2 text-sm text-gray-600">
          <p><strong>Funcionalidades planificadas:</strong></p>
          <ul className="list-disc list-inside space-y-1 ml-4">
            <li>Dashboard con métricas agregadas</li>
            <li>Gráficos interactivos de distribución de KPIs</li>
            <li>Filtros por tipo de instrumento y fecha</li>
            <li>Exportación de reportes en PDF/Excel</li>
            <li>Análisis de correlaciones entre KPIs</li>
          </ul>
        </div>

        <div className="mt-8">
          <Link
            to="/app/instrumentos"
            className="inline-block px-6 py-2 bg-green-500 hover:bg-green-600 text-white font-medium rounded-md transition-colors"
          >
            Ver Instrumentos
          </Link>
        </div>
      </div>
    </div>
  );
}
