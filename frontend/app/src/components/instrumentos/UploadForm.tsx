/**
 * Componente UploadForm - PASO 1: Subir archivo
 * 
 * Formulario para subir el archivo del instrumento.
 * Campos: archivo, tipo_instrumento, visibilidad
 */

import { useState } from 'react';
import type { TipoInstrumento, Visibilidad, UploadWithFileRequest } from '../../types';
import { TIPO_INSTRUMENTO_LABELS, ACCEPTED_FILE_TYPES } from '../../types/constants';
import LoadingSpinner from '../common/LoadingSpinner';
import ErrorAlert from '../common/ErrorAlert';

interface UploadFormProps {
  onSubmit: (request: UploadWithFileRequest) => Promise<void>;
  loading: boolean;
  error: string | null;
}

export default function UploadForm({ onSubmit, loading, error }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [tipoInstrumento, setTipoInstrumento] = useState<TipoInstrumento>('encuesta');
  const [visibilidad, setVisibilidad] = useState<Visibilidad>('public');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!file) {
      alert('Debe seleccionar un archivo');
      return;
    }

    await onSubmit({
      file,
      tipo_instrumento: tipoInstrumento,
      visibilidad,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && <ErrorAlert message={error} />}

      {/* Tipo de instrumento */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Tipo de Instrumento *
        </label>
        <select
          value={tipoInstrumento}
          onChange={(e) => setTipoInstrumento(e.target.value as TipoInstrumento)}
          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          required
        >
          {Object.entries(TIPO_INSTRUMENTO_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-gray-500">
          Archivos aceptados: {ACCEPTED_FILE_TYPES[tipoInstrumento]}
        </p>
      </div>

      {/* Archivo */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Archivo del Instrumento *
        </label>
        <input
          type="file"
          onChange={handleFileChange}
          accept={ACCEPTED_FILE_TYPES[tipoInstrumento]}
          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          required
        />
        {file && (
          <p className="mt-2 text-sm text-gray-600">
            Seleccionado: <strong>{file.name}</strong> ({(file.size / 1024).toFixed(2)} KB)
          </p>
        )}
      </div>

      {/* Visibilidad */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Visibilidad *
        </label>
        <div className="flex space-x-4">
          <label className="flex items-center">
            <input
              type="radio"
              value="public"
              checked={visibilidad === 'public'}
              onChange={(e) => setVisibilidad(e.target.value as Visibilidad)}
              className="mr-2"
            />
            <span className="text-sm text-gray-700">Público</span>
          </label>
          <label className="flex items-center">
            <input
              type="radio"
              value="private"
              checked={visibilidad === 'private'}
              onChange={(e) => setVisibilidad(e.target.value as Visibilidad)}
              className="mr-2"
            />
            <span className="text-sm text-gray-700">Privado</span>
          </label>
        </div>
        <p className="mt-1 text-xs text-gray-500">
          Esta configuración es inmutable después de la subida.
        </p>
      </div>

      {/* Botón */}
      <div className="flex justify-end">
        {loading ? (
          <LoadingSpinner message="Subiendo archivo..." />
        ) : (
          <button
            type="submit"
            className="px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white font-medium rounded-md transition-colors"
          >
            Subir Archivo
          </button>
        )}
      </div>
    </form>
  );
}
