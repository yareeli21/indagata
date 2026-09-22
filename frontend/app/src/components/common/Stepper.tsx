/**
 * Componente Stepper - Indicador visual de pasos
 * 
 * Muestra el progreso en un wizard de múltiples pasos.
 * Cada paso puede estar: completado, activo, o deshabilitado.
 */

interface StepperProps {
  steps: string[];
  currentStep: number;
  enabledSteps: number[];
}

export default function Stepper({ steps, currentStep, enabledSteps }: StepperProps) {
  const isStepCompleted = (stepIndex: number) => stepIndex < currentStep;
  const isStepActive = (stepIndex: number) => stepIndex === currentStep;
  const isStepEnabled = (stepIndex: number) => enabledSteps.includes(stepIndex);

  return (
    <div className="w-full py-6">
      <div className="flex items-center justify-between">
        {steps.map((step, index) => {
          const stepNumber = index + 1;
          const completed = isStepCompleted(index);
          const active = isStepActive(index);
          const enabled = isStepEnabled(index);

          return (
            <div key={index} className="flex items-center flex-1">
              {/* Paso */}
              <div className="flex flex-col items-center">
                {/* Círculo del número */}
                <div
                  className={`
                    w-10 h-10 rounded-full flex items-center justify-center font-semibold text-sm
                    transition-all duration-300
                    ${
                      completed
                        ? 'bg-green-500 text-white'
                        : active
                        ? 'bg-blue-500 text-white ring-4 ring-blue-200'
                        : enabled
                        ? 'bg-gray-300 text-gray-700'
                        : 'bg-gray-200 text-gray-400'
                    }
                  `}
                >
                  {completed ? (
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  ) : (
                    stepNumber
                  )}
                </div>

                {/* Label del paso */}
                <div
                  className={`
                    mt-2 text-xs font-medium text-center max-w-[100px]
                    ${active ? 'text-blue-600' : completed ? 'text-green-600' : 'text-gray-500'}
                  `}
                >
                  {step}
                </div>
              </div>

              {/* Línea conectora (excepto en el último paso) */}
              {index < steps.length - 1 && (
                <div
                  className={`
                    flex-1 h-1 mx-2 transition-all duration-300
                    ${completed ? 'bg-green-500' : 'bg-gray-300'}
                  `}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
