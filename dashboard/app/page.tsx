import { getPredictions, getNiches } from "@/lib/db";
import { PredictionsTable } from "@/components/PredictionsTable";

export const revalidate = 300;

type PredictionForTable = {
  id: number;
  term: string;
  breakoutScore: number;
  relevanceScore: number;
  status: string;
  forecast: { confidence: number } | null;
  contentGaps: unknown[];
  niche: { name: string } | null;
};

function toForecast(v: unknown): { confidence: number } | null {
  if (v && typeof v === "object" && !Array.isArray(v) && "confidence" in v) {
    const conf = (v as Record<string, unknown>).confidence;
    if (typeof conf === "number") return { confidence: conf };
  }
  return null;
}

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ niche?: string; status?: string }>;
}) {
  const params = await searchParams;
  const rawNicheId = params.niche ? Number(params.niche) : undefined;
  const nicheId = rawNicheId !== undefined && Number.isFinite(rawNicheId) ? rawNicheId : undefined;

  const predictions = await getPredictions({
    nicheId,
    status: params.status,
    limit: 200,
  });
  const niches = await getNiches();

  const tableData: PredictionForTable[] = predictions.map((p: {
    id: number;
    term: string;
    breakoutScore: number;
    relevanceScore: number;
    status: string;
    forecast: unknown;
    contentGaps: unknown;
    niche: { name: string } | null;
  }) => ({
    id: p.id,
    term: p.term,
    breakoutScore: p.breakoutScore,
    relevanceScore: p.relevanceScore,
    status: p.status,
    forecast: toForecast(p.forecast),
    contentGaps: Array.isArray(p.contentGaps) ? p.contentGaps : [],
    niche: p.niche,
  }));

  return (
    <main className="max-w-5xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">SEO Forecaster</h1>
        <p className="text-gray-500 text-sm mt-1">
          {predictions.length} pautas detectadas · atualização diária
        </p>
      </div>

      <div className="flex gap-2 mb-6 flex-wrap">
        <a
          href="/"
          className={`px-3 py-1 rounded text-sm border ${
            !params.niche ? "bg-black text-white border-black" : "bg-white text-gray-700 border-gray-300"
          }`}
        >
          Todos os nichos
        </a>
        {niches.map((n) => (
          <a
            key={n.id}
            href={`?niche=${n.id}`}
            className={`px-3 py-1 rounded text-sm border ${
              params.niche === String(n.id)
                ? "bg-black text-white border-black"
                : "bg-white text-gray-700 border-gray-300"
            }`}
          >
            {n.name}
          </a>
        ))}
      </div>

      <PredictionsTable predictions={tableData} />
    </main>
  );
}
