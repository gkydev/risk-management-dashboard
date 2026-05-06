import { useCallback, useEffect, useState } from "react";
import {
  getConfig,
  getPnlHistory,
  getRecentTrades,
  resetDashboard,
  WS_URL,
} from "../api";
import type {
  BookSummary,
  ConfigPayload,
  ConnectionState,
  LivePayload,
  MarketQuote,
  PnlPoint,
  Position,
  Trade,
} from "../types";

const MAX_TAPE_ROWS = 80;
const MAX_PNL_POINTS = 300;
const LIVE_PNL_SAMPLE_SECONDS = 1;
const RECENT_PNL_WINDOW_SECONDS = 60;
const OLDER_PNL_BUCKET_SECONDS = 10;
const RECONNECT_BASE_MS = 500;
const RECONNECT_MAX_MS = 5000;

export interface DashboardDataState {
  config?: ConfigPayload;
  prices: MarketQuote[];
  trades: Trade[];
  positions: Position[];
  summary?: BookSummary;
  pnlSeries: PnlPoint[];
  connection: ConnectionState;
  loading: boolean;
  apiError?: string;
  lastLiveAtMs?: number;
}

const initialState: DashboardDataState = {
  prices: [],
  trades: [],
  positions: [],
  pnlSeries: [],
  connection: "connecting",
  loading: true,
};

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Unexpected error";
}

function normalizePnlSeries(points: PnlPoint[]): PnlPoint[] {
  const sortedPoints = [...points].sort(
    (left, right) => left.timestamp - right.timestamp,
  );
  const latestTimestamp = sortedPoints.at(-1)?.timestamp ?? 0;
  let lastOlderBucket = -1;
  const compactedPoints: PnlPoint[] = [];

  for (const point of sortedPoints) {
    const ageSeconds = latestTimestamp - point.timestamp;
    if (ageSeconds > RECENT_PNL_WINDOW_SECONDS) {
      const bucket = Math.floor(point.timestamp / OLDER_PNL_BUCKET_SECONDS);
      if (bucket === lastOlderBucket) {
        continue;
      }
      lastOlderBucket = bucket;
    }
    compactedPoints.push(point);
  }

  return compactedPoints.slice(-MAX_PNL_POINTS);
}

function appendPnlPoint(points: PnlPoint[], point: PnlPoint): PnlPoint[] {
  const latestPoint = points.at(-1);
  if (
    latestPoint &&
    point.timestamp - latestPoint.timestamp < LIVE_PNL_SAMPLE_SECONDS
  ) {
    return points;
  }

  return normalizePnlSeries([...points, point]);
}

function mergeById<T>(
  current: T[],
  incoming: T[],
  idFor: (item: T) => string,
  timestampFor: (item: T) => number,
): T[] {
  const byId = new Map<string, T>();
  for (const item of [...incoming, ...current]) {
    byId.set(idFor(item), item);
  }
  return Array.from(byId.values())
    .sort((left, right) => timestampFor(right) - timestampFor(left))
    .slice(0, MAX_TAPE_ROWS);
}

export function useDashboardData() {
  const [state, setState] = useState<DashboardDataState>(initialState);

  const refreshInitialData = useCallback(async () => {
    setState((previous) => ({ ...previous, loading: true, apiError: undefined }));
    try {
      const [config, tradesPayload, pnlHistoryPayload] = await Promise.all([
        getConfig(),
        getRecentTrades(10).catch(() => ({ trades: [] })),
        getPnlHistory(300).catch(() => ({ points: [] })),
      ]);

      setState((previous) => ({
        ...previous,
        config,
        trades: tradesPayload.trades,
        pnlSeries: normalizePnlSeries(pnlHistoryPayload.points),
        loading: false,
        apiError: undefined,
      }));
    } catch (error) {
      setState((previous) => ({
        ...previous,
        loading: false,
        apiError: `Initial data request failed: ${errorMessage(error)}`,
      }));
    }
  }, []);

  const handleLivePayload = useCallback((payload: LivePayload) => {
    setState((previous) => {
      const nextPoint = {
        timestamp: payload.timestamp,
        total_pnl: payload.summary.total_pnl,
      };

      return {
        ...previous,
        prices: payload.prices,
        positions: payload.positions,
        summary: payload.summary,
        trades: mergeById(
          previous.trades,
          payload.recent_trades,
          (trade) => trade.trade_id,
          (trade) => trade.executed_at,
        ),
        pnlSeries: appendPnlPoint(previous.pnlSeries, nextPoint),
        connection: "connected",
        lastLiveAtMs: payload.timestamp * 1000,
      };
    });
  }, []);

  const reset = useCallback(async () => {
    setState((previous) => ({ ...previous, loading: true, apiError: undefined }));
    try {
      await resetDashboard();
      setState({
        ...initialState,
        connection: state.connection,
        loading: false,
      });
      await refreshInitialData();
    } catch (error) {
      setState((previous) => ({
        ...previous,
        loading: false,
        apiError: `Reset failed: ${errorMessage(error)}`,
      }));
    }
  }, [refreshInitialData, state.connection]);

  useEffect(() => {
    void refreshInitialData();
  }, [refreshInitialData]);

  useEffect(() => {
    let socket: WebSocket | undefined;
    let reconnectTimerId: number | undefined;
    let closedByEffect = false;
    let reconnectAttempts = 0;

    const connect = () => {
      setState((previous) => ({
        ...previous,
        connection: reconnectAttempts > 0 ? "reconnecting" : "connecting",
      }));

      socket = new WebSocket(WS_URL);

      socket.onopen = () => {
        reconnectAttempts = 0;
        setState((previous) => ({ ...previous, connection: "connected" }));
      };

      socket.onmessage = (event) => {
        try {
          handleLivePayload(JSON.parse(event.data) as LivePayload);
        } catch (error) {
          setState((previous) => ({
            ...previous,
            apiError: `Live payload parse failed: ${errorMessage(error)}`,
          }));
        }
      };

      socket.onclose = () => {
        if (closedByEffect) {
          return;
        }
        reconnectAttempts += 1;
        setState((previous) => ({ ...previous, connection: "disconnected" }));
        const delayMs = Math.min(
          RECONNECT_BASE_MS * 2 ** (reconnectAttempts - 1),
          RECONNECT_MAX_MS,
        );
        reconnectTimerId = window.setTimeout(connect, delayMs);
      };

      socket.onerror = () => {
        socket?.close();
      };
    };

    connect();

    return () => {
      closedByEffect = true;
      if (reconnectTimerId !== undefined) {
        window.clearTimeout(reconnectTimerId);
      }
      socket?.close();
    };
  }, [handleLivePayload]);

  return {
    ...state,
    refreshInitialData,
    reset,
  };
}
