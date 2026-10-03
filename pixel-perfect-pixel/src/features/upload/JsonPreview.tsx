interface JsonPreviewProps {
  datos: unknown;
}

const PATRON = /("(?:\\.|[^"\\])*")(\s*:)?|\b(-?\d+(?:\.\d+)?)\b|\b(true|false|null)\b/g;

export function JsonPreview({ datos }: JsonPreviewProps) {
  const texto = JSON.stringify(datos, null, 2);
  const partes: React.ReactNode[] = [];
  let ultimo = 0;
  let m: RegExpExecArray | null;
  let k = 0;
  while ((m = PATRON.exec(texto))) {
    if (m.index > ultimo) partes.push(texto.slice(ultimo, m.index));
    if (m[1]) {
      partes.push(
        <span key={k++} className={m[2] ? "text-code-key" : "text-code-string"}>
          {m[1]}
        </span>,
      );
      if (m[2]) partes.push(m[2]);
    } else {
      partes.push(
        <span key={k++} className="text-code-number">
          {m[0]}
        </span>,
      );
    }
    ultimo = PATRON.lastIndex;
  }
  partes.push(texto.slice(ultimo));

  return (
    <pre className="max-h-[28rem] overflow-auto rounded-xl bg-code p-5 font-mono text-sm leading-relaxed text-code-foreground">
      <code>{partes}</code>
    </pre>
  );
}
