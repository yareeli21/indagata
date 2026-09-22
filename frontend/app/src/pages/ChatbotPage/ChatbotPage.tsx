/**
 * Página de Chatbot (PLACEHOLDER)
 * 
 * Esta página NO está implementada todavía.
 * Placeholder preparado para desarrollo futuro.
 */
import { Link } from 'react-router-dom';

export default function ChatbotPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
      <div className="max-w-2xl w-full bg-white rounded-lg shadow-lg p-12 text-center">
        <div className="mb-6">
          <div className="w-24 h-24 bg-green-100 rounded-full mx-auto flex items-center justify-center mb-4">
            <svg className="w-12 h-12 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Chatbot con IA
          </h1>
          <p className="text-gray-500">
            Funcionalidad pendiente de implementación
          </p>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
          <h2 className="text-lg font-semibold text-blue-900 mb-2">
            Próximamente
          </h2>
          <p className="text-blue-700 text-sm">
            Esta pantalla permitirá interactuar con un chatbot inteligente que responderá preguntas 
            sobre los instrumentos de investigación utilizando RAG (Retrieval-Augmented Generation).
          </p>
        </div>

        <div className="text-left space-y-2 text-sm text-gray-600">
          <p><strong>Funcionalidades planificadas:</strong></p>
          <ul className="list-disc list-inside space-y-1 ml-4">
            <li>Consulta de metadatos de instrumentos</li>
            <li>Búsqueda semántica en documentos</li>
            <li>Recomendaciones de instrumentos similares</li>
            <li>Análisis de KPIs asociados</li>
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
