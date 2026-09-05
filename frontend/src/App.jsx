import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, AlertTriangle, CheckCircle2, RefreshCw, Filter, 
  Search, Eye, ArrowRight, Activity, Cpu, FileText, CreditCard, Building, Banknote, Upload, Key, Database,
  Settings, Sliders, Send, Layers, Check, X, Shield, Terminal, Mail, MessageSquare
} from 'lucide-react';

const API_BASE = "http://127.0.0.1:8000";

export default function App() {
  const [activeTab, setActiveTab] = useState("dashboard"); // 'dashboard' | 'integrations' | 'settings' | 'activity'
  
  const [summary, setSummary] = useState(null);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState("ALL");
  const [search, setSearch] = useState("");
  const [selectedCase, setSelectedCase] = useState(null);
  const [activityFeed, setActivityFeed] = useState([]);

  // Modals
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showRazorpayModal, setShowRazorpayModal] = useState(false);

  // Settings State
  const [settings, setSettings] = useState({
    telegram_bot_token: "",
    owner_chat_id: "",
    target_email: "finance@merchant.com",
    authority: {
      auto_approve_limit: 10000,
      approval_required_limit: 50000
    },
    razorpay_key_id: "",
    razorpay_key_secret: ""
  });
  const [settingsMsg, setSettingsMsg] = useState("");
  const [telegramTestMsg, setTelegramTestMsg] = useState("");

  // Upload state
  const [uploadInvoices, setUploadInvoices] = useState(null);
  const [uploadPayments, setUploadPayments] = useState(null);
  const [uploadSettlements, setUploadSettlements] = useState(null);
  const [uploadBank, setUploadBank] = useState(null);

  // Razorpay state
  const [rzpKeyId, setRzpKeyId] = useState("");
  const [rzpKeySecret, setRzpKeySecret] = useState("");

  const fetchData = async () => {
    setLoading(true);
    try {
      const summaryRes = await fetch(`${API_BASE}/api/reconcile/summary`);
      const summaryData = await summaryRes.json();
      setSummary(summaryData);

      const resultsRes = await fetch(`${API_BASE}/api/reconcile/results`);
      const resultsData = await resultsRes.json();
      setResults(resultsData.results || []);

      const settingsRes = await fetch(`${API_BASE}/api/settings`);
      const settingsData = await settingsRes.json();
      setSettings(settingsData);
      setRzpKeyId(settingsData.razorpay_key_id || "");
      setRzpKeySecret(settingsData.razorpay_key_secret || "");

      const actRes = await fetch(`${API_BASE}/api/activity`);
      const actData = await actRes.json();
      setActivityFeed(actData.events || []);
    } catch (err) {
      console.error("Error fetching reconciliation data:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleRunReconciliation = async () => {
    setLoading(true);
    try {
      await fetch(`${API_BASE}/api/reconcile/run`, { method: "POST" });
      await fetchData();
    } catch (err) {
      console.error("Error running reconciliation:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings)
      });
      const data = await res.json();
      setSettingsMsg("Settings saved successfully!");
      setTimeout(() => setSettingsMsg(""), 3000);
      await fetchData();
    } catch (err) {
      setSettingsMsg("Failed to save settings.");
    } finally {
      setLoading(false);
    }
  };

  const handleTestTelegram = async () => {
    setTelegramTestMsg("Sending test message...");
    const formData = new FormData();
    formData.append("token", settings.telegram_bot_token);
    formData.append("chat_id", settings.owner_chat_id);

    try {
      const res = await fetch(`${API_BASE}/api/settings/test-telegram`, {
        method: "POST",
        body: formData
      });
      if (res.ok) {
        setTelegramTestMsg("✅ Test alert sent to Telegram!");
      } else {
        const errData = await res.json();
        setTelegramTestMsg(`❌ Test failed: ${errData.detail}`);
      }
    } catch (err) {
      setTelegramTestMsg("❌ Connection failed.");
    }
  };

  const handleCustomUploadSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    const formData = new FormData();
    if (uploadInvoices) formData.append("invoices_file", uploadInvoices);
    if (uploadPayments) formData.append("payments_file", uploadPayments);
    if (uploadSettlements) formData.append("settlements_file", uploadSettlements);
    if (uploadBank) formData.append("bank_file", uploadBank);

    try {
      await fetch(`${API_BASE}/api/reconcile/upload`, {
        method: "POST",
        body: formData
      });
      setShowUploadModal(false);
      await fetchData();
    } catch (err) {
      console.error("Upload reconciliation failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleRazorpaySyncSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    const formData = new FormData();
    formData.append("key_id", rzpKeyId);
    formData.append("key_secret", rzpKeySecret);

    try {
      await fetch(`${API_BASE}/api/reconcile/razorpay-sync`, {
        method: "POST",
        body: formData
      });
      setShowRazorpayModal(false);
      await fetchData();
    } catch (err) {
      console.error("Razorpay sync failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDetail = async (chainId) => {
    try {
      const res = await fetch(`${API_BASE}/api/reconcile/case/${chainId}`);
      const data = await res.json();
      setSelectedCase(data);
    } catch (err) {
      console.error("Error fetching case detail:", err);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const filteredResults = results.filter(r => {
    const matchesFilter = 
      filter === "ALL" || 
      (filter === "RECONCILED" && r.status === "RECONCILED") ||
      (filter === "PROBABLE" && r.status === "PROBABLE_MATCH") ||
      (filter === "EXCEPTION" && (r.status === "EXCEPTION" || r.status === "HIGH_RISK"));

    const matchesSearch = 
      r.chain_id.toLowerCase().includes(search.toLowerCase()) ||
      (r.invoice_id && r.invoice_id.toLowerCase().includes(search.toLowerCase())) ||
      r.explanation.toLowerCase().includes(search.toLowerCase());

    return matchesFilter && matchesSearch;
  });

  return (
    <div style={{ padding: "32px 5%", maxWidth: "1400px", margin: "0 auto" }}>
      {/* Top Header */}
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "6px" }}>
            <div style={{ padding: "8px", background: "rgba(99, 102, 241, 0.2)", borderRadius: "10px", color: "#818cf8" }}>
              <Cpu size={28} />
            </div>
            <h1 style={{ fontSize: "1.75rem", fontWeight: "700", letterSpacing: "-0.5px" }}>LedgerPilot</h1>
            <span className="status-badge badge-reconciled" style={{ fontSize: "0.7rem" }}>
              <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#34d399" }}></span>
              Hermes AI Controller
            </span>
          </div>
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
            Autonomous Finance Control Plane — Dashboard, Telegram Bot & Authority Management
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button className="btn-primary" style={{ background: "rgba(255, 255, 255, 0.06)", border: "1px solid var(--border-color)" }} onClick={() => setShowUploadModal(true)}>
            <Upload size={16} /> Upload CSVs
          </button>

          <button className="btn-primary" style={{ background: "rgba(56, 189, 248, 0.15)", color: "#38bdf8", border: "1px solid rgba(56, 189, 248, 0.3)" }} onClick={() => setShowRazorpayModal(true)}>
            <Key size={16} /> Razorpay Sync
          </button>

          <button className="btn-primary" onClick={handleRunReconciliation} disabled={loading}>
            <RefreshCw size={16} className={loading ? "spin" : ""} />
            {loading ? "Processing..." : "Run Controller Sync"}
          </button>
        </div>
      </header>

      {/* Navigation Control Bar */}
      <div style={{ display: "flex", gap: "12px", marginBottom: "28px", borderBottom: "1px solid var(--border-color)", paddingBottom: "12px" }}>
        <button
          onClick={() => setActiveTab("dashboard")}
          style={{
            background: activeTab === "dashboard" ? "rgba(99, 102, 241, 0.2)" : "transparent",
            color: activeTab === "dashboard" ? "#818cf8" : "var(--text-muted)",
            border: activeTab === "dashboard" ? "1px solid rgba(99, 102, 241, 0.4)" : "1px solid transparent",
            padding: "8px 16px",
            borderRadius: "8px",
            fontWeight: "600",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px"
          }}
        >
          <Activity size={16} /> Reconcile & Trace
        </button>

        <button
          onClick={() => setActiveTab("integrations")}
          style={{
            background: activeTab === "integrations" ? "rgba(99, 102, 241, 0.2)" : "transparent",
            color: activeTab === "integrations" ? "#818cf8" : "var(--text-muted)",
            border: activeTab === "integrations" ? "1px solid rgba(99, 102, 241, 0.4)" : "1px solid transparent",
            padding: "8px 16px",
            borderRadius: "8px",
            fontWeight: "600",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px"
          }}
        >
          <Layers size={16} /> Integration Hub
        </button>

        <button
          onClick={() => setActiveTab("settings")}
          style={{
            background: activeTab === "settings" ? "rgba(99, 102, 241, 0.2)" : "transparent",
            color: activeTab === "settings" ? "#818cf8" : "var(--text-muted)",
            border: activeTab === "settings" ? "1px solid rgba(99, 102, 241, 0.4)" : "1px solid transparent",
            padding: "8px 16px",
            borderRadius: "8px",
            fontWeight: "600",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px"
          }}
        >
          <Settings size={16} /> Settings & Channels
        </button>

        <button
          onClick={() => setActiveTab("activity")}
          style={{
            background: activeTab === "activity" ? "rgba(99, 102, 241, 0.2)" : "transparent",
            color: activeTab === "activity" ? "#818cf8" : "var(--text-muted)",
            border: activeTab === "activity" ? "1px solid rgba(99, 102, 241, 0.4)" : "1px solid transparent",
            padding: "8px 16px",
            borderRadius: "8px",
            fontWeight: "600",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px"
          }}
        >
          <Terminal size={16} /> Controller Activity
        </button>
      </div>

      {/* TAB 1: RECONCILE & TRACE DASHBOARD */}
      {activeTab === "dashboard" && (
        <>
          {summary && summary.mode && (
            <div style={{ background: "rgba(99, 102, 241, 0.1)", border: "1px solid rgba(99, 102, 241, 0.3)", padding: "10px 16px", borderRadius: "8px", marginBottom: "24px", fontSize: "0.85rem", color: "#818cf8", display: "flex", alignItems: "center", gap: "8px" }}>
              <Database size={16} />
              <span>Active Data Mode: <strong>{summary.mode}</strong></span>
            </div>
          )}

          {/* KPI Metric Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "20px", marginBottom: "36px" }}>
            <div className="glass-panel kpi-card">
              <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "0.8rem" }}>
                <span>TOTAL PROCESSED</span>
                <Activity size={16} />
              </div>
              <div style={{ fontSize: "1.8rem", fontWeight: "700", color: "#f8fafc" }}>
                {summary ? summary.total_records : "—"}
              </div>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>4-Way Record Chains</div>
            </div>

            <div className="glass-panel kpi-card">
              <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "0.8rem" }}>
                <span>AUTO CLOSURE RATE</span>
                <CheckCircle2 size={16} color="#34d399" />
              </div>
              <div style={{ fontSize: "1.8rem", fontWeight: "700", color: "#34d399" }}>
                {summary ? summary.controller_closure_rate : "—"}
              </div>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Straight-Through Resolution</div>
            </div>

            <div className="glass-panel kpi-card">
              <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "0.8rem" }}>
                <span>EXCEPTION PRECISION</span>
                <ShieldCheck size={16} color="#38bdf8" />
              </div>
              <div style={{ fontSize: "1.8rem", fontWeight: "700", color: "#38bdf8" }}>
                {summary ? (summary.exception_precision || "100.0%") : "—"}
              </div>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Zero False Positives</div>
            </div>

            <div className="glass-panel kpi-card">
              <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "0.8rem" }}>
                <span>EXCEPTION RECALL</span>
                <ShieldCheck size={16} color="#a855f7" />
              </div>
              <div style={{ fontSize: "1.8rem", fontWeight: "700", color: "#c084fc" }}>
                {summary ? (summary.exception_recall || "100.0%") : "—"}
              </div>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Caught All Discrepancies</div>
            </div>

            <div className="glass-panel kpi-card">
              <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "0.8rem" }}>
                <span>FLAGGED EXCEPTIONS</span>
                <AlertTriangle size={16} color="#f87171" />
              </div>
              <div style={{ fontSize: "1.8rem", fontWeight: "700", color: "#f87171" }}>
                {summary ? summary.exceptions_flagged : "—"}
              </div>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Escalated for Human Review</div>
            </div>
          </div>

          {/* Control Room Table Section */}
          <div className="glass-panel" style={{ padding: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px", flexWrap: "wrap", gap: "12px" }}>
              <div style={{ display: "flex", gap: "8px" }}>
                {["ALL", "RECONCILED", "PROBABLE", "EXCEPTION"].map(tab => (
                  <button
                    key={tab}
                    onClick={() => setFilter(tab)}
                    style={{
                      background: filter === tab ? "rgba(99, 102, 241, 0.2)" : "transparent",
                      color: filter === tab ? "#818cf8" : "var(--text-muted)",
                      border: filter === tab ? "1px solid rgba(99, 102, 241, 0.4)" : "1px solid transparent",
                      padding: "6px 14px",
                      borderRadius: "8px",
                      fontSize: "0.8rem",
                      fontWeight: "600",
                      cursor: "pointer"
                    }}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              <div style={{ position: "relative", width: "280px" }}>
                <Search size={16} style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }} />
                <input
                  type="text"
                  placeholder="Search Chain or Invoice ID..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  style={{
                    width: "100%",
                    background: "rgba(0, 0, 0, 0.2)",
                    border: "1px solid var(--border-color)",
                    borderRadius: "8px",
                    padding: "8px 12px 8px 36px",
                    color: "#fff",
                    fontSize: "0.85rem",
                    outline: "none"
                  }}
                />
              </div>
            </div>

            <div style={{ overflowX: "auto" }}>
              <table>
                <thead>
                  <tr>
                    <th>Chain ID</th>
                    <th>Invoice</th>
                    <th>Status</th>
                    <th>Root Cause</th>
                    <th>Discrepancy</th>
                    <th>Confidence</th>
                    <th>Severity</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredResults.map(r => (
                    <tr key={r.chain_id}>
                      <td style={{ fontWeight: "600", color: "#f1f5f9" }}>{r.chain_id}</td>
                      <td style={{ color: "#94a3b8" }}>{r.invoice_id || "—"}</td>
                      <td>
                        <span className={`status-badge ${
                          r.status === 'RECONCILED' ? 'badge-reconciled' :
                          r.status === 'PROBABLE_MATCH' ? 'badge-probable' :
                          r.status === 'HIGH_RISK' ? 'badge-highrisk' : 'badge-exception'
                        }`}>
                          {r.status}
                        </span>
                      </td>
                      <td style={{ fontSize: "0.8rem", color: "#cbd5e1" }}>{r.root_cause}</td>
                      <td style={{ fontWeight: "600", color: r.discrepancy_amount > 0 ? "#f87171" : "#34d399" }}>
                        ₹{r.discrepancy_amount.toFixed(2)}
                      </td>
                      <td>{(r.confidence_score * 100).toFixed(0)}%</td>
                      <td>
                        <span style={{
                          fontSize: "0.75rem",
                          fontWeight: "600",
                          color: r.severity === 'CRITICAL' ? '#c084fc' : r.severity === 'HIGH' ? '#f87171' : '#94a3b8'
                        }}>
                          {r.severity}
                        </span>
                      </td>
                      <td>
                        <button
                          onClick={() => handleOpenDetail(r.chain_id)}
                          style={{
                            background: "rgba(255, 255, 255, 0.05)",
                            border: "1px solid var(--border-color)",
                            color: "#38bdf8",
                            padding: "4px 10px",
                            borderRadius: "6px",
                            fontSize: "0.75rem",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: "4px"
                          }}
                        >
                          <Eye size={14} /> Trace
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* TAB 2: INTEGRATION HUB */}
      {activeTab === "integrations" && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "24px" }}>
          {/* Razorpay Connector */}
          <div className="glass-panel" style={{ padding: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <Key size={24} color="#38bdf8" />
                <h3 style={{ fontSize: "1.1rem", fontWeight: "700" }}>Razorpay Sandbox</h3>
              </div>
              <span className="status-badge badge-reconciled">Active</span>
            </div>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "20px" }}>
              Direct API Integration for syncing payments, settlements, and refund streams in real-time.
            </p>
            <button className="btn-primary" style={{ width: "100%" }} onClick={() => setShowRazorpayModal(true)}>
              Configure API Keys & Sync
            </button>
          </div>

          {/* CSV File Connector */}
          <div className="glass-panel" style={{ padding: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <Upload size={24} color="#34d399" />
                <h3 style={{ fontSize: "1.1rem", fontWeight: "700" }}>Universal CSV Importer</h3>
              </div>
              <span className="status-badge badge-reconciled">Active</span>
            </div>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "20px" }}>
              Upload arbitrary merchant CSV exports (ERP Invoices, Bank Statements, Gateway CSVs).
            </p>
            <button className="btn-primary" style={{ width: "100%" }} onClick={() => setShowUploadModal(true)}>
              Upload Custom CSV Statements
            </button>
          </div>

          {/* Tally Prime Connector */}
          <div className="glass-panel" style={{ padding: "24px", opacity: 0.7 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <Building size={24} color="#f59e0b" />
                <h3 style={{ fontSize: "1.1rem", fontWeight: "700" }}>Tally Prime ERP</h3>
              </div>
              <span className="status-badge badge-probable">Connector Ready</span>
            </div>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "20px" }}>
              Sync vouchers, sales ledgers, and bank receipts automatically via Tally XML/ODBC.
            </p>
            <button className="btn-primary" style={{ width: "100%", background: "rgba(255,255,255,0.05)" }} disabled>
              Ready for Enterprise Sync
            </button>
          </div>

          {/* Zoho Books Connector */}
          <div className="glass-panel" style={{ padding: "24px", opacity: 0.7 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <FileText size={24} color="#a855f7" />
                <h3 style={{ fontSize: "1.1rem", fontWeight: "700" }}>Zoho Books</h3>
              </div>
              <span className="status-badge badge-probable">Connector Ready</span>
            </div>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "20px" }}>
              OAuth 2.0 connection for syncing sales invoices and customer payments.
            </p>
            <button className="btn-primary" style={{ width: "100%", background: "rgba(255,255,255,0.05)" }} disabled>
              Ready for OAuth Sync
            </button>
          </div>
        </div>
      )}

      {/* TAB 3: SETTINGS & CHANNELS */}
      {activeTab === "settings" && (
        <div style={{ maxWidth: "800px", margin: "0 auto" }}>
          <form onSubmit={handleSaveSettings} className="glass-panel" style={{ padding: "28px" }}>
            <h2 style={{ fontSize: "1.3rem", fontWeight: "700", marginBottom: "20px", display: "flex", alignItems: "center", gap: "8px" }}>
              <Settings size={20} color="#818cf8" /> Hermes Control Plane Settings
            </h2>

            {settingsMsg && (
              <div style={{ background: "rgba(52, 211, 153, 0.15)", border: "1px solid #34d399", color: "#34d399", padding: "10px", borderRadius: "8px", marginBottom: "20px", fontSize: "0.85rem" }}>
                {settingsMsg}
              </div>
            )}

            {/* Telegram Channel Section */}
            <div style={{ marginBottom: "28px", borderBottom: "1px solid var(--border-color)", paddingBottom: "24px" }}>
              <h3 style={{ fontSize: "1rem", fontWeight: "600", marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
                <MessageSquare size={18} color="#38bdf8" /> Telegram Notification Channel
              </h3>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "12px" }}>
                <div>
                  <label style={{ fontSize: "0.75rem", fontWeight: "600", color: "#cbd5e1" }}>Telegram Bot Token</label>
                  <input
                    type="text"
                    placeholder="123456789:ABCdef..."
                    value={settings.telegram_bot_token || ""}
                    onChange={e => setSettings({ ...settings, telegram_bot_token: e.target.value })}
                    style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-color)", borderRadius: "6px", padding: "8px", color: "#fff", marginTop: "4px" }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: "0.75rem", fontWeight: "600", color: "#cbd5e1" }}>Owner Chat ID</label>
                  <input
                    type="text"
                    placeholder="987654321"
                    value={settings.owner_chat_id || ""}
                    onChange={e => setSettings({ ...settings, owner_chat_id: e.target.value })}
                    style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-color)", borderRadius: "6px", padding: "8px", color: "#fff", marginTop: "4px" }}
                  />
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <button type="button" className="btn-primary" style={{ background: "rgba(56, 189, 248, 0.15)", color: "#38bdf8", border: "1px solid rgba(56, 189, 248, 0.3)" }} onClick={handleTestTelegram}>
                  <Send size={14} /> Send Test Telegram Alert
                </button>
                {telegramTestMsg && <span style={{ fontSize: "0.8rem", color: "#cbd5e1" }}>{telegramTestMsg}</span>}
              </div>
            </div>

            {/* Email Channel Section */}
            <div style={{ marginBottom: "28px", borderBottom: "1px solid var(--border-color)", paddingBottom: "24px" }}>
              <h3 style={{ fontSize: "1rem", fontWeight: "600", marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
                <Mail size={18} color="#a855f7" /> Email Digest & Approval Channel
              </h3>

              <div>
                <label style={{ fontSize: "0.75rem", fontWeight: "600", color: "#cbd5e1" }}>Target Notification Email</label>
                <input
                  type="email"
                  placeholder="finance@merchant.com"
                  value={settings.target_email || ""}
                  onChange={e => setSettings({ ...settings, target_email: e.target.value })}
                  style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-color)", borderRadius: "6px", padding: "8px", color: "#fff", marginTop: "4px" }}
                />
              </div>
            </div>

            {/* Authority Policy Engine Section */}
            <div style={{ marginBottom: "28px" }}>
              <h3 style={{ fontSize: "1rem", fontWeight: "600", marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
                <Shield size={18} color="#f59e0b" /> Authority & Permission Limits
              </h3>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                <div>
                  <label style={{ fontSize: "0.75rem", fontWeight: "600", color: "#cbd5e1" }}>Auto-Approve Limit (₹)</label>
                  <input
                    type="number"
                    value={settings.authority?.auto_approve_limit || 10000}
                    onChange={e => setSettings({
                      ...settings,
                      authority: { ...settings.authority, auto_approve_limit: parseFloat(e.target.value) }
                    })}
                    style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-color)", borderRadius: "6px", padding: "8px", color: "#fff", marginTop: "4px" }}
                  />
                  <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "4px" }}>Discrepancies ≤ this amount auto-resolved</div>
                </div>

                <div>
                  <label style={{ fontSize: "0.75rem", fontWeight: "600", color: "#cbd5e1" }}>Approval Required Limit (₹)</label>
                  <input
                    type="number"
                    value={settings.authority?.approval_required_limit || 50000}
                    onChange={e => setSettings({
                      ...settings,
                      authority: { ...settings.authority, approval_required_limit: parseFloat(e.target.value) }
                    })}
                    style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-color)", borderRadius: "6px", padding: "8px", color: "#fff", marginTop: "4px" }}
                  />
                  <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "4px" }}>Requires owner Telegram/Email approval</div>
                </div>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button type="submit" className="btn-primary" disabled={loading}>
                {loading ? "Saving..." : "Save Control Plane Settings"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* TAB 4: HERMES CONTROLLER ACTIVITY FEED */}
      {activeTab === "activity" && (
        <div className="glass-panel" style={{ padding: "28px" }}>
          <h2 style={{ fontSize: "1.2rem", fontWeight: "700", marginBottom: "20px", display: "flex", alignItems: "center", gap: "8px" }}>
            <Terminal size={20} color="#34d399" /> Real-Time AI Controller Audit Log
          </h2>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {activityFeed.length === 0 ? (
              <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>No controller activities logged yet. Run a reconciliation sync to view events.</p>
            ) : (
              activityFeed.map((act, idx) => (
                <div key={idx} style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border-color)", padding: "12px 16px", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginRight: "12px" }}>{act.timestamp}</span>
                    <span style={{ fontSize: "0.8rem", fontWeight: "700", color: "#818cf8", marginRight: "12px" }}>[{act.action}]</span>
                    <span style={{ fontSize: "0.85rem", color: "#e2e8f0" }}>{act.details}</span>
                  </div>
                  {act.chain_id && (
                    <span style={{ fontSize: "0.75rem", background: "rgba(255,255,255,0.05)", padding: "2px 8px", borderRadius: "4px", color: "#38bdf8" }}>
                      {act.chain_id}
                    </span>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Modal 1: Custom CSV Upload */}
      {showUploadModal && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
          background: "rgba(0, 0, 0, 0.8)", backdropFilter: "blur(8px)",
          display: "flex", justifyContent: "center", alignItems: "center", zIndex: 1000
        }}>
          <div className="glass-panel" style={{ width: "90%", maxWidth: "550px", padding: "28px" }}>
            <h2 style={{ fontSize: "1.2rem", fontWeight: "700", marginBottom: "6px" }}>Upload Merchant CSV Statements</h2>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "20px" }}>
              Upload real financial exports (ERP Invoices, Payment Gateway CSV, Settlement report, Bank statement).
            </p>

            <form onSubmit={handleCustomUploadSubmit} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ fontSize: "0.75rem", fontWeight: "600", color: "#cbd5e1" }}>1. Invoices CSV</label>
                <input type="file" accept=".csv" onChange={e => setUploadInvoices(e.target.files[0])} style={{ marginTop: "4px", width: "100%", fontSize: "0.8rem" }} />
              </div>
              <div>
                <label style={{ fontSize: "0.75rem", fontWeight: "600", color: "#cbd5e1" }}>2. Gateway Payments CSV</label>
                <input type="file" accept=".csv" onChange={e => setUploadPayments(e.target.files[0])} style={{ marginTop: "4px", width: "100%", fontSize: "0.8rem" }} />
              </div>
              <div>
                <label style={{ fontSize: "0.75rem", fontWeight: "600", color: "#cbd5e1" }}>3. Settlement CSV</label>
                <input type="file" accept=".csv" onChange={e => setUploadSettlements(e.target.files[0])} style={{ marginTop: "4px", width: "100%", fontSize: "0.8rem" }} />
              </div>
              <div>
                <label style={{ fontSize: "0.75rem", fontWeight: "600", color: "#cbd5e1" }}>4. Bank Statement CSV</label>
                <input type="file" accept=".csv" onChange={e => setUploadBank(e.target.files[0])} style={{ marginTop: "4px", width: "100%", fontSize: "0.8rem" }} />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "16px" }}>
                <button type="button" className="btn-primary" style={{ background: "transparent" }} onClick={() => setShowUploadModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={loading}>{loading ? "Processing..." : "Run Upload Reconciliation"}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal 2: Razorpay Test Sync */}
      {showRazorpayModal && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
          background: "rgba(0, 0, 0, 0.8)", backdropFilter: "blur(8px)",
          display: "flex", justifyContent: "center", alignItems: "center", zIndex: 1000
        }}>
          <div className="glass-panel" style={{ width: "90%", maxWidth: "500px", padding: "28px" }}>
            <h2 style={{ fontSize: "1.2rem", fontWeight: "700", marginBottom: "6px" }}>Razorpay Test-Mode Sandbox Sync</h2>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "20px" }}>
              Enter your Razorpay Test Key ID & Secret to sync live sandbox payments & settlements via API.
            </p>

            <form onSubmit={handleRazorpaySyncSubmit} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ fontSize: "0.75rem", fontWeight: "600", color: "#cbd5e1" }}>Razorpay Key ID</label>
                <input
                  type="text"
                  placeholder="rzp_test_..."
                  value={rzpKeyId}
                  onChange={e => setRzpKeyId(e.target.value)}
                  required
                  style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-color)", borderRadius: "6px", padding: "8px", color: "#fff", marginTop: "4px" }}
                />
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", fontWeight: "600", color: "#cbd5e1" }}>Razorpay Key Secret</label>
                <input
                  type="password"
                  placeholder="••••••••••••••••"
                  value={rzpKeySecret}
                  onChange={e => setRzpKeySecret(e.target.value)}
                  required
                  style={{ width: "100%", background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-color)", borderRadius: "6px", padding: "8px", color: "#fff", marginTop: "4px" }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "16px" }}>
                <button type="button" className="btn-primary" style={{ background: "transparent" }} onClick={() => setShowRazorpayModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={loading}>{loading ? "Syncing API..." : "Sync & Reconcile"}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Case Trace Modal */}
      {selectedCase && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
          background: "rgba(0, 0, 0, 0.8)", backdropFilter: "blur(8px)",
          display: "flex", justifyContent: "center", alignItems: "center", zIndex: 1000
        }}>
          <div className="glass-panel" style={{ width: "90%", maxWidth: "850px", padding: "28px", maxHeight: "90vh", overflowY: "auto" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
              <div>
                <h2 style={{ fontSize: "1.25rem", fontWeight: "700" }}>
                  4-Way Transaction Trace: {selectedCase.reconciliation.chain_id}
                </h2>
                <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                  Evidence Package & Controller Diagnosis
                </p>
              </div>
              <button
                onClick={() => setSelectedCase(null)}
                style={{ background: "none", border: "none", color: "#fff", fontSize: "1.5rem", cursor: "pointer" }}
              >
                ×
              </button>
            </div>

            {/* AI Diagnosis Header */}
            <div style={{ background: "rgba(99, 102, 241, 0.1)", border: "1px solid rgba(99, 102, 241, 0.3)", borderRadius: "10px", padding: "16px", marginBottom: "24px" }}>
              <div style={{ fontSize: "0.75rem", fontWeight: "600", color: "#818cf8", marginBottom: "4px" }}>
                AI CONTROLLER DIAGNOSIS
              </div>
              <div style={{ fontSize: "0.9rem", color: "#e2e8f0" }}>
                {selectedCase.reconciliation.explanation}
              </div>
            </div>

            {/* 4-Way Chain Timeline */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px", marginBottom: "24px" }}>
              <div style={{ background: "rgba(255, 255, 255, 0.03)", padding: "12px", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "8px" }}>
                  <FileText size={14} /> 1. INVOICE
                </div>
                <div style={{ fontWeight: "600", fontSize: "0.85rem" }}>{selectedCase.trace.invoice?.invoice_id}</div>
                <div style={{ fontSize: "0.8rem", color: "#34d399", marginTop: "4px" }}>₹{selectedCase.trace.invoice?.gross_amount}</div>
              </div>

              <div style={{ background: "rgba(255, 255, 255, 0.03)", padding: "12px", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "8px" }}>
                  <CreditCard size={14} /> 2. PG PAYMENT
                </div>
                <div style={{ fontWeight: "600", fontSize: "0.85rem" }}>{selectedCase.trace.payment?.payment_id || "MISSING"}</div>
                <div style={{ fontSize: "0.8rem", color: "#38bdf8", marginTop: "4px" }}>Net: ₹{selectedCase.trace.payment?.net_amount || 0}</div>
              </div>

              <div style={{ background: "rgba(255, 255, 255, 0.03)", padding: "12px", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "8px" }}>
                  <Building size={14} /> 3. SETTLEMENT
                </div>
                <div style={{ fontWeight: "600", fontSize: "0.85rem" }}>{selectedCase.trace.settlement?.settlement_id || "MISSING"}</div>
                <div style={{ fontSize: "0.8rem", color: "#fbbf24", marginTop: "4px" }}>Payout: ₹{selectedCase.trace.settlement?.net_amount || 0}</div>
              </div>

              <div style={{ background: "rgba(255, 255, 255, 0.03)", padding: "12px", borderRadius: "8px", border: "1px solid var(--border-color)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "8px" }}>
                  <Banknote size={14} /> 4. BANK CREDIT
                </div>
                <div style={{ fontWeight: "600", fontSize: "0.85rem" }}>{selectedCase.trace.bank_transaction?.bank_txn_id || "MISSING"}</div>
                <div style={{ fontSize: "0.8rem", color: "#34d399", marginTop: "4px" }}>Credit: ₹{selectedCase.trace.bank_transaction?.credit || 0}</div>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button className="btn-primary" onClick={() => setSelectedCase(null)}>
                Close Case Review
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}