/**
 * Componente InstrumentoDetalle - Panel de detalle de un instrumento
 * 
 * Muestra información completa del instrumento seleccionado:
 * - Información general
 * - Metadatos Dublin Core
 * - Metadatos enriquecidos
 * - KPIs asociados
 * - Botones de descarga
 */

import type { InstrumentoDetalle as InstrumentoDetalleType } from '../../types';
import { TIPO_INSTRUMENTO_LABELS, ESTADO_COLORS } from '../../types/constants';
import { formatDate } from '../../utils/formatters';
import DownloadButtons from './DownloadButtons';

interface InstrumentoDetalleProps {
  instrumento: InstrumentoDetalleType | null;
  loading: boolean;
}

export default function InstrumentoDetalle({ instrumento, loading }: InstrumentoDetalleProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <div className="inline-block w-8 h-8 border-4 border-gray-200 border-t-blue-500 rounded-full animate-spin" />
        <p className="mt-4 text-gray-600">Cargando detalle...</p>
      </div>
    );
  }

  if (!instrumento) {
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
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <p className="text-gray-600">
          Seleccione un instrumento para ver su detalle
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Información general */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              {instrumento.nombre}
            </h2>
            <div className="flex items-center space-x-3">
              <span className="text-sm text-gray-500">
                ID: {instrumento.instrumento_id}
              </span>
              <span
                className={`px-3 py-1 rounded-full text-xs font-medium ${
                  ESTADO_COLORS[instrumento.dublin_core ? 'metadata_registrado' : 'pendiente']
                }`}
              >
                {TIPO_INSTRUMENTO_LABELS[instrumento.tipo_instrumento]}
              </span>
            </div>
          </div>
        </div>

        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="font-medium text-gray-500">Idioma</dt>
            <dd className="mt-1 text-gray-900">{instrumento.idioma || 'No especificado'}</dd>
          </div>
          <div>
            <dt className="font-medium text-gray-500">Visibilidad</dt>
            <dd className="mt-1 text-gray-900">
              {instrumento.visibilidad === 'public' ? 'Público' : 'Privado'}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-gray-500">Propietario</dt>
            <dd className="mt-1 text-gray-900">{instrumento.propietario || 'No especificado'}</dd>
          </div>
          <div>
            <dt className="font-medium text-gray-500">Fecha de Creación</dt>
            <dd className="mt-1 text-gray-900">{formatDate(instrumento.creado_en)}</dd>
          </div>
          {instrumento.fecha_procesamiento && (
            <div className="col-span-2">
              <dt className="font-medium text-gray-500">Última Actualización</dt>
              <dd className="mt-1 text-gray-900">{formatDate(instrumento.fecha_procesamiento)}</dd>
            </div>
          )}
        </dl>
      </div>

      {/* Dublin Core */}
      {instrumento.dublin_core && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Metadatos Dublin Core</h3>
          <dl className="space-y-3 text-sm">
            {Object.entries(instrumento.dublin_core).map(([key, value]) => (
              <div key={key} className="border-b border-gray-100 pb-3 last:border-0">
                <dt className="font-medium text-gray-500 capitalize">
                  {key.replace('dc_', '').replace('_', ' ')}
                </dt>
                <dd className="mt-1 text-gray-900">
                  {Array.isArray(value) ? value.join(', ') : String(value)}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {/* Metadatos enriquecidos */}
      {instrumento.metadatos_enriquecidos && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Metadatos Enriquecidos</h3>
          <dl className="space-y-3 text-sm">
            {instrumento.metadatos_enriquecidos.poblacion_objetivo && (
              <div className="border-b border-gray-100 pb-3">
                <dt className="font-medium text-gray-500">Población Objetivo</dt>
                <dd className="mt-1 text-gray-900">
                  {instrumento.metadatos_enriquecidos.poblacion_objetivo}
                </dd>
              </div>
            )}
            {instrumento.metadatos_enriquecidos.unidad_analisis && (
              <div className="border-b border-gray-100 pb-3">
                <dt className="font-medium text-gray-500">Unidad de Análisis</dt>
                <dd className="mt-1 text-gray-900">
                  {instrumento.metadatos_enriquecidos.unidad_analisis}
                </dd>
              </div>
            )}
            {instrumento.metadatos_enriquecidos.sector_economico && (
              <div className="border-b border-gray-100 pb-3">
                <dt className="font-medium text-gray-500">Sector Económico</dt>
                <dd className="mt-1 text-gray-900">
                  {instrumento.metadatos_enriquecidos.sector_economico}
                </dd>
              </div>
            )}
            {instrumento.metadatos_enriquecidos.ambito_geografico && (
              <div className="border-b border-gray-100 pb-3">
                <dt className="font-medium text-gray-500">Ámbito Geográfico</dt>
                <dd className="mt-1 text-gray-900">
                  {instrumento.metadatos_enriquecidos.ambito_geografico}
                </dd>
              </div>
            )}
            {instrumento.metadatos_enriquecidos.dominio_tematico && (
              <div className="border-b border-gray-100 pb-3">
                <dt className="font-medium text-gray-500">Dominio Temático</dt>
                <dd className="mt-1 text-gray-900">
                  {instrumento.metadatos_enriquecidos.dominio_tematico}
                </dd>
              </div>
            )}
            {instrumento.metadatos_enriquecidos.metodologia_levantamiento && (
              <div className="border-b border-gray-100 pb-3">
                <dt className="font-medium text-gray-500">Metodología de Levantamiento</dt>
                <dd className="mt-1 text-gray-900">
                  {instrumento.metadatos_enriquecidos.metodologia_levantamiento}
                </dd>
              </div>
            )}
            {instrumento.metadatos_enriquecidos.nivel_educativo && (
              <div className="border-b border-gray-100 pb-3">
                <dt className="font-medium text-gray-500">Nivel Educativo</dt>
                <dd className="mt-1 text-gray-900">
                  {instrumento.metadatos_enriquecidos.nivel_educativo}
                </dd>
              </div>
            )}
            {instrumento.metadatos_enriquecidos.periodicidad && (
              <div className="border-b border-gray-100 pb-3">
                <dt className="font-medium text-gray-500">Periodicidad</dt>
                <dd className="mt-1 text-gray-900">
                  {instrumento.metadatos_enriquecidos.periodicidad}
                </dd>
              </div>
            )}
            {instrumento.metadatos_enriquecidos.tamano_muestra && (
              <div className="border-b border-gray-100 pb-3">
                <dt className="font-medium text-gray-500">Tamaño de Muestra</dt>
                <dd className="mt-1 text-gray-900">
                  {instrumento.metadatos_enriquecidos.tamano_muestra}
                </dd>
              </div>
            )}
          </dl>
        </div>
      )}

      {/* KPIs asociados */}
      {instrumento.kpis_inferidos_detalle && instrumento.kpis_inferidos_detalle.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">
            KPIs Asociados ({instrumento.kpis_inferidos_detalle.length})
          </h3>
          <div className="space-y-3">
            {instrumento.kpis_inferidos_detalle.map((kpi, index) => (
              <div
                key={index}
                className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-medium text-gray-900">{kpi.nombre_kpi}</h4>
                    {kpi.tipo_relacion && (
                      <span className="inline-block mt-1 px-2 py-1 text-xs rounded-full bg-purple-100 text-purple-800">
                        {kpi.tipo_relacion}
                      </span>
                    )}
                    {kpi.evidencia_textual && (
                      <p className="mt-2 text-sm text-gray-600 italic">
                        "{kpi.evidencia_textual}"
                      </p>
                    )}
                  </div>
                  <div className="text-right ml-4">
                    {kpi.score_inferencia && (
                      <div className="text-sm">
                        <span className="text-gray-500">Score:</span>
                        <span className="ml-1 font-medium text-blue-600">
                          {(kpi.score_inferencia * 100).toFixed(0)}%
                        </span>
                      </div>
                    )}
                    <span
                      className={`inline-block mt-1 text-xs px-2 py-1 rounded-full ${
                        kpi.origen === 'registro_manual'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-blue-100 text-blue-800'
                      }`}
                    >
                      {kpi.origen === 'registro_manual' ? 'Manual' : 'ETL'}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error */}
      {instrumento.error_detalle && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            <div>
              <p className="text-sm font-medium text-red-800">Error en el procesamiento</p>
              <p className="text-sm text-red-700 mt-1">{instrumento.error_detalle}</p>
            </div>
          </div>
        </div>
      )}

      {/* Botones de descarga */}
      <DownloadButtons instrumento={instrumento} />
    </div>
  );
}
