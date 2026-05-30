"use client";
import { useState } from "react";
import Link from "next/link";
import { StatusBadge } from "./StatusBadge";
import { ConfidenceBadge } from "./ConfidenceBadge";

type Prediction = {
  id: number;
  term: string;
  breakoutScore: number;
  relevanceScore: number;
  status: string;
  forecast: { confidence: number } | null;
  contentGaps: unknown[];
  niche: { name: string } | null;
};

export function PredictionsTable({ predictions }: { predictions: Prediction[] }) {
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const filtered = statusFilter === "all"
    ? predictions
    : predictions.filter((p) => p.status === statusFilter);

  return (
    <div>
      <div className="flex gap-2 mb-4 flex-wrap">
        {["all", "emerging", "maturing", "saturating"].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1 rounded text-sm border capitalize ${
              statusFilter === s ? "bg-black text-white border-black" : "bg-white text-gray-700 border-gray-300"
            }`}
          >
            {s}
          </button>
        ))}
      </div>
      <div className="text-xs text-gray-400 mb-2">{filtered.length} pautas</div>
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b text-left text-gray-500 text-xs uppercase tracking-wide">
            <th className="py-2 pr-4 font-medium">Termo</th>
            <th className="py-2 pr-4 font-medium">Nicho</th>
            <th className="py-2 pr-4 font-medium">Score</th>
            <th className="py-2 pr-4 font-medium">Status</th>
            <th className="py-2 pr-4 font-medium">Confiança</th>
            <th className="py-2 font-medium">Gap?</th>
          </tr>
        </thead>
        <tbody>
          {filtered.length === 0 ? (
            <tr>
              <td colSpan={6} className="py-8 text-center text-gray-400 text-sm">
                Nenhuma pauta encontrada.
              </td>
            </tr>
          ) : (
            filtered.map((p) => (
              <tr key={p.id} className="border-b hover:bg-gray-50 transition-colors">
                <td className="py-2 pr-4">
                  <Link href={`/prediction/${p.id}`} className="text-blue-600 hover:underline font-medium">
                    {p.term}
                  </Link>
                </td>
                <td className="py-2 pr-4 text-gray-600 text-xs">{p.niche?.name ?? "—"}</td>
                <td className="py-2 pr-4 font-mono text-xs">{p.breakoutScore.toFixed(3)}</td>
                <td className="py-2 pr-4"><StatusBadge status={p.status} /></td>
                <td className="py-2 pr-4">
                  <ConfidenceBadge confidence={p.forecast?.confidence ?? null} />
                </td>
                <td className="py-2 text-green-600 font-bold">
                  {Array.isArray(p.contentGaps) && p.contentGaps.length > 0 ? "✓" : ""}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
