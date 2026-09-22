/**
 * Página de Carga de Instrumentos
 * 
 * Wizard de 5 pasos controlado por estados del instrumento.
 * Los pasos se habilitan/deshabilitan según el estado retornado por el backend.
 * 
 * Flujo:
 * 1. Upload archivo → estado: pendiente
 * 2. Registrar metadatos → estado: metadata_registrado
 * 3. Analizar ETL → estado: etl_pendiente
 * 4. Revisar propuestas → estado: etl_aprobado
 * 5. Ejecutar ingesta → estado: vectorizado
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { instrumentosService } from '../../services';
import type {
  EstadoPipeline,
  UploadWithFileRequest,
  UploadResponse,
  MetadataRequest,
  MetadataResponse,
  EtlExtractResponse,
  EtlProposalsResponse,
  AprobacionRequest,
  AprobacionResponse,
  IngestaRequest,
  IngestaResponse,
} from '../../types';
import { WIZARD_STEP_TITLES, ESTADO_TO_WIZARD } from '../../types/constants';
import {
  Stepper,
  LoadingSpinner,
  ErrorAlert,
  SuccessMessage,
} from '../../components/common';
import {
  UploadForm,
  MetadataForm,
  ETLAnalysisPanel,
  ETLProposalsPanel,
  IngestaPanel,
} from '../../components/instrumentos';

export default function CargaInstrumentosPage() {
  const navigate = useNavigate();

  // Estado del wizard
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [enabledSteps, setEnabledSteps] = useState<number[]>([0, 1]);
  const [instrumentoId, setInstrumentoId] = useState<number | null>(null);
  const [estado, setEstado] = useState<EstadoPipeline>('pendiente');

  // Estados de carga y errores por paso
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Respuestas de cada paso
  const [uploadResponse, setUploadResponse] = useState<UploadResponse | null>(null);
  const [metadataResponse, setMetadataResponse] = useState<MetadataResponse | null>(null);
  const [etlExtractResponse, setEtlExtractResponse] = useState<EtlExtractResponse | null>(null);
  const [proposalsResponse, setProposalsResponse] = useState<EtlProposalsResponse | null>(null);
  const [aprobacionResponse, setAprobacionResponse] = useState<AprobacionResponse | null>(null);
  const [ingestaResponse, setIngestaResponse] = useState<IngestaResponse | null>(null);

  // Sincronizar wizard con estado del backend
  useEffect(() => {
    if (estado) {
      const mapping = ESTADO_TO_WIZARD[estado];
      if (mapping) {
        setCurrentStep(mapping.currentStep);
        setEnabledSteps(mapping.enabledSteps);
      }
    }
  }, [estado]);

  // Handler para PASO 1: Upload
  const handleUpload = async (request: UploadWithFileRequest) => {
    setLoading(true);
    setError(null);
    try {
      const response = await instrumentosService.upload(request);
      setUploadResponse(response);
      setInstrumentoId(response.instrumento_id);
      setEstado(response.estado);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al subir archivo');
    } finally {
      setLoading(false);
    }
  };

  // Handler para PASO 2: Metadatos
  const handleMetadata = async (request: MetadataRequest) => {
    setLoading(true);
    setError(null);
    try {
      const response = await instrumentosService.createMetadata(request);
      setMetadataResponse(response);
      setEstado(response.estado);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al registrar metadatos');
    } finally {
      setLoading(false);
    }
  };

  // Handler para PASO 3: Análisis ETL
  const handleExtractETL = async () => {
    if (!instrumentoId) return;
    
    setLoading(true);
    setError(null);
    try {
      const response = await instrumentosService.extractETL(instrumentoId);
      setEtlExtractResponse(response);
      setEstado(response.estado);
      
      // Cargar propuestas para el paso 4
      const proposals = await instrumentosService.getProposals(instrumentoId);
      setProposalsResponse(proposals);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al analizar instrumento');
    } finally {
      setLoading(false);
    }
  };

  // Handler para PASO 4: Aprobar propuestas
  const handleApproveProposals = async (request: AprobacionRequest) => {
    if (!instrumentoId) return;
    
    setLoading(true);
    setError(null);
    try {
      const response = await instrumentosService.approveProposals(instrumentoId, request);
      setAprobacionResponse(response);
      setEstado(response.estado);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al aprobar propuestas');
    } finally {
      setLoading(false);
    }
  };

  // Handler para PASO 5: Ingesta
  const handleIngest = async () => {
    if (!instrumentoId) return;
    
    setLoading(true);
    setError(null);
    try {
      const request: IngestaRequest = { instrumento_id: instrumentoId };
      const response = await instrumentosService.ingest(request);
      setIngestaResponse(response);
      setEstado('vectorizado');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al ejecutar ingesta');
    } finally {
      setLoading(false);
    }
  };

  // Renderizar contenido según paso actual
  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
      case 1:
        // PASO 1 y 2: Upload y Metadatos (ambos habilitados en estado pendiente)
        return (
          <div className="space-y-8">
            {/* Paso 1: Upload */}
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                Paso 1: Subir Archivo
              </h2>
              {uploadResponse ? (
                <SuccessMessage message={uploadResponse.mensaje} />
              ) : (
                <div className="bg-white rounded-lg shadow p-6">
                  <UploadForm
                    onSubmit={handleUpload}
                    loading={loading && !uploadResponse}
                    error={error}
                  />
                </div>
              )}
            </div>

            {/* Paso 2: Metadatos (solo si paso 1 completado) */}
            {uploadResponse && instrumentoId && (
              <div>
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  Paso 2: Registrar Metadatos Dublin Core
                </h2>
                {metadataResponse ? (
                  <SuccessMessage message={metadataResponse.mensaje} />
                ) : (
                  <div className="bg-white rounded-lg shadow p-6">
                    <MetadataForm
                      instrumentoId={instrumentoId}
                      onSubmit={handleMetadata}
                      loading={loading && !metadataResponse}
                      error={error}
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        );

      case 3:
        // PASO 3: Análisis ETL
        return (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              Paso 3: Analizar Instrumento
            </h2>
            <div className="bg-white rounded-lg shadow p-6">
              <ETLAnalysisPanel
                instrumentoId={instrumentoId!}
                onAnalyze={handleExtractETL}
                loading={loading}
                error={error}
                result={etlExtractResponse}
              />
            </div>
          </div>
        );

      case 4:
        // PASO 4: Revisar propuestas
        return (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              Paso 4: Revisar Propuestas ETL
            </h2>
            {aprobacionResponse ? (
              <SuccessMessage message={aprobacionResponse.mensaje} />
            ) : proposalsResponse ? (
              <div className="bg-white rounded-lg shadow p-6">
                <ETLProposalsPanel
                  instrumentoId={instrumentoId!}
                  propuestas={proposalsResponse.propuestas}
                  onApprove={handleApproveProposals}
                  loading={loading}
                  error={error}
                />
              </div>
            ) : (
              <LoadingSpinner message="Cargando propuestas..." />
            )}
          </div>
        );

      case 5:
        // PASO 5: Ingesta
        return (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              Paso 5: Ejecutar Ingesta Final
            </h2>
            <div className="bg-white rounded-lg shadow p-6">
              <IngestaPanel
                instrumentoId={instrumentoId!}
                onIngest={handleIngest}
                loading={loading}
                error={error}
                result={ingestaResponse}
              />
            </div>
          </div>
        );

      default:
        return (
          <div className="bg-gray-100 rounded-lg p-8 text-center">
            <p className="text-gray-500">Paso no disponible</p>
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Cargar Nuevo Instrumento
              </h1>
              <p className="text-gray-600">
                Proceso guiado de 5 pasos para ingresar instrumentos de investigación al sistema
              </p>
            </div>
            {instrumentoId && (
              <div className="text-right">
                <p className="text-sm text-gray-500">ID del Instrumento</p>
                <p className="text-2xl font-bold text-blue-600">{instrumentoId}</p>
              </div>
            )}
          </div>
        </div>

        {/* Stepper */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-8">
          <Stepper
            steps={WIZARD_STEP_TITLES}
            currentStep={currentStep}
            enabledSteps={enabledSteps}
          />
        </div>

        {/* Error global (estado = error) */}
        {estado === 'error' && (
          <div className="mb-8">
            <ErrorAlert 
              message="El instrumento tiene un error. Por favor contacte al administrador." 
            />
          </div>
        )}

        {/* Contenido del paso actual */}
        {renderStepContent()}

        {/* Botón de cancelar */}
        {estado !== 'vectorizado' && (
          <div className="mt-8 flex justify-center">
            <button
              onClick={() => navigate('/instrumentos')}
              className="px-6 py-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              Cancelar y volver
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
