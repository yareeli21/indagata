/**
 * Servicio centralizado para todas las operaciones de instrumentos
 * 
 * REGLA CRÍTICA: Ningún componente puede llamar fetch() o axios directamente.
 * Toda comunicación con el backend debe pasar por este servicio.
 * 
 * Endpoints mapeados:
 * - POST   /instrumentos/upload           → upload()
 * - POST   /instrumentos/metadata         → createMetadata()
 * - GET    /instrumentos/{id}/etl/extract → extractETL()
 * - GET    /instrumentos/{id}/etl/proposals → getProposals()
 * - POST   /instrumentos/{id}/etl/approve → approveProposals()
 * - POST   /instrumentos/ingesta          → ingest()
 * - GET    /instrumentos                  → list()
 * - GET    /instrumentos/{id}             → getDetail()
 * - GET    /instrumentos/{id}/download    → download()
 * - DELETE /instrumentos/{id}             → deleteInstrumento()
 */

import apiClient, { extractErrorMessage } from './apiClient';
import type {
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
  FiltrosInstrumento,
  InstrumentoResumen,
  InstrumentoDetalle,
  EliminacionResponse,
  TipoDescarga,
} from '../types';

/**
 * Clase de servicio para operaciones de instrumentos
 */
class InstrumentosService {
  private readonly basePath = '/instrumentos';

  /**
   * PASO 1: Subir archivo
   * POST /instrumentos/upload
   */
  async upload(request: UploadWithFileRequest): Promise<UploadResponse> {
    try {
      const formData = new FormData();
      formData.append('archivo', request.file);
      formData.append('tipo_instrumento', request.tipo_instrumento);
      
      if (request.visibilidad) {
        formData.append('visibilidad', request.visibilidad);
      }

      const response = await apiClient.post<UploadResponse>(
        `${this.basePath}/upload`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      return response.data;
    } catch (error) {
      const message = extractErrorMessage(error);
      throw new Error(`Error al subir archivo: ${message}`);
    }
  }

  /**
   * PASO 2: Registrar metadatos Dublin Core + KPIs base
   * POST /instrumentos/metadata
   */
  async createMetadata(request: MetadataRequest): Promise<MetadataResponse> {
    try {
      const response = await apiClient.post<MetadataResponse>(
        `${this.basePath}/metadata`,
        request
      );

      return response.data;
    } catch (error) {
      const message = extractErrorMessage(error);
      throw new Error(`Error al registrar metadatos: ${message}`);
    }
  }

  /**
   * PASO 3: Analizar instrumento (extracción ETL)
   * GET /instrumentos/{id}/etl/extract
   */
  async extractETL(instrumentoId: number): Promise<EtlExtractResponse> {
    try {
      const response = await apiClient.get<EtlExtractResponse>(
        `${this.basePath}/${instrumentoId}/etl/extract`
      );

      return response.data;
    } catch (error) {
      const message = extractErrorMessage(error);
      throw new Error(`Error al analizar instrumento: ${message}`);
    }
  }

  /**
   * PASO 4: Obtener propuestas ETL generadas por el LLM
   * GET /instrumentos/{id}/etl/proposals
   */
  async getProposals(instrumentoId: number): Promise<EtlProposalsResponse> {
    try {
      const response = await apiClient.get<EtlProposalsResponse>(
        `${this.basePath}/${instrumentoId}/etl/proposals`
      );

      return response.data;
    } catch (error) {
      const message = extractErrorMessage(error);
      throw new Error(`Error al obtener propuestas ETL: ${message}`);
    }
  }

  /**
   * PASO 4: Aprobar o rechazar propuestas ETL
   * POST /instrumentos/{id}/etl/approve
   */
  async approveProposals(
    instrumentoId: number,
    request: AprobacionRequest
  ): Promise<AprobacionResponse> {
    try {
      const response = await apiClient.post<AprobacionResponse>(
        `${this.basePath}/${instrumentoId}/etl/approve`,
        request
      );

      return response.data;
    } catch (error) {
      const message = extractErrorMessage(error);
      throw new Error(`Error al aprobar propuestas: ${message}`);
    }
  }

  /**
   * PASO 5: Ejecutar ingesta final
   * POST /instrumentos/ingesta
   */
  async ingest(request: IngestaRequest): Promise<IngestaResponse> {
    try {
      const response = await apiClient.post<IngestaResponse>(
        `${this.basePath}/ingesta`,
        request
      );

      return response.data;
    } catch (error) {
      const message = extractErrorMessage(error);
      throw new Error(`Error al ejecutar ingesta: ${message}`);
    }
  }

  /**
   * Listar instrumentos con filtros opcionales
   * GET /instrumentos
   */
  async list(filtros?: FiltrosInstrumento): Promise<InstrumentoResumen[]> {
    try {
      const params: Record<string, any> = {};
      
      if (filtros) {
        if (filtros.tipo_instrumento) params.tipo_instrumento = filtros.tipo_instrumento;
        if (filtros.idioma) params.idioma = filtros.idioma;
        if (filtros.kpi_id) params.kpi_id = filtros.kpi_id;
        if (filtros.skip !== undefined) params.skip = filtros.skip;
        if (filtros.limit !== undefined) params.limit = filtros.limit;
      }

      const response = await apiClient.get<InstrumentoResumen[]>(
        this.basePath,
        { params }
      );

      return response.data;
    } catch (error) {
      const message = extractErrorMessage(error);
      throw new Error(`Error al listar instrumentos: ${message}`);
    }
  }

  /**
   * Obtener detalle completo de un instrumento
   * GET /instrumentos/{id}
   */
  async getDetail(instrumentoId: number): Promise<InstrumentoDetalle> {
    try {
      const response = await apiClient.get<InstrumentoDetalle>(
        `${this.basePath}/${instrumentoId}`
      );

      return response.data;
    } catch (error) {
      const message = extractErrorMessage(error);
      throw new Error(`Error al obtener detalle: ${message}`);
    }
  }

  /**
   * Descargar archivo del instrumento
   * GET /instrumentos/{id}/download?type={original|json|sav}
   * 
   * Retorna la URL del blob para descarga directa
   */
  async download(
    instrumentoId: number,
    tipo: TipoDescarga
  ): Promise<Blob> {
    try {
      const response = await apiClient.get(
        `${this.basePath}/${instrumentoId}/download`,
        {
          params: { type: tipo },
          responseType: 'blob',
        }
      );

      return response.data;
    } catch (error) {
      const message = extractErrorMessage(error);
      throw new Error(`Error al descargar archivo: ${message}`);
    }
  }

  /**
   * Helper para iniciar descarga en el navegador
   */
  async downloadFile(
    instrumentoId: number,
    tipo: TipoDescarga,
    nombreArchivo: string
  ): Promise<void> {
    try {
      const blob = await this.download(instrumentoId, tipo);
      
      // Crear URL temporal del blob
      const url = window.URL.createObjectURL(blob);
      
      // Crear elemento <a> temporal para descarga
      const link = document.createElement('a');
      link.href = url;
      link.download = nombreArchivo;
      document.body.appendChild(link);
      link.click();
      
      // Limpiar
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      const message = extractErrorMessage(error);
      throw new Error(`Error al descargar archivo: ${message}`);
    }
  }

  /**
   * Eliminar instrumento
   * DELETE /instrumentos/{id}
   */
  async deleteInstrumento(instrumentoId: number): Promise<EliminacionResponse> {
    try {
      const response = await apiClient.delete<EliminacionResponse>(
        `${this.basePath}/${instrumentoId}`
      );

      return response.data;
    } catch (error) {
      const message = extractErrorMessage(error);
      throw new Error(`Error al eliminar instrumento: ${message}`);
    }
  }

  /**
   * Verificar estado de un instrumento
   * Helper útil para polling durante procesos largos
   */
  async checkStatus(instrumentoId: number): Promise<InstrumentoDetalle> {
    return this.getDetail(instrumentoId);
  }
}

// Exportar instancia única del servicio (Singleton)
export const instrumentosService = new InstrumentosService();

// Exportar la clase para testing si es necesario
export default InstrumentosService;
