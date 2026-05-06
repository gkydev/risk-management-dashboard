import { memo } from "react";
import type { MarketQuote } from "../types";
import { formatBps, formatCompact, formatPrice } from "../utils/format";

interface PriceBoardProps {
  prices: MarketQuote[];
}

function PriceBoardImpl({ prices }: PriceBoardProps) {
  const sortedPrices = [...prices].sort((left, right) =>
    left.market.localeCompare(right.market),
  );

  return (
    <section className="panel price-board-panel">
      <div className="panel-heading">
        <div>
          <h2>Market Prices</h2>
          <p>{prices.length} streams</p>
        </div>
      </div>
      <div className="quote-grid">
        {sortedPrices.map((quote) => {
          const spreadBps = ((quote.ask - quote.bid) / quote.mid) * 10_000;
          const topBidDepth = quote.bid_depth[0]?.quantity;
          const topAskDepth = quote.ask_depth[0]?.quantity;
          const depthRows = Array.from({ length: 3 }, (_, index) => ({
            bid: quote.bid_depth[index],
            ask: quote.ask_depth[index],
          }));

          return (
            <article className="quote-card" key={quote.market}>
              <div className="quote-header">
                <div>
                  <h3>{quote.market}</h3>
                  <p>Mid {formatPrice(quote.mid)}</p>
                </div>
                <span>{formatBps(spreadBps)}</span>
              </div>

              <div className="quote-sides">
                <div className="quote-side bid">
                  <span>Bid</span>
                  <strong>{formatPrice(quote.bid)}</strong>
                  <small>{formatCompact(topBidDepth)}</small>
                </div>
                <div className="quote-side ask">
                  <span>Ask</span>
                  <strong>{formatPrice(quote.ask)}</strong>
                  <small>{formatCompact(topAskDepth)}</small>
                </div>
              </div>

              <div className="depth-ladder" aria-label={`${quote.market} top depth`}>
                {depthRows.map((row, index) => (
                  <div className="depth-row" key={`${quote.market}-${index}`}>
                    <span className="depth-cell bid">
                      <strong>{formatCompact(row.bid?.quantity)}</strong>
                      <span>{formatPrice(row.bid?.price)}</span>
                    </span>
                    <span className="depth-level">{index + 1}</span>
                    <span className="depth-cell ask">
                      <span>{formatPrice(row.ask?.price)}</span>
                      <strong>{formatCompact(row.ask?.quantity)}</strong>
                    </span>
                  </div>
                ))}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

export const PriceBoard = memo(PriceBoardImpl);
