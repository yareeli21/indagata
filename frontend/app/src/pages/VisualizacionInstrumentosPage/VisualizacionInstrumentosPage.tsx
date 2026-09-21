/**
 * Página de Visualización y Descarga de Instrumentos
 * 
 * Área 1: Catálogo filtrable de instrumentos
 * Área 2: Detalle del instrumento seleccionado
 * 
 * Layout de dos columnas:
 * - Izquierda (2/3): Filtros + Tabla de instrumentos
 * - Derecha (1/3): Detalle del instrumento seleccionado
 */

import { useState, useEffect } from 'react';
import { instrumentosService } from '../../services';
import type {
  InstrumentoResumen,
  InstrumentoDetalle,
  FiltrosInstrumento,
  FiltrosActivos,
} from '../../types';
import {
  SearchFilters,
  InstrumentosTable,
  InstrumentoDetalle as InstrumentoDetalleComponent,
} from '../../components/instrumentos';
import { ErrorAlert } from '../../components/common';

export default function VisualizacionInstrumentosPage() {
  // Estados para el catálogo
  const [instrumentos, setInstrumentos] = useState<InstrumentoResumen[]>([]);
  const [loadingList, setLoadingList] = useState<boolean>(true);
  const [errorList, setErrorList] = useState<string | null>(null);

  // Estados para el detalle
  const [selectedInstrumento, setSelectedInstrumento] = useState<InstrumentoResumen | null>(null);
  const [instrumentoDetalle, setInstrumentoDetalle] = useState<InstrumentoDetalle | null>(null);
  const [loadingDetalle, setLoadingDetalle] = useState<boolean>(false);
  const [errorDetalle, setErrorDetalle] = useState<string | null>(null);

  // Estados para filtros
  const [filtrosActivos, setFiltrosActivos] = useState<FiltrosActivos>({
    tipo_instrumento: null,
    idioma: '',
    kpi_id: null,
  });

  // Cargar lista de instrumentos
  const cargarInstrumentos = async () => {
    setLoadingList(true);
    setErrorList(null);

    try {
      const filtros: FiltrosInstrumento = {
        tipo_instrumento: filtrosActivos.tipo_instrumento,
        idioma: filtrosActivos.idioma || undefined,
        kpi_id: filtrosActivos.kpi_id || undefined,
        skip: 0,
        limit: 50,
      };

      const data = await instrumentosService.list(filtros);
      setInstrumentos(data);
    } catch (err) {
      setErrorList(err instanceof Error ? err.message : 'Error al cargar instrumentos');
    } finally {
      setLoadingList(false);
    }
  };

  // Cargar detalle del instrumento seleccionado
  const cargarDetalle = async (instrumento: InstrumentoResumen) => {
    setSelectedInstrumento(instrumento);
    setLoadingDetalle(true);
    setErrorDetalle(null);

    try {
      const detalle = await instrumentosService.getDetail(instrumento.instrumento_id);
      setInstrumentoDetalle(detalle);
    } catch (err) {
      setErrorDetalle(err instanceof Error ? err.message : 'Error al cargar detalle');
      setInstrumentoDetalle(null);
    } finally {
      setLoadingDetalle(false);
    }
  };

  // Cargar instrumentos al montar y cuando cambian los filtros
  useEffect(() => {
    cargarInstrumentos();
  }, [filtrosActivos]);

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-[1920px] mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Instrumentos de Investigación
              </h1>
              <p className="text-gray-600">
                Catálogo completo de instrumentos procesados en el sistema
              </p>
            </div>
            <a
              href="/cargar"
              className="px-6 py-2 bg-green-500 hover:bg-green-600 text-white font-medium rounded-md transition-colors"
            >
              + Cargar Nuevo
            </a>
          </div>
        </div>

        {/* Error global */}
        {errorList && (
          <div className="mb-6">
            <ErrorAlert message={errorList} onClose={() => setErrorList(null)} />
          </div>
        )}

        {/* Layout de dos áreas */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* ÁREA 1: Catálogo (2/3 del espacio) */}
          <div className="lg:col-span-2 space-y-6">
            {/* Filtros */}
            <SearchFilters
              filtros={filtrosActivos}
              onFiltrosChange={setFiltrosActivos}
            />

            {/* Tabla de instrumentos */}
            <InstrumentosTable
              instrumentos={instrumentos}
              selectedId={selectedInstrumento?.instrumento_id || null}
              onSelect={cargarDetalle}
              loading={loadingList}
            />
          </div>

          {/* ÁREA 2: Detalle (1/3 del espacio) */}
          <div className="lg:col-span-1">
            <div className="lg:sticky lg:top-6">
              {errorDetalle && (
                <div className="mb-4">
                  <ErrorAlert message={errorDetalle} onClose={() => setErrorDetalle(null)} />
                </div>
              )}
              
              <InstrumentoDetalleComponent
                instrumento={instrumentoDetalle}
                loading={loadingDetalle}
              />
            </div>
          </div>
        </div>

        {/* Resumen estadístico */}
        <div className="mt-8 bg-white rounded-lg shadow p-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div>
              <p className="text-3xl font-bold text-blue-600">{instrumentos.length}</p>
              <p className="text-sm text-gray-600">Instrumentos</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-green-600">
                {instrumentos.filter((i) => i.tipo_instrumento === 'encuesta').length}
              </p>
              <p className="text-sm text-gray-600">Encuestas</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-purple-600">
                {instrumentos.filter((i) => i.tipo_instrumento === 'entrevista').length}
              </p>
              <p className="text-sm text-gray-600">Entrevistas</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-orange-600">
                {instrumentos.filter((i) => i.tipo_instrumento === 'prueba_estandarizada').length}
              </p>
              <p className="text-sm text-gray-600">Pruebas</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
