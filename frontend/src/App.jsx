import { useEffect, useState } from "react";
import "./App.css";
import OverviewPanel from "./components/OverviewPanel";
import DigestPanel from "./components/DigestPanel";
import LeaderboardPanel from "./components/LeaderboardPanel";
import InsightsPanel from "./components/InsightsPanel";
import DataPanel from "./components/DataPanel";
import { BarChart3, BrainCircuit, ChevronDown, FileText, Gauge, Headphones, Lightbulb, Package, ShieldCheck, Sparkles, Users, ShoppingCart, UserRound, Search } from "lucide-react";

const TABS = [
  { id: "overview", label: "Dashboard", icon: Gauge },
  { id: "digest", label: "Weekly Digest", icon: BarChart3 },
  { id: "insights", label: "Complaints & Topics", icon: Lightbulb },
  { id: "leaderboard", label: "Agent Leaderboard", icon: Users },
];

const URL_TABS = new Set([
  ...TABS.map((tab) => tab.id),
  "products",
  "customers",
  "orders",
  "tickets",
  "evaluation",
]);

function readTabFromUrl() {
  const requestedTab = new URLSearchParams(window.location.search).get("view");
  return URL_TABS.has(requestedTab) ? requestedTab : "overview";
}

function App() {
  const [activeTab, setActiveTab] = useState(readTabFromUrl);
  const [showPeriodInfo, setShowPeriodInfo] = useState(false);

  useEffect(() => {
    const handleHistoryChange = () => setActiveTab(readTabFromUrl());
    window.addEventListener("popstate", handleHistoryChange);
    return () => window.removeEventListener("popstate", handleHistoryChange);
  }, []);

  const navigateTo = (tab) => {
    setActiveTab(tab);
    window.history.pushState({}, "", `?view=${tab}`);
  };

  const renderPanel = () => {
    switch (activeTab) {
      case "overview":
        return <OverviewPanel />;
      case "digest":
        return <DigestPanel />;
      case "leaderboard":
        return <LeaderboardPanel />;
      case "insights":
        return <InsightsPanel />;
      case "products":
      case "customers":
      case "orders":
      case "tickets":
      case "evaluation":
        return <DataPanel resource={activeTab} />;
      default:
        return <OverviewPanel />;
    }
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-mark"><Headphones size={19} strokeWidth={2.4} /></div>
          <div><strong>Vireo Audio</strong><span>Support Intelligence</span></div>
        </div>
        <nav className="sidebar-nav">
          <div className="sidebar-section-label">Workspace</div>
          {TABS.map((tab) => {
            const Icon = tab.icon;
            return <button key={tab.id} className={`sidebar-btn ${activeTab === tab.id ? "active" : ""}`} onClick={() => navigateTo(tab.id)}><Icon size={17} />{tab.label}</button>;
          })}
          <div className="sidebar-section-label">Data</div>
          <button className={`sidebar-btn ${activeTab === "products" ? "active" : ""}`} onClick={() => navigateTo("products")}><Package size={17} />Products</button>
          <button className={`sidebar-btn ${activeTab === "customers" ? "active" : ""}`} onClick={() => navigateTo("customers")}><UserRound size={17} />Customers</button>
          <button className={`sidebar-btn ${activeTab === "orders" ? "active" : ""}`} onClick={() => navigateTo("orders")}><ShoppingCart size={17} />Orders</button>
          <button className={`sidebar-btn ${activeTab === "tickets" ? "active" : ""}`} onClick={() => navigateTo("tickets")}><Search size={17} />Ticket Explorer</button>
          <div className="sidebar-section-label">Governance</div>
          <button className={`sidebar-btn ${activeTab === "evaluation" ? "active" : ""}`} onClick={() => navigateTo("evaluation")}><ShieldCheck size={17} />Evaluation</button>
        </nav>
        <div className="sidebar-footer"><span className="status-dot" />Data synced<br /><small>Jan 2025 - Jun 2026<br />18 months · 100% tickets</small><b>V1.0</b></div>
      </aside>
      <div className="app-content">
        <header className="topbar">
          <div><div className="eyebrow"><BrainCircuit size={14} /> VIREO SUPPORT INTELLIGENCE</div><h1>Vireo Support Intelligence</h1><p className="topbar-subtitle">AI-powered analysis of 18 months of support tickets</p></div>
          <div className="topbar-actions"><div className="period-control-wrap"><button className="date-control" onClick={() => setShowPeriodInfo((value) => !value)}><FileText size={14} /> Jan 2025 — Jun 2026 <ChevronDown size={14} /></button>{showPeriodInfo && <div className="period-popover">Showing the complete source period.<strong>18 months · 11,875 deduplicated tickets</strong></div>}</div><button className="primary-action" onClick={() => navigateTo("digest")}><Sparkles size={15} /> Generate Weekly Digest</button></div>
        </header>
        <main className="app-main">{renderPanel()}</main>
      </div>
    </div>
  );
}

export default App;
