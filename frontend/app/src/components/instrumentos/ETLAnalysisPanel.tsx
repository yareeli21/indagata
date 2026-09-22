/**
 * Componente ETLAnalysisPanel - PASO 3: Analizar instrumento
 * 
 * Panel simple con botón para disparar el análisis ETL.
 * Muestra el resultado del análisis.
 */

import type { EtlExtractResponse } from '../../types';
import LoadingSpinner from '../common/LoadingSpinner';
import ErrorAlert from '../common/ErrorAlert';
import SuccessMessage from '../common/SuccessMessage';

interface ETLAnalysisPanelProps {
  instrumentoId: number;
  onAnalyze: () => Promise<void>;
  loading: boolean;
  error: string | null;
  result: EtlExtractResponse | null;
}

export default function ETLAnalysisPanel({
  instrumentoId: _instrumentoId,
  onAnalyze,
  loading,
  error,
  result,
}: ETLAnalysisPanelProps) {
  return (
    <div className="space-y-6">
      {error && <ErrorAlert message={error} />}

      {result && (
        <SuccessMessage message={result.mensaje} />
      )}

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-2">
          Análisis ETL con Inteligencia Artificial
        </h3>
        <p className="text-sm text-blue-800 mb-4">
          El sistema analizará el instrumento utilizando un modelo de lenguaje (LLM) para:
        </p>
        <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside mb-4">
          <li>Detectar transformaciones necesarias en los datos</li>
          <li>Inferir metadatos enriquecidos adicionales</li>
          <li>Sugerir KPIs relevantes basándose en el contenido</li>
        </ul>
        <p className="text-xs text-blue-700">
          Este proceso puede tardar entre 30 segundos y 2 minutos dependiendo del tamaño del instrumento.
        </p>
      </div>

      {result && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h4 className="font-semibold mb-4">Resumen del Análisis</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-blue-600">{result.n_propuestas}</p>
              <p className="text-sm text-gray-600">Total Propuestas</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-purple-600">{result.n_transformaciones}</p>
              <p className="text-sm text-gray-600">Transformaciones</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-green-600">{result.n_metadatos}</p>
              <p className="text-sm text-gray-600">Metadatos</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-orange-600">{result.n_kpis}</p>
              <p className="text-sm text-gray-600">KPIs</p>
            </div>
          </div>
        </div>
      )}

      <div className="flex justify-center">
        {loading ? (
          <LoadingSpinner size="lg" message="Analizando instrumento con IA..." />
        ) : (
          <button
            onClick={onAnalyze}
            disabled={!!result}
            className="px-8 py-3 bg-blue-500 hover:bg-blue-600 text-white font-medium rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {result ? 'Análisis Completado' : 'Iniciar Análisis ETL'}
          </button>
        )}
      </div>
    </div>
  );
}
