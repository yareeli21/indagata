/**
 * Componente ETLProposalsPanel - PASO 4: Revisar propuestas ETL
 * 
 * Muestra todas las propuestas generadas por el LLM.
 * Permite aceptar o rechazar cada propuesta individualmente.
 * Construye el payload de AprobacionRequest automáticamente.
 */

import { useState, useEffect } from 'react';
import type { EtlPropuestaOutput, AprobacionRequest, DecisionInput } from '../../types';
import LoadingSpinner from '../common/LoadingSpinner';
import ErrorAlert from '../common/ErrorAlert';

interface ETLProposalsPanelProps {
  instrumentoId: number;
  propuestas: EtlPropuestaOutput[];
  onApprove: (request: AprobacionRequest) => Promise<void>;
  loading: boolean;
  error: string | null;
}

export default function ETLProposalsPanel({
  instrumentoId,
  propuestas,
  onApprove,
  loading,
  error,
}: ETLProposalsPanelProps) {
  // Estado local de decisiones
  const [decisiones, setDecisiones] = useState<Map<number, 'aceptada' | 'rechazada'>>(new Map());

  useEffect(() => {
    // Inicializar con propuestas pendientes
    const initialDecisions = new Map<number, 'aceptada' | 'rechazada'>();
    propuestas.forEach((p) => {
      if (p.estado_decision === 'aceptada') initialDecisions.set(p.propuesta_id, 'aceptada');
      if (p.estado_decision === 'rechazada') initialDecisions.set(p.propuesta_id, 'rechazada');
    });
    setDecisiones(initialDecisions);
  }, [propuestas]);

  const handleDecision = (propuestaId: number, decision: 'aceptada' | 'rechazada') => {
    setDecisiones((prev) => {
      const newDecisiones = new Map(prev);
      newDecisiones.set(propuestaId, decision);
      return newDecisiones;
    });
  };

  const handleSubmit = async () => {
    // Construir payload
    const decisionesArray: DecisionInput[] = Array.from(decisiones.entries()).map(
      ([propuesta_id, decision]) => ({
        propuesta_id,
        decision,
      })
    );

    const request: AprobacionRequest = {
      instrumento_id: instrumentoId,
      decisiones: decisionesArray,
    };

    await onApprove(request);
  };

  const propuestasPendientes = propuestas.filter((p) => p.estado_decision === 'pendiente');
  const allDecided = propuestasPendientes.every((p) => decisiones.has(p.propuesta_id));

  // Agrupar por tipo
  const propuestasPorTipo = {
    transformacion: propuestas.filter((p) => p.tipo === 'transformacion'),
    metadato_enriquecido: propuestas.filter((p) => p.tipo === 'metadato_enriquecido'),
    kpi_sugerido: propuestas.filter((p) => p.tipo === 'kpi_sugerido'),
  };

  const tipoColors = {
    transformacion: 'purple',
    metadato_enriquecido: 'green',
    kpi_sugerido: 'orange',
  };

  const tipoLabels = {
    transformacion: 'Transformación de Datos',
    metadato_enriquecido: 'Metadato Enriquecido',
    kpi_sugerido: 'KPI Sugerido',
  };

  return (
    <div className="space-y-6">
      {error && <ErrorAlert message={error} />}

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          <strong>Revisar propuestas:</strong> El LLM ha analizado el instrumento y generó{' '}
          <strong>{propuestas.length} propuestas</strong>. Revise cada una y decida si aceptarla o
          rechazarla.
        </p>
      </div>

      {/* Resumen */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-2xl font-bold text-gray-900">{propuestasPendientes.length}</p>
            <p className="text-sm text-gray-600">Pendientes</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-green-600">{decisiones.size}</p>
            <p className="text-sm text-gray-600">Decididas</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-blue-600">{propuestas.length}</p>
            <p className="text-sm text-gray-600">Total</p>
          </div>
        </div>
      </div>

      {/* Propuestas agrupadas por tipo */}
      {Object.entries(propuestasPorTipo).map(([tipo, items]) =>
        items.length > 0 ? (
          <div key={tipo} className="space-y-4">
            <h3 className="text-lg font-semibold flex items-center space-x-2">
              <span
                className={`w-3 h-3 rounded-full bg-${
                  tipoColors[tipo as keyof typeof tipoColors]
                }-500`}
              />
              <span>{tipoLabels[tipo as keyof typeof tipoLabels]}</span>
              <span className="text-sm font-normal text-gray-500">({items.length})</span>
            </h3>

            {items.map((propuesta) => (
              <PropuestaCard
                key={propuesta.propuesta_id}
                propuesta={propuesta}
                decision={decisiones.get(propuesta.propuesta_id)}
                onDecision={handleDecision}
                color={tipoColors[tipo as keyof typeof tipoColors]}
              />
            ))}
          </div>
        ) : null
      )}

      {/* Botón de aprobación */}
      <div className="flex justify-end pt-6 border-t">
        {loading ? (
          <LoadingSpinner message="Guardando decisiones..." />
        ) : (
          <button
            onClick={handleSubmit}
            disabled={!allDecided}
            className="px-8 py-3 bg-green-500 hover:bg-green-600 text-white font-medium rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {allDecided ? 'Guardar Decisiones' : `Faltan ${propuestasPendientes.length - decisiones.size} decisiones`}
          </button>
        )}
      </div>
    </div>
  );
}

// Componente para una tarjeta de propuesta individual
interface PropuestaCardProps {
  propuesta: EtlPropuestaOutput;
  decision?: 'aceptada' | 'rechazada';
  onDecision: (propuestaId: number, decision: 'aceptada' | 'rechazada') => void;
  color: string;
}

function PropuestaCard({ propuesta, decision, onDecision, color }: PropuestaCardProps) {
  const isPending = propuesta.estado_decision === 'pendiente';

  return (
    <div
      className={`border-2 rounded-lg p-4 transition-all ${
        decision === 'aceptada'
          ? 'border-green-500 bg-green-50'
          : decision === 'rechazada'
          ? 'border-red-500 bg-red-50'
          : 'border-gray-200 bg-white'
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h4 className="font-semibold text-gray-900">{propuesta.descripcion}</h4>
          <p className="text-sm text-gray-600 mt-1">{propuesta.accion_sugerida}</p>
        </div>
        <span
          className={`ml-4 px-3 py-1 rounded-full text-xs font-medium bg-${color}-100 text-${color}-800`}
        >
          ID: {propuesta.propuesta_id}
        </span>
      </div>

      {/* Detalles */}
      <div className="space-y-2 text-sm">
        <div>
          <strong className="text-gray-700">Justificación:</strong>
          <p className="text-gray-600 mt-1">{propuesta.justificacion}</p>
        </div>

        {propuesta.impacto_esperado && (
          <div>
            <strong className="text-gray-700">Impacto esperado:</strong>
            <p className="text-gray-600 mt-1">{propuesta.impacto_esperado}</p>
          </div>
        )}

        {propuesta.valor_original && (
          <div className="grid grid-cols-2 gap-4 mt-3">
            <div className="bg-gray-100 rounded p-3">
              <strong className="text-gray-700 text-xs">Valor original:</strong>
              <p className="text-gray-800 mt-1 font-mono text-xs">{propuesta.valor_original}</p>
            </div>
            {propuesta.valor_propuesto && (
              <div className="bg-blue-100 rounded p-3">
                <strong className="text-blue-700 text-xs">Valor propuesto:</strong>
                <p className="text-blue-800 mt-1 font-mono text-xs">{propuesta.valor_propuesto}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Botones de decisión */}
      {isPending && (
        <div className="flex space-x-3 mt-4 pt-4 border-t">
          <button
            onClick={() => onDecision(propuesta.propuesta_id, 'aceptada')}
            className={`flex-1 py-2 rounded-md font-medium transition-colors ${
              decision === 'aceptada'
                ? 'bg-green-500 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-green-100 hover:text-green-700'
            }`}
          >
            ✓ Aceptar
          </button>
          <button
            onClick={() => onDecision(propuesta.propuesta_id, 'rechazada')}
            className={`flex-1 py-2 rounded-md font-medium transition-colors ${
              decision === 'rechazada'
                ? 'bg-red-500 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-red-100 hover:text-red-700'
            }`}
          >
            ✗ Rechazar
          </button>
        </div>
      )}
    </div>
  );
}
