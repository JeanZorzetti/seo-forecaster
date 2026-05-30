import Link from "next/link";
import { ForecastChart } from "./ForecastChart";
import { StatusBadge } from "./StatusBadge";

type Forecast = {
  curve: number[];
  peak_day: number;
  confidence: number;
};

type Props = {
  prediction: {
    id: number;
    term: string;
    status: string;
    breakoutScore: number;
    relevanceScore: number;
    forecast: Forecast | null;
    intents: string[];
    contentGaps: string[];
    niche: { name: string } | null;
    runDate: Date;
  };
};

export function PredictionDetail({ prediction: p }: Props) {
  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <div className="flex items-center gap-2 text-sm text-gray-400">
        <Link href="/" className="hover:text-gray-700 transition-colors">← Voltar</Link>
      </div>

      <div>
        <h1 className="text-2xl font-bold tracking-tight">{p.term}</h1>
        <div className="flex items-center gap-3 mt-2 flex-wrap">
          <StatusBadge status={p.status} />
          {p.niche?.name && (
            <span className="text-sm text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
              {p.niche.name}
            </span>
          )}
          <span className="text-xs text-gray-400">
            Score: <span className="font-mono">{p.breakoutScore.toFixed(3)}</span>
          </span>
          <span className="text-xs text-gray-400">
            Relevância: <span className="font-mono">{p.relevanceScore.toFixed(3)}</span>
          </span>
        </div>
      </div>

      {p.forecast ? (
        <div className="border rounded-lg p-4 bg-white">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Previsão de Volume (Chronos)</h2>
          <ForecastChart
            curve={p.forecast.curve}
            peakDay={p.forecast.peak_day}
            confidence={p.forecast.confidence}
          />
        </div>
      ) : (
        <div className="border rounded-lg p-4 bg-gray-50">
          <p className="text-sm text-gray-500">
            Previsão Chronos pendente — aguardando histórico suficiente (mínimo 3 dias).
          </p>
        </div>
      )}

      {p.intents.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gray-700 mb-3">
            Próximas buscas long-tail
          </h2>
          <ol className="list-decimal pl-5 space-y-1.5">
            {p.intents.map((intent, i) => (
              <li key={i} className="text-sm text-gray-700">{intent}</li>
            ))}
          </ol>
        </div>
      )}

      {p.contentGaps.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Content gaps</h2>
          <ul className="space-y-1.5">
            {p.contentGaps.map((gap, i) => (
              <li key={i} className="text-sm text-gray-700 flex gap-2">
                <span className="text-green-500 font-bold mt-0.5">✓</span>
                <span>{gap}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="text-xs text-gray-400 border-t pt-4">
        Detectado em: {new Date(p.runDate).toLocaleDateString("pt-BR")}
      </div>
    </div>
  );
}
