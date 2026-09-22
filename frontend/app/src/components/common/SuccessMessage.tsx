/**
 * Componente SuccessMessage - Muestra mensajes de éxito
 */

interface SuccessMessageProps {
  message: string;
  onClose?: () => void;
}

export default function SuccessMessage({ message, onClose }: SuccessMessageProps) {
  return (
    <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-start space-x-3">
      {/* Icono */}
      <svg
        className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5"
        fill="currentColor"
        viewBox="0 0 20 20"
      >
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
          clipRule="evenodd"
        />
      </svg>

      {/* Mensaje */}
      <div className="flex-1">
        <p className="text-sm text-green-800 font-medium">Éxito</p>
        <p className="text-sm text-green-700 mt-1">{message}</p>
      </div>

      {/* Botón cerrar */}
      {onClose && (
        <button
          onClick={onClose}
          className="text-green-500 hover:text-green-700 transition-colors"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      )}
    </div>
  );
}
