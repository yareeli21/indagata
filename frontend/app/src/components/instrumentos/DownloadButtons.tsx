/**
 * Componente DownloadButtons - Botones de descarga de archivos
 * 
 * Permite descargar:
 * - Archivo original
 * - JSON enriquecido
 * - Archivo SAV (solo encuestas)
 */

import { useState } from 'react';
import type { InstrumentoDetalle, TipoDescarga } from '../../types';
import { instrumentosService } from '../../services';

interface DownloadButtonsProps {
  instrumento: InstrumentoDetalle;
}

export default function DownloadButtons({ instrumento }: DownloadButtonsProps) {
  const [downloading, setDownloading] = useState<TipoDescarga | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleDownload = async (tipo: TipoDescarga) => {
    setDownloading(tipo);
    setError(null);

    try {
      let filename = '';
      
      switch (tipo) {
        case 'original':
          filename = `${instrumento.nombre}_original`;
          break;
        case 'json':
          filename = `${instrumento.nombre}_enriquecido.json`;
          break;
        case 'sav':
          filename = `${instrumento.nombre}.sav`;
          break;
      }

      await instrumentosService.downloadFile(
        instrumento.instrumento_id,
        tipo,
        filename
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al descargar archivo');
    } finally {
      setDownloading(null);
    }
  };

  const isSavAvailable =
    instrumento.tipo_instrumento === 'encuesta' &&
    instrumento.fecha_procesamiento;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Descargas</h3>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Archivo original */}
        <button
          onClick={() => handleDownload('original')}
          disabled={downloading !== null}
          className="flex flex-col items-center justify-center p-4 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <svg
            className="w-8 h-8 text-gray-600 mb-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
            />
          </svg>
          <span className="font-medium text-gray-900">Original</span>
          <span className="text-xs text-gray-500 mt-1">
            {downloading === 'original' ? 'Descargando...' : 'Archivo subido'}
          </span>
        </button>

        {/* JSON enriquecido */}
        <button
          onClick={() => handleDownload('json')}
          disabled={downloading !== null || !instrumento.fecha_procesamiento}
          className="flex flex-col items-center justify-center p-4 border-2 border-gray-200 rounded-lg hover:border-green-500 hover:bg-green-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <svg
            className="w-8 h-8 text-gray-600 mb-2"
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
          <span className="font-medium text-gray-900">JSON</span>
          <span className="text-xs text-gray-500 mt-1">
            {downloading === 'json'
              ? 'Descargando...'
              : instrumento.fecha_procesamiento
              ? 'Enriquecido'
              : 'No disponible'}
          </span>
        </button>

        {/* SAV (solo encuestas) */}
        <button
          onClick={() => handleDownload('sav')}
          disabled={downloading !== null || !isSavAvailable}
          className="flex flex-col items-center justify-center p-4 border-2 border-gray-200 rounded-lg hover:border-purple-500 hover:bg-purple-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <svg
            className="w-8 h-8 text-gray-600 mb-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"
            />
          </svg>
          <span className="font-medium text-gray-900">SAV</span>
          <span className="text-xs text-gray-500 mt-1">
            {downloading === 'sav'
              ? 'Descargando...'
              : isSavAvailable
              ? 'SPSS/Stata'
              : 'Solo encuestas'}
          </span>
        </button>
      </div>

      <p className="text-xs text-gray-500 mt-4">
        Los archivos JSON y SAV solo están disponibles después de completar el proceso de ingesta.
      </p>
    </div>
  );
}
