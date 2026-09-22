/**
 * Componente IngestaPanel - PASO 5: Ejecutar ingesta final
 * 
 * Panel para disparar el pipeline final de ingesta.
 * Muestra progreso y resultado final.
 */

import type { IngestaResponse } from '../../types';
import LoadingSpinner from '../common/LoadingSpinner';
import ErrorAlert from '../common/ErrorAlert';

interface IngestaPanelProps {
  instrumentoId: number;
  onIngest: () => Promise<void>;
  loading: boolean;
  error: string | null;
  result: IngestaResponse | null;
}

export default function IngestaPanel({
  instrumentoId: _instrumentoId,
  onIngest,
  loading,
  error,
  result,
}: IngestaPanelProps) {
  return (
    <div className="space-y-6">
      {error && <ErrorAlert message={error} />}

      {result && (
        <div className="bg-green-50 border-2 border-green-500 rounded-lg p-6">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-12 h-12 bg-green-500 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-xl font-bold text-green-900">¡Ingesta Completada!</h3>
              <p className="text-green-700">{result.mensaje}</p>
            </div>
          </div>

          <div className="bg-white rounded-lg p-4 mt-4">
            <h4 className="font-semibold mb-2">Siguiente paso:</h4>
            <p className="text-sm text-gray-700 mb-4">
              El instrumento ya está disponible en el sistema y puede ser consultado, descargado
              y utilizado para análisis con el chatbot.
            </p>
            <a
              href="/instrumentos"
              className="inline-block px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white font-medium rounded-md transition-colors"
            >
              Ver Instrumentos
            </a>
          </div>
        </div>
      )}

      {!result && (
        <>
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-purple-900 mb-2">
              Pipeline Final de Ingesta
            </h3>
            <p className="text-sm text-purple-800 mb-4">
              Este paso ejecutará el pipeline completo que incluye:
            </p>
            <ol className="text-sm text-purple-800 space-y-2 list-decimal list-inside">
              <li>Aplicación de transformaciones aceptadas</li>
              <li>Consolidación de metadatos enriquecidos</li>
              <li>Generación de JSON enriquecido</li>
              <li>Creación de archivo SAV (solo encuestas)</li>
              <li>Chunking del documento</li>
              <li>Generación de embeddings</li>
              <li>Ingesta en vectorstore para RAG</li>
            </ol>
            <p className="text-xs text-purple-700 mt-4">
              Este proceso puede tardar varios minutos dependiendo del tamaño del instrumento.
            </p>
          </div>

          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <svg
                className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
              <div>
                <p className="text-sm font-medium text-yellow-800">Importante</p>
                <p className="text-sm text-yellow-700 mt-1">
                  Una vez iniciada la ingesta, el proceso no puede detenerse. Asegúrese de haber
                  revisado todas las propuestas ETL correctamente.
                </p>
              </div>
            </div>
          </div>

          <div className="flex justify-center pt-4">
            {loading ? (
              <div className="text-center">
                <LoadingSpinner size="lg" message="Ejecutando pipeline de ingesta..." />
                <p className="text-sm text-gray-600 mt-4">
                  Este proceso puede tardar varios minutos. Por favor no cierre esta ventana.
                </p>
              </div>
            ) : (
              <button
                onClick={onIngest}
                className="px-8 py-3 bg-purple-500 hover:bg-purple-600 text-white font-medium rounded-md transition-colors"
              >
                Ejecutar Ingesta
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
