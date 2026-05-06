import { Activity, Wifi, WifiOff } from "lucide-react";
import type { ConnectionState } from "../types";
import { formatAge } from "../utils/format";

interface ConnectionBadgeProps {
  connection: ConnectionState;
  lastLiveAtMs?: number;
  nowMs: number;
}

export function ConnectionBadge({
  connection,
  lastLiveAtMs,
  nowMs,
}: ConnectionBadgeProps) {
  const stale = lastLiveAtMs ? nowMs - lastLiveAtMs > 2500 : false;
  const stateLabel = stale ? "stale" : connection;
  const Icon = stateLabel === "connected" ? Wifi : stateLabel === "stale" ? Activity : WifiOff;

  return (
    <div className={`connection-badge ${stateLabel}`}>
      <Icon size={16} aria-hidden="true" />
      <span>{stateLabel}</span>
      <span className="connection-age">{formatAge(lastLiveAtMs, nowMs)}</span>
    </div>
  );
}
