import { memo } from "react";
import type { Trade } from "../types";
import { formatPrice, formatQuantity, formatTime } from "../utils/format";

interface RecentActivityProps {
  trades: Trade[];
}

const TradeRow = memo(function TradeRow({ trade }: { trade: Trade }) {
  return (
    <article className="activity-row" key={trade.trade_id}>
      <div>
        <div className="activity-title">
          <span>{trade.market}</span>
          <span className={`side-chip ${trade.side}`}>{trade.side}</span>
        </div>
        <p>
          {trade.client_id} - {formatQuantity(trade.quantity)} at {formatPrice(trade.price)}
        </p>
      </div>
      <time>{formatTime(trade.executed_at)}</time>
    </article>
  );
});

function RecentActivityImpl({ trades }: RecentActivityProps) {
  const latestTrades = trades.slice(0, 10);

  return (
    <aside className="activity-column">
      <section className="panel activity-panel">
        <div className="panel-heading">
          <div>
            <h2>Latest Trades</h2>
            <p>{latestTrades.length} latest</p>
          </div>
        </div>
        <div className="activity-list">
          {latestTrades.length > 0 ? (
            latestTrades.map((trade) => (
              <TradeRow key={trade.trade_id} trade={trade} />
            ))
          ) : (
            <div className="empty-state compact">No trades</div>
          )}
        </div>
      </section>
    </aside>
  );
}

export const RecentActivity = memo(RecentActivityImpl);
