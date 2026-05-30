"use client";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

type ForecastChartProps = {
  curve: number[];
  peakDay: number;
  confidence: number;
};

export function ForecastChart({ curve, peakDay, confidence }: ForecastChartProps) {
  const data = curve.map((v, i) => ({ day: i + 1, value: Math.round(v) }));

  return (
    <div>
      <div className="text-xs text-gray-500 mb-2">
        Previsão 90 dias · Confiança:{" "}
        <span className={confidence < 0.4 ? "text-amber-600 font-medium" : "text-gray-700"}>
          {Math.round(confidence * 100)}%
        </span>
        {confidence < 0.4 && " · ⚠ histórico curto — previsão preliminar"}
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 5, right: 20, bottom: 20, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="day"
            label={{ value: "dias", position: "insideBottom", offset: -10, style: { fontSize: 11 } }}
            tick={{ fontSize: 11 }}
          />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip
            formatter={(value) => [value ?? 0, "volume previsto"]}
            labelFormatter={(label) => `Dia ${label}`}
          />
          <ReferenceLine
            x={peakDay + 1}
            stroke="#ef4444"
            strokeDasharray="4 2"
            label={{ value: "pico", position: "top", style: { fontSize: 10, fill: "#ef4444" } }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#2563eb"
            dot={false}
            strokeWidth={2}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
