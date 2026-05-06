import { memo } from "react";
import type { Position } from "../types";
import {
  formatCompactCurrency,
  formatPrice,
  formatQuantity,
} from "../utils/format";

interface PositionsPanelProps {
  positions: Position[];
}

function PositionsPanelImpl({ positions }: PositionsPanelProps) {
  const openPositions = positions.filter((position) => position.quantity !== 0);
  const sortedPositions = [...openPositions].sort(
    (left, right) => Math.abs(right.market_value) - Math.abs(left.market_value),
  );

  return (
    <section className="panel positions-panel">
      <div className="panel-heading">
        <div>
          <h2>Open Positions</h2>
          <p>{openPositions.length} markets</p>
        </div>
      </div>
      <div className="position-list">
        {sortedPositions.map((position) => {
          const side = position.quantity >= 0 ? "long" : "short";

          return (
            <article className="position-row" key={position.market}>
              <div className="position-main">
                <div>
                  <div className="position-title">
                    <span>{position.market}</span>
                    <span className={`side-chip ${side}`}>
                      {side === "long" ? "Long" : "Short"}
                    </span>
                  </div>
                  <p>
                    {formatQuantity(Math.abs(position.quantity))} @{" "}
                    {formatPrice(position.mark)}
                  </p>
                </div>
                <strong className={position.pnl >= 0 ? "positive-text" : "negative-text"}>
                  {formatCompactCurrency(position.pnl)}
                </strong>
              </div>
              <div className="position-meta">
                <span>Exposure</span>
                <strong>{formatCompactCurrency(position.market_value)}</strong>
              </div>
            </article>
          );
        })}
        {openPositions.length === 0 ? <div className="empty-state compact">No open positions</div> : null}
      </div>
    </section>
  );
}

export const PositionsPanel = memo(PositionsPanelImpl);
