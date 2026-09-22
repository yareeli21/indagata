/**
 * Componente InstrumentosTable - Tabla de instrumentos
 * 
 * Muestra lista de instrumentos en formato tabla.
 * Permite seleccionar un instrumento para ver su detalle.
 */

import type { InstrumentoResumen } from '../../types';
import { TIPO_INSTRUMENTO_LABELS } from '../../types/constants';
import { formatDateShort } from '../../utils/formatters';

interface InstrumentosTableProps {
  instrumentos: InstrumentoResumen[];
  selectedId: number | null;
  onSelect: (instrumento: InstrumentoResumen) => void;
  loading: boolean;
}

export default function InstrumentosTable({
  instrumentos,
  selectedId,
  onSelect,
  loading,
}: InstrumentosTableProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <div className="inline-block w-8 h-8 border-4 border-gray-200 border-t-blue-500 rounded-full animate-spin" />
        <p className="mt-4 text-gray-600">Cargando instrumentos...</p>
      </div>
    );
  }

  if (instrumentos.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <svg
          className="mx-auto w-16 h-16 text-gray-300 mb-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          No hay instrumentos
        </h3>
        <p className="text-gray-600 mb-4">
          No se encontraron instrumentos con los filtros aplicados
        </p>
        <a
          href="/cargar"
          className="inline-block px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white font-medium rounded-md transition-colors"
        >
          Cargar Instrumento
        </a>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Instrumento
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Tipo
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Idioma
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Visibilidad
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Fecha
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {instrumentos.map((instrumento) => (
              <tr
                key={instrumento.instrumento_id}
                onClick={() => onSelect(instrumento)}
                className={`cursor-pointer transition-colors ${
                  selectedId === instrumento.instrumento_id
                    ? 'bg-blue-50 hover:bg-blue-100'
                    : 'hover:bg-gray-50'
                }`}
              >
                <td className="px-6 py-4">
                  <div className="flex items-center">
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {instrumento.nombre}
                      </div>
                      <div className="text-sm text-gray-500">
                        ID: {instrumento.instrumento_id}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="text-sm text-gray-900">
                    {TIPO_INSTRUMENTO_LABELS[instrumento.tipo_instrumento]}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="text-sm text-gray-900">
                    {instrumento.idioma || 'N/A'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      instrumento.visibilidad === 'public'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {instrumento.visibilidad === 'public' ? 'Público' : 'Privado'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatDateShort(instrumento.creado_en)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Paginación (placeholder) */}
      <div className="bg-gray-50 px-6 py-3 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-700">
            Mostrando <span className="font-medium">{instrumentos.length}</span> instrumentos
          </div>
          <div className="text-sm text-gray-500">
            Paginación en desarrollo
          </div>
        </div>
      </div>
    </div>
  );
}
