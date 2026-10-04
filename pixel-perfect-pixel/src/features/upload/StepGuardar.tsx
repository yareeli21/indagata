interface StepGuardarProps {
  resumen: { etiqueta: string; valor: string }[];
}

export function StepGuardar({ resumen }: StepGuardarProps) {
  return (
    <dl className="divide-y rounded-xl border bg-card">
      {resumen.map((r) => (
        <div key={r.etiqueta} className="grid grid-cols-[12rem_1fr] gap-4 px-5 py-3 text-sm">
          <dt className="text-muted-foreground">{r.etiqueta}</dt>
          <dd className="font-medium">{r.valor || "—"}</dd>
        </div>
      ))}
    </dl>
  );
}
