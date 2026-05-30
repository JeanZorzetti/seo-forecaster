export function ConfidenceBadge({ confidence }: { confidence: number | null }) {
  if (confidence === null) {
    return <span className="text-xs text-gray-400">previsão pendente</span>;
  }
  if (confidence < 0.4) {
    return <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">preliminar</span>;
  }
  return <span className="text-xs text-gray-500">{Math.round(confidence * 100)}%</span>;
}
