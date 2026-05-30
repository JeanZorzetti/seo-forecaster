import { notFound } from "next/navigation";
import { getPredictionById } from "@/lib/db";
import { PredictionDetail } from "@/components/PredictionDetail";

function toForecast(v: unknown): { curve: number[]; peak_day: number; confidence: number } | null {
  if (
    v && typeof v === "object" && !Array.isArray(v) &&
    "curve" in v && "peak_day" in v && "confidence" in v
  ) {
    const rec = v as Record<string, unknown>;
    if (Array.isArray(rec.curve) && typeof rec.peak_day === "number" && typeof rec.confidence === "number") {
      return {
        curve: rec.curve.map((x) => (typeof x === "number" ? x : 0)),
        peak_day: rec.peak_day,
        confidence: rec.confidence,
      };
    }
  }
  return null;
}

function toStringArray(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  return v.filter((x): x is string => typeof x === "string");
}

export default async function PredictionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const numId = Number(id);
  if (!Number.isFinite(numId)) notFound();

  const prediction = await getPredictionById(numId);
  if (!prediction) notFound();

  return (
    <PredictionDetail
      prediction={{
        id: prediction.id,
        term: prediction.term,
        status: prediction.status,
        breakoutScore: prediction.breakoutScore,
        relevanceScore: prediction.relevanceScore,
        forecast: toForecast(prediction.forecast),
        intents: toStringArray(prediction.intents),
        contentGaps: toStringArray(prediction.contentGaps),
        niche: prediction.niche,
        runDate: prediction.runDate,
      }}
    />
  );
}
