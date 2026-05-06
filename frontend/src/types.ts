export type ConnectionState =
  | "connecting"
  | "connected"
  | "reconnecting"
  | "disconnected";

export type Side = "buy" | "sell";

export interface PriceLevel {
  price: number;
  quantity: number;
}

export interface MarketQuote {
  market: string;
  bid: number;
  ask: number;
  mid: number;
  bid_depth: PriceLevel[];
  ask_depth: PriceLevel[];
  timestamp: number;
}

export interface Trade {
  trade_id: string;
  client_id: string;
  market: string;
  side: Side;
  quantity: number;
  price: number;
  liquidity_side: "bid" | "ask";
  book_quantity_delta: number;
  cash_delta: number;
  executed_at: number;
}

export interface Position {
  market: string;
  quantity: number;
  cash: number;
  mark: number;
  market_value: number;
  pnl: number;
}

export interface BookSummary {
  total_pnl: number;
  gross_exposure: number;
  monetization: number;
  client_yield_bps: number;
  trade_count: number;
}

export interface ConfigPayload {
  timestamp: number;
  markets: Array<{
    market: string;
    base_price: number;
    spread_bps: number;
    volatility_bps: number;
    depth_levels: number;
  }>;
  clients: Array<{
    client_id: string;
    display_name: string;
    trade_chance_per_tick: number;
    max_quantity: number;
  }>;
  cadence: Record<string, number>;
}

export interface RecentTradesPayload {
  timestamp: number;
  limit: number;
  trades: Trade[];
}

export interface PnlHistoryPayload {
  timestamp: number;
  limit: number;
  points: PnlPoint[];
}

export interface LivePayload {
  timestamp: number;
  prices: MarketQuote[];
  recent_trades: Trade[];
  positions: Position[];
  summary: BookSummary;
}

export interface PnlPoint {
  timestamp: number;
  total_pnl: number;
}
