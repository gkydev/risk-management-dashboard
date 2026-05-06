import { memo, useMemo } from "react";
import {
  Banknote,
  ChartNoAxesColumn,
  HandCoins,
  LineChart,
  Percent,
  Sigma,
  type LucideIcon,
} from "lucide-react";
import type { BookSummary, Position } from "../types";
import { formatBps, formatCompactCurrency, formatNumber } from "../utils/format";

interface KpiGridProps {
  summary?: BookSummary;
  positions: Position[];
}

interface KpiItem {
  label: string;
  value: string;
  tone?: "positive" | "negative" | "neutral";
  icon: LucideIcon;
}

function pnlTone(value: number | undefined): KpiItem["tone"] {
  if (value === undefined || value === 0) {
    return "neutral";
  }
  return value > 0 ? "positive" : "negative";
}

function KpiGridImpl({ summary, positions }: KpiGridProps) {
  const openPositionCount = useMemo(
    () => positions.filter((position) => position.quantity !== 0).length,
    [positions],
  );

  const items: KpiItem[] = [
    {
      label: "Total PnL",
      value: formatCompactCurrency(summary?.total_pnl),
      tone: pnlTone(summary?.total_pnl),
      icon: LineChart,
    },
    {
      label: "Gross Exposure",
      value: formatCompactCurrency(summary?.gross_exposure),
      icon: Sigma,
    },
    {
      label: "Monetization",
      value: formatCompactCurrency(summary?.monetization),
      tone: pnlTone(summary?.monetization),
      icon: HandCoins,
    },
    {
      label: "Client Yield",
      value: formatBps(summary?.client_yield_bps),
      icon: Percent,
    },
    {
      label: "Open Positions",
      value: formatNumber(openPositionCount),
      icon: ChartNoAxesColumn,
    },
    {
      label: "Trades",
      value: formatNumber(summary?.trade_count),
      icon: Banknote,
    },
  ];

  return (
    <section className="kpi-grid" aria-label="Key metrics">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <article className={`metric-card ${item.tone ?? "neutral"}`} key={item.label}>
            <div className="metric-icon">
              <Icon size={18} aria-hidden="true" />
            </div>
            <div>
              <p className="metric-label">{item.label}</p>
              <p className="metric-value">{item.value}</p>
            </div>
          </article>
        );
      })}
    </section>
  );
}

export const KpiGrid = memo(KpiGridImpl);
