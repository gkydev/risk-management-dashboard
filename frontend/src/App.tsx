import { useEffect, useState } from "react";
import { RotateCcw } from "lucide-react";
import { ConnectionBadge } from "./components/ConnectionBadge";
import { KpiGrid } from "./components/KpiGrid";
import { PnlChart } from "./components/PnlChart";
import { PositionsPanel } from "./components/PositionsPanel";
import { PriceBoard } from "./components/PriceBoard";
import { RecentActivity } from "./components/RecentActivity";
import { useDashboardData } from "./hooks/useDashboardData";

function App() {
  const dashboard = useDashboardData();
  const [nowMs, setNowMs] = useState(Date.now());

  useEffect(() => {
    const intervalId = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(intervalId);
  }, []);

  const marketCount = dashboard.config?.markets.length ?? dashboard.prices.length;
  const clientCount = dashboard.config?.clients.length ?? 0;

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Finalto Book Risk</p>
          <h1>Risk Management Dashboard</h1>
          <div className="meta-line">
            <span>{marketCount} markets</span>
            <span>{clientCount} clients</span>
          </div>
        </div>
        <div className="topbar-actions">
          <ConnectionBadge
            connection={dashboard.connection}
            lastLiveAtMs={dashboard.lastLiveAtMs}
            nowMs={nowMs}
          />
          <button
            className="icon-button danger"
            disabled={dashboard.loading}
            onClick={() => void dashboard.reset()}
            type="button"
          >
            <RotateCcw size={16} aria-hidden="true" />
            <span>Reset</span>
          </button>
        </div>
      </header>

      {dashboard.apiError ? <div className="error-banner">{dashboard.apiError}</div> : null}

      <KpiGrid summary={dashboard.summary} positions={dashboard.positions} />

      <div className="dashboard-grid">
        <div className="market-column">
          <PriceBoard prices={dashboard.prices} />
        </div>
        <div className="center-column">
          <PnlChart points={dashboard.pnlSeries} />
          <PositionsPanel positions={dashboard.positions} />
        </div>
        <RecentActivity trades={dashboard.trades} />
      </div>
    </main>
  );
}

export default App;
