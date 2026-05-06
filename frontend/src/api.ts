import type {
  ConfigPayload,
  PnlHistoryPayload,
  RecentTradesPayload,
} from "./types";

function defaultApiUrl(): string {
  return import.meta.env.DEV ? "http://127.0.0.1:8000" : "";
}

function defaultWsUrl(): string {
  if (import.meta.env.DEV) {
    return "ws://127.0.0.1:8000/ws/live";
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/live`;
}

const configuredApiUrl = import.meta.env.VITE_API_BASE_URL ?? defaultApiUrl();
const configuredWsUrl = import.meta.env.VITE_WS_URL ?? defaultWsUrl();

export const API_BASE_URL = configuredApiUrl.replace(/\/$/, "");
export const WS_URL = configuredWsUrl;

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

export function getConfig(): Promise<ConfigPayload> {
  return requestJson<ConfigPayload>("/api/config");
}

export function getRecentTrades(limit = 30): Promise<RecentTradesPayload> {
  return requestJson<RecentTradesPayload>(`/api/trades/recent?limit=${limit}`);
}

export function getPnlHistory(limit = 300): Promise<PnlHistoryPayload> {
  return requestJson<PnlHistoryPayload>(`/api/pnl/history?limit=${limit}`);
}

export function resetDashboard(): Promise<{ status: string }> {
  return requestJson<{ status: string }>("/api/reset", { method: "POST" });
}
