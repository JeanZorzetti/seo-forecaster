import { getPredictions, getNiches } from "@/lib/db";
import { PredictionsTable } from "@/components/PredictionsTable";

export const revalidate = 300;

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ niche?: string; status?: string }>;
}) {
  const params = await searchParams;
  const predictions = await getPredictions({
    nicheId: params.niche ? parseInt(params.niche) : undefined,
    status: params.status,
    limit: 200,
  });
  const niches = await getNiches();

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

      <PredictionsTable predictions={predictions as Parameters<typeof PredictionsTable>[0]["predictions"]} />
    </main>
  );
}
