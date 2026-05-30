import { notFound } from "next/navigation";
import { getPredictionById } from "@/lib/db";
import { PredictionDetail } from "@/components/PredictionDetail";

export default async function PredictionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const prediction = await getPredictionById(parseInt(id));
  if (!prediction) notFound();

  const forecast = prediction.forecast as {
    curve: number[];
    peak_day: number;
    confidence: number;
  } | null;

  const intents = Array.isArray(prediction.intents)
    ? (prediction.intents as string[])
    : [];

  const contentGaps = Array.isArray(prediction.contentGaps)
    ? (prediction.contentGaps as string[])
    : [];

  return (
    <PredictionDetail
      prediction={{
        id: prediction.id,
        term: prediction.term,
        status: prediction.status,
        breakoutScore: prediction.breakoutScore,
        relevanceScore: prediction.relevanceScore,
        forecast,
        intents,
        contentGaps,
        niche: prediction.niche,
        runDate: prediction.runDate,
      }}
    />
  );
}
