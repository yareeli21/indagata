const PUNTOS: ReadonlyArray<readonly [number, number]> = [
  [18, 30],
  [32, 18],
  [46, 34],
  [60, 22],
  [74, 40],
  [86, 26],
  [24, 52],
  [40, 60],
  [56, 50],
  [70, 62],
  [84, 54],
  [64, 76],
];

/** Constelación de puntos que evoca el espacio de embeddings (gateway Espacio). */
export function VisualConstelacion() {
  return (
    <svg
      viewBox="0 0 100 100"
      preserveAspectRatio="xMaxYMin meet"
      className="absolute right-0 top-0 h-2/3 w-2/3"
    >
      {PUNTOS.slice(1).map(([x, y], i) => {
        const [px, py] = PUNTOS[i] ?? [x, y];
        return (
          <line
            key={i}
            x1={px}
            y1={py}
            x2={x}
            y2={y}
            className="stroke-primary/20"
            strokeWidth={0.5}
          />
        );
      })}
      {PUNTOS.map(([x, y], i) => (
        <circle
          key={i}
          cx={x}
          cy={y}
          r={i % 3 === 0 ? 2.4 : 1.5}
          className={i % 4 === 0 ? "fill-accent" : "fill-primary/45"}
        />
      ))}
    </svg>
  );
}
