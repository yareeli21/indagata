import { Stepper as StepperCompartido } from "@/components/shared/Stepper";

interface Paso {
  numero: number;
  etiqueta: string;
}

interface StepperProps {
  pasos: Paso[];
  actual: number; // 1-indexed
}

/** Adapta los pasos numerados (1-indexed) al Stepper compartido. */
export function Stepper({ pasos, actual }: StepperProps) {
  return <StepperCompartido pasos={pasos.map((p) => p.etiqueta)} actual={actual - 1} />;
}
