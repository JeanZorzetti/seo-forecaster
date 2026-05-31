// Indicates how the breakout score was computed:
//  - "volume": cold-start bootstrap (ranked by raw daily volume, < 3 days history)
//  - "tendência": real acceleration detected (2nd-derivative, >= 3 days history)
// We infer the mode from the forecast: a usable Chronos forecast requires >= 3
// days of history, which is exactly when acceleration scoring kicks in.
export function ModeBadge({ forecast }: { forecast: { confidence: number } | null }) {
  const isAcceleration = forecast != null && forecast.confidence >= 0.4;

  if (isAcceleration) {
    return (
      <span
        title="Score por aceleração real (2ª derivada, histórico ≥ 3 dias)"
        className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800"
      >
        ↗ tendência
      </span>
    );
  }
  return (
    <span
      title="Score por volume bruto do dia (bootstrap — aguardando ≥ 3 dias de histórico para medir aceleração)"
      className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600"
    >
      volume
    </span>
  );
}
