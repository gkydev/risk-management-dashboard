import { memo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { PnlPoint } from "../types";
import { formatCompactCurrency, formatCurrency, formatTime } from "../utils/format";

interface PnlChartProps {
  points: PnlPoint[];
}

function PnlChartImpl({ points }: PnlChartProps) {
  const latestPnl = points.at(-1)?.total_pnl ?? 0;
  const lineColor = latestPnl >= 0 ? "#3ddc97" : "#ff5c70";
  const hasPoints = points.length > 1;

  return (
    <section className="panel pnl-panel">
      <div className="panel-heading">
        <div>
          <h2>PnL Curve</h2>
          <p>{points.length} live points</p>
        </div>
      </div>
      <div className="chart-box">
        {hasPoints ? (
          <ResponsiveContainer
            debounce={100}
            height="100%"
            minHeight={1}
            minWidth={1}
            width="100%"
          >
            <LineChart data={points} margin={{ top: 12, right: 16, bottom: 4, left: 8 }}>
              <CartesianGrid stroke="#2f343a" strokeDasharray="3 3" />
              <XAxis
                dataKey="timestamp"
                domain={["dataMin", "dataMax"]}
                tickFormatter={formatTime}
                type="number"
                stroke="#8e98a8"
                tick={{ fontSize: 12 }}
              />
              <YAxis
                stroke="#8e98a8"
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => formatCompactCurrency(Number(value))}
                width={72}
              />
              <Tooltip
                labelFormatter={(value) => formatTime(Number(value))}
                formatter={(value) => [formatCurrency(Number(value)), "PnL"]}
                contentStyle={{
                  background: "#11161d",
                  border: "1px solid #303741",
                  borderRadius: 8,
                  boxShadow: "0 12px 30px rgba(0, 0, 0, 0.35)",
                }}
                cursor={{ stroke: "#64748b", strokeDasharray: "4 4", strokeWidth: 1 }}
                itemStyle={{ color: "#dbe3ee", fontWeight: 650 }}
                labelStyle={{ color: "#f8fafc", fontWeight: 760, marginBottom: 4 }}
              />
              <Line
                dataKey="total_pnl"
                dot={false}
                isAnimationActive={false}
                stroke={lineColor}
                strokeWidth={2}
                type="monotone"
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="empty-state">Waiting for live PnL</div>
        )}
      </div>
    </section>
  );
}

export const PnlChart = memo(PnlChartImpl);
