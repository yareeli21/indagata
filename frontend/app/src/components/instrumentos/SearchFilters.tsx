/**
 * Componente SearchFilters - Filtros para búsqueda de instrumentos
 * 
 * Filtros disponibles:
 * - Tipo de instrumento
 * - Idioma
 * - KPI asociado
 */

import type { TipoInstrumento, FiltrosActivos } from '../../types';
import { TIPO_INSTRUMENTO_LABELS } from '../../types/constants';

interface SearchFiltersProps {
  filtros: FiltrosActivos;
  onFiltrosChange: (filtros: FiltrosActivos) => void;
}

export default function SearchFilters({ filtros, onFiltrosChange }: SearchFiltersProps) {
  const handleTipoChange = (tipo: string) => {
    onFiltrosChange({
      ...filtros,
      tipo_instrumento: tipo === 'todos' ? null : (tipo as TipoInstrumento),
    });
  };

  const handleIdiomaChange = (idioma: string) => {
    onFiltrosChange({
      ...filtros,
      idioma: idioma,
    });
  };

  const handleLimpiar = () => {
    onFiltrosChange({
      tipo_instrumento: null,
      idioma: '',
      kpi_id: null,
    });
  };

  const hasFiltrosActivos =
    filtros.tipo_instrumento !== null || filtros.idioma !== '' || filtros.kpi_id !== null;

  return (
    <div className="bg-white rounded-lg shadow p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">Filtros de Búsqueda</h3>
        {hasFiltrosActivos && (
          <button
            onClick={handleLimpiar}
            className="text-sm text-blue-600 hover:text-blue-800 transition-colors"
          >
            Limpiar filtros
          </button>
        )}
      </div>

      {/* Tipo de instrumento */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Tipo de Instrumento
        </label>
        <select
          value={filtros.tipo_instrumento || 'todos'}
          onChange={(e) => handleTipoChange(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
        >
          <option value="todos">Todos</option>
          {Object.entries(TIPO_INSTRUMENTO_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {/* Idioma */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Idioma
        </label>
        <input
          type="text"
          value={filtros.idioma}
          onChange={(e) => handleIdiomaChange(e.target.value)}
          placeholder="ej: es, en, fr"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
        />
      </div>

      {/* KPI (placeholder) */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          KPI Asociado
        </label>
        <div className="bg-gray-50 border border-gray-200 rounded-md p-3">
          <p className="text-xs text-gray-500">
            Selector de KPIs en desarrollo
          </p>
        </div>
      </div>

      {/* Indicador de filtros activos */}
      {hasFiltrosActivos && (
        <div className="pt-3 border-t">
          <p className="text-xs text-gray-500 mb-2">Filtros activos:</p>
          <div className="flex flex-wrap gap-2">
            {filtros.tipo_instrumento && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                {TIPO_INSTRUMENTO_LABELS[filtros.tipo_instrumento]}
              </span>
            )}
            {filtros.idioma && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                Idioma: {filtros.idioma}
              </span>
            )}
            {filtros.kpi_id && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                KPI: {filtros.kpi_id}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
