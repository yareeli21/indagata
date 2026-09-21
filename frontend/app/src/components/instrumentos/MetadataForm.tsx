/**
 * Componente MetadataForm - PASO 2: Registrar metadatos Dublin Core
 * 
 * Formulario para los 13 campos DC obligatorios + 2 opcionales.
 * Incluye sección para agregar KPIs base conocidos.
 */

import { useState } from 'react';
import type { MetadataRequest, KpiInferidoInput } from '../../types';
import { DUBLIN_CORE_LABELS } from '../../types/constants';
import LoadingSpinner from '../common/LoadingSpinner';
import ErrorAlert from '../common/ErrorAlert';

interface MetadataFormProps {
  instrumentoId: number;
  onSubmit: (request: MetadataRequest) => Promise<void>;
  loading: boolean;
  error: string | null;
}

export default function MetadataForm({ instrumentoId, onSubmit, loading, error }: MetadataFormProps) {
  // Estados para campos Dublin Core
  const [formData, setFormData] = useState({
    dc_title: '',
    dc_creator: '',
    dc_subject: '',
    dc_description: '',
    dc_publisher: '',
    dc_contributor: '',
    dc_date: '',
    dc_type: '',
    dc_format: '',
    dc_identifier: '',
    dc_language: 'es',
    dc_coverage: '',
    dc_rights: '',
    dc_source: '',
    dc_relation: '',
  });

  // Estado para KPIs (placeholder - en producción vendría de una API)
  const [kpis, _setKpis] = useState<KpiInferidoInput[]>([]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const request: MetadataRequest = {
      instrumento_id: instrumentoId,
      ...formData,
      dc_subject: formData.dc_subject.split(',').map(s => s.trim()),
      kpis_inferidos: kpis,
    };

    await onSubmit(request);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && <ErrorAlert message={error} />}

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          <strong>Dublin Core:</strong> Estándar internacional de metadatos para recursos digitales.
          Complete los 13 campos obligatorios.
        </p>
      </div>

      {/* Campos obligatorios */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Título */}
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {DUBLIN_CORE_LABELS.dc_title} *
          </label>
          <input
            type="text"
            name="dc_title"
            value={formData.dc_title}
            onChange={handleChange}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
        </div>

        {/* Creador */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {DUBLIN_CORE_LABELS.dc_creator} *
          </label>
          <input
            type="text"
            name="dc_creator"
            value={formData.dc_creator}
            onChange={handleChange}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
        </div>

        {/* Editor/Institución */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {DUBLIN_CORE_LABELS.dc_publisher} *
          </label>
          <input
            type="text"
            name="dc_publisher"
            value={formData.dc_publisher}
            onChange={handleChange}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
        </div>

        {/* Temas */}
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {DUBLIN_CORE_LABELS.dc_subject} *
          </label>
          <input
            type="text"
            name="dc_subject"
            value={formData.dc_subject}
            onChange={handleChange}
            placeholder="Educación, Evaluación, Matemáticas"
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
          <p className="mt-1 text-xs text-gray-500">Separados por comas</p>
        </div>

        {/* Descripción */}
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {DUBLIN_CORE_LABELS.dc_description} *
          </label>
          <textarea
            name="dc_description"
            value={formData.dc_description}
            onChange={handleChange}
            rows={4}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
        </div>

        {/* Colaborador */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {DUBLIN_CORE_LABELS.dc_contributor} *
          </label>
          <input
            type="text"
            name="dc_contributor"
            value={formData.dc_contributor}
            onChange={handleChange}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
        </div>

        {/* Fecha */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {DUBLIN_CORE_LABELS.dc_date} *
          </label>
          <input
            type="date"
            name="dc_date"
            value={formData.dc_date}
            onChange={handleChange}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
        </div>

        {/* Tipo */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {DUBLIN_CORE_LABELS.dc_type} *
          </label>
          <input
            type="text"
            name="dc_type"
            value={formData.dc_type}
            onChange={handleChange}
            placeholder="Instrumento de evaluación"
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
        </div>

        {/* Formato */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {DUBLIN_CORE_LABELS.dc_format} *
          </label>
          <input
            type="text"
            name="dc_format"
            value={formData.dc_format}
            onChange={handleChange}
            placeholder="PDF, DOCX, etc."
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
        </div>

        {/* Identificador */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {DUBLIN_CORE_LABELS.dc_identifier} *
          </label>
          <input
            type="text"
            name="dc_identifier"
            value={formData.dc_identifier}
            onChange={handleChange}
            placeholder="ISBN, DOI, URL, etc."
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
        </div>

        {/* Idioma */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {DUBLIN_CORE_LABELS.dc_language} *
          </label>
          <input
            type="text"
            name="dc_language"
            value={formData.dc_language}
            onChange={handleChange}
            placeholder="es, en, fr, etc."
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
        </div>

        {/* Cobertura */}
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {DUBLIN_CORE_LABELS.dc_coverage} *
          </label>
          <input
            type="text"
            name="dc_coverage"
            value={formData.dc_coverage}
            onChange={handleChange}
            placeholder="México, 2020-2024, Educación básica"
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
        </div>

        {/* Derechos */}
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {DUBLIN_CORE_LABELS.dc_rights} *
          </label>
          <input
            type="text"
            name="dc_rights"
            value={formData.dc_rights}
            onChange={handleChange}
            placeholder="© 2024, CC BY-NC-SA, etc."
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            required
          />
        </div>

        {/* Campos opcionales */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {DUBLIN_CORE_LABELS.dc_source}
          </label>
          <input
            type="text"
            name="dc_source"
            value={formData.dc_source}
            onChange={handleChange}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {DUBLIN_CORE_LABELS.dc_relation}
          </label>
          <input
            type="text"
            name="dc_relation"
            value={formData.dc_relation}
            onChange={handleChange}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Sección KPIs (placeholder) */}
      <div className="border-t pt-6">
        <h3 className="text-lg font-semibold mb-4">KPIs Base Conocidos (Opcional)</h3>
        <p className="text-sm text-gray-600 mb-4">
          Esta sección permitirá seleccionar KPIs conocidos asociados al instrumento.
          Implementación completa pendiente.
        </p>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
          <p className="text-gray-500 text-sm">Selector de KPIs en desarrollo</p>
        </div>
      </div>

      {/* Botón */}
      <div className="flex justify-end pt-6 border-t">
        {loading ? (
          <LoadingSpinner message="Registrando metadatos..." />
        ) : (
          <button
            type="submit"
            className="px-6 py-2 bg-green-500 hover:bg-green-600 text-white font-medium rounded-md transition-colors"
          >
            Registrar Metadatos
          </button>
        )}
      </div>
    </form>
  );
}
