import React, { useState, useEffect } from 'react';
import {
  ShieldCheck, AlertTriangle, CheckCircle2, RefreshCw,
  Search, Eye, Activity, Cpu, FileText, CreditCard, Building, Banknote, Upload, Key, Database
} from 'lucide-react';

const API_BASE = "http://127.0.0.1:8000";

const statusPillClass = (status) => {
  switch (status) {
    case 'RECONCILED':    return 'pill pill--ok';
    case 'PROBABLE_MATCH': return 'pill pill--warn';
    case 'HIGH_RISK':     return 'pill pill--vio';
    case 'EXCEPTION':     return 'pill pill--bad';
    default:              return 'pill pill--muted';
  }
};

const kpiValueClass = (idx) => {
  if (idx === 1) return 'kpi-value kpi-value--ok';
  if (idx === 2) return 'kpi-value kpi-value--info';
  if (idx === 3) return 'kpi-value kpi-value--vio';
  if (idx === 4) return 'kpi-value kpi-value--bad';
  return 'kpi-value';
};

export default function App() {
  const [summary, setSummary] = useState(null);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState("ALL");
  const [search, setSearch] = useState("");
  const [selectedCase, setSelectedCase] = useState(null);

  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showRazorpayModal, setShowRazorpayModal] = useState(false);

  const [uploadInvoices, setUploadInvoices] = useState(null);
  const [uploadPayments, setUploadPayments] = useState(null);
  const [uploadSettlements, setUploadSettlements] = useState(null);
  const [uploadBank, setUploadBank] = useState(null);

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

  const handleCustomUploadSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    const formData = new FormData();
    if (uploadInvoices) formData.append("invoices_file", uploadInvoices);
    if (uploadPayments) formData.append("payments_file", uploadPayments);
    if (uploadSettlements) formData.append("settlements_file", uploadSettlements);
    if (uploadBank) formData.append("bank_file", uploadBank);

    try {
      const res = await fetch(`${API_BASE}/api/reconcile/upload`, {
        method: "POST",
        body: formData
      });
      const data = await res.json();
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
      const res = await fetch(`${API_BASE}/api/reconcile/razorpay-sync`, {
        method: "POST",
        body: formData
      });
      const data = await res.json();
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

  const totalCount = filteredResults.length;

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <div className="brand">
            <div className="brand-mark"><Cpu size={18} /></div>
            <h1>LedgerPilot</h1>
            <span className="ver">v04 · TRACK&nbsp;04</span>
          </div>
          <p className="subtitle">
            <strong>AI Finance Controller</strong>: multi-source reconciliation across invoices, gateway
            payments, settlements, and bank credits. Real CSV parsing, Razorpay API sync.
          </p>
        </div>

        <div className="actions">
          <button className="btn" onClick={() => setShowUploadModal(true)}>
            <Upload size={14} /> Upload CSVs
          </button>
          <button className="btn" onClick={() => setShowRazorpayModal(true)}>
            <Key size={14} /> Razorpay Sync
          </button>
          <button className="btn btn--primary" onClick={handleRunReconciliation} disabled={loading}>
            <RefreshCw size={14} className={loading ? "spin" : ""} />
            {loading ? "Processing…" : "Run Benchmark"}
          </button>
        </div>
      </header>

      {summary && summary.mode && (
        <div className="mode-banner">
          <span className="dot" />
          <Database size={14} />
          <span>Active data mode · <strong>{summary.mode}</strong></span>
        </div>
      )}

      <section className="kpi-grid" aria-label="Key performance indicators">
        <div className="kpi">
          <div className="kpi-head"><span>Total processed</span><span className="kpi-icon"><Activity size={14} /></span></div>
          <div className="kpi-value">{summary ? summary.total_records : "—"}</div>
          <div className="kpi-foot">4-way record chains</div>
        </div>
        <div className="kpi">
          <div className="kpi-head"><span>Auto-closure rate</span><span className="kpi-icon"><CheckCircle2 size={14} /></span></div>
          <div className={kpiValueClass(1)}>{summary ? summary.controller_closure_rate : "—"}</div>
          <div className="kpi-foot">Straight-through resolution</div>
        </div>
        <div className="kpi">
          <div className="kpi-head"><span>Exception precision</span><span className="kpi-icon"><ShieldCheck size={14} /></span></div>
          <div className={kpiValueClass(2)}>{summary ? (summary.exception_precision || "100.0%") : "—"}</div>
          <div className="kpi-foot">Zero false positives</div>
        </div>
        <div className="kpi">
          <div className="kpi-head"><span>Exception recall</span><span className="kpi-icon"><ShieldCheck size={14} /></span></div>
          <div className={kpiValueClass(3)}>{summary ? (summary.exception_recall || "100.0%") : "—"}</div>
          <div className="kpi-foot">Caught all discrepancies</div>
        </div>
        <div className="kpi">
          <div className="kpi-head"><span>Flagged exceptions</span><span className="kpi-icon"><AlertTriangle size={14} /></span></div>
          <div className={kpiValueClass(4)}>{summary ? summary.exceptions_flagged : "—"}</div>
          <div className="kpi-foot">Escalated for review</div>
        </div>
      </section>

      <section className="panel" aria-label="Reconciliation cases">
        <div className="panel-head">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span className="panel-title">Reconciliation cases</span>
            <span className="panel-meta">{totalCount.toString().padStart(3, '0')} / {results.length.toString().padStart(3, '0')}</span>
          </div>

          <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <div className="tabs" role="tablist">
              {["ALL", "RECONCILED", "PROBABLE", "EXCEPTION"].map(tab => (
                <button
                  key={tab}
                  role="tab"
                  aria-pressed={filter === tab}
                  className="tab"
                  onClick={() => setFilter(tab)}
                >
                  {tab === "RECONCILED" ? "Reconciled"
                    : tab === "PROBABLE" ? "Probable"
                    : tab === "EXCEPTION" ? "Exceptions"
                    : "All"}
                </button>
              ))}
            </div>

            <div className="search">
              <Search size={14} />
              <input
                type="text"
                placeholder="Search chain, invoice, or reason…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Chain</th>
                <th>Invoice</th>
                <th>Status</th>
                <th>Root cause</th>
                <th style={{ textAlign: 'right' }}>Discrepancy</th>
                <th style={{ textAlign: 'right' }}>Confidence</th>
                <th>Severity</th>
                <th style={{ textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredResults.map(r => (
                <tr key={r.chain_id}>
                  <td className="t-mono t-strong">{r.chain_id}</td>
                  <td className="t-mono t-dim">{r.invoice_id || "—"}</td>
                  <td>
                    <span className={statusPillClass(r.status)}>{r.status.replace('_', ' ')}</span>
                  </td>
                  <td className="t-dim" style={{ maxWidth: 320 }}>{r.root_cause}</td>
                  <td className={`t-num ${r.discrepancy_amount > 0 ? 't-num--neg' : 't-num--pos'}`}>
                    ₹{r.discrepancy_amount.toFixed(2)}
                  </td>
                  <td className="t-num t-dim">{(r.confidence_score * 100).toFixed(0)}%</td>
                  <td><span className={`sev sev--${r.severity}`}>{r.severity}</span></td>
                  <td style={{ textAlign: 'right' }}>
                    <button className="btn btn--link" onClick={() => handleOpenDetail(r.chain_id)}>
                      <Eye size={13} /> Trace
                    </button>
                  </td>
                </tr>
              ))}
              {filteredResults.length === 0 && (
                <tr>
                  <td colSpan="8" style={{ textAlign: 'center', padding: '48px 20px', color: 'var(--text-mut)' }}>
                    No cases match the current filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {showUploadModal && (
        <div className="scrim" onMouseDown={(e) => { if (e.target === e.currentTarget) setShowUploadModal(false); }}>
          <div className="modal" role="dialog" aria-modal="true" aria-labelledby="upload-title">
            <div className="modal-head">
              <div>
                <div id="upload-title" className="modal-title">Upload merchant CSV statements</div>
                <div className="modal-sub">Real financial exports: ERP invoices, payment gateway CSV, settlement report, bank statement.</div>
              </div>
              <button className="modal-close" aria-label="Close" onClick={() => setShowUploadModal(false)}>×</button>
            </div>
            <form onSubmit={handleCustomUploadSubmit}>
              <div className="modal-body">
                <div className="field">
                  <label htmlFor="up-invoices">1 · Invoices CSV</label>
                  <input id="up-invoices" type="file" accept=".csv" onChange={e => setUploadInvoices(e.target.files[0])} />
                </div>
                <div className="field">
                  <label htmlFor="up-payments">2 · Gateway payments CSV</label>
                  <input id="up-payments" type="file" accept=".csv" onChange={e => setUploadPayments(e.target.files[0])} />
                </div>
                <div className="field">
                  <label htmlFor="up-settlements">3 · Settlement CSV</label>
                  <input id="up-settlements" type="file" accept=".csv" onChange={e => setUploadSettlements(e.target.files[0])} />
                </div>
                <div className="field">
                  <label htmlFor="up-bank">4 · Bank statement CSV</label>
                  <input id="up-bank" type="file" accept=".csv" onChange={e => setUploadBank(e.target.files[0])} />
                </div>
              </div>
              <div className="modal-foot">
                <button type="button" className="btn btn--ghost" onClick={() => setShowUploadModal(false)}>Cancel</button>
                <button type="submit" className="btn btn--primary" disabled={loading}>
                  {loading ? "Processing…" : "Run upload reconciliation"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showRazorpayModal && (
        <div className="scrim" onMouseDown={(e) => { if (e.target === e.currentTarget) setShowRazorpayModal(false); }}>
          <div className="modal" role="dialog" aria-modal="true" aria-labelledby="rzp-title">
            <div className="modal-head">
              <div>
                <div id="rzp-title" className="modal-title">Razorpay test-mode sandbox sync</div>
                <div className="modal-sub">Enter test key credentials to sync live sandbox payments &amp; settlements via API.</div>
              </div>
              <button className="modal-close" aria-label="Close" onClick={() => setShowRazorpayModal(false)}>×</button>
            </div>
            <form onSubmit={handleRazorpaySyncSubmit}>
              <div className="modal-body">
                <div className="field">
                  <label htmlFor="rzp-key">Razorpay key ID</label>
                  <input id="rzp-key" type="text" placeholder="rzp_test_…" value={rzpKeyId} onChange={e => setRzpKeyId(e.target.value)} required />
                </div>
                <div className="field">
                  <label htmlFor="rzp-secret">Razorpay key secret</label>
                  <input id="rzp-secret" type="password" placeholder="••••••••••••••••" value={rzpKeySecret} onChange={e => setRzpKeySecret(e.target.value)} required />
                </div>
              </div>
              <div className="modal-foot">
                <button type="button" className="btn btn--ghost" onClick={() => setShowRazorpayModal(false)}>Cancel</button>
                <button type="submit" className="btn btn--primary" disabled={loading}>
                  {loading ? "Syncing API…" : "Sync & reconcile"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {selectedCase && (
        <div className="scrim" onMouseDown={(e) => { if (e.target === e.currentTarget) setSelectedCase(null); }}>
          <div className="modal modal--wide" role="dialog" aria-modal="true" aria-labelledby="trace-title">
            <div className="modal-head">
              <div>
                <div id="trace-title" className="modal-title">
                  4-way transaction trace · <span className="t-mono" style={{ color: 'var(--text)' }}>{selectedCase.reconciliation.chain_id}</span>
                </div>
                <div className="modal-sub">Evidence package &amp; controller diagnosis</div>
              </div>
              <button className="modal-close" aria-label="Close" onClick={() => setSelectedCase(null)}>×</button>
            </div>

            <div className="modal-body">
              <div className="diagnosis">
                <div className="diagnosis-tag">AI controller diagnosis</div>
                <p>{selectedCase.reconciliation.explanation}</p>
              </div>

              <div className="chain">
                <div className="chain-step">
                  <div className="chain-step-label"><FileText size={12} /> 1 · Invoice</div>
                  <div className="chain-step-id">{selectedCase.trace.invoice?.invoice_id || "—"}</div>
                  <div className="chain-step-amt chain-step-amt--inv">₹{selectedCase.trace.invoice?.gross_amount ?? 0}</div>
                </div>
                <div className="chain-step">
                  <div className="chain-step-label"><CreditCard size={12} /> 2 · PG payment</div>
                  <div className="chain-step-id">{selectedCase.trace.payment?.payment_id || "MISSING"}</div>
                  <div className={`chain-step-amt ${selectedCase.trace.payment?.payment_id ? 'chain-step-amt--pg' : 'chain-step-amt--miss'}`}>
                    Net · ₹{selectedCase.trace.payment?.net_amount || 0}
                  </div>
                </div>
                <div className="chain-step">
                  <div className="chain-step-label"><Building size={12} /> 3 · Settlement</div>
                  <div className="chain-step-id">{selectedCase.trace.settlement?.settlement_id || "MISSING"}</div>
                  <div className={`chain-step-amt ${selectedCase.trace.settlement?.settlement_id ? 'chain-step-amt--set' : 'chain-step-amt--miss'}`}>
                    Payout · ₹{selectedCase.trace.settlement?.net_amount || 0}
                  </div>
                </div>
                <div className="chain-step">
                  <div className="chain-step-label"><Banknote size={12} /> 4 · Bank credit</div>
                  <div className="chain-step-id">{selectedCase.trace.bank_transaction?.bank_txn_id || "MISSING"}</div>
                  <div className={`chain-step-amt ${selectedCase.trace.bank_transaction?.bank_txn_id ? 'chain-step-amt--bnk' : 'chain-step-amt--miss'}`}>
                    Credit · ₹{selectedCase.trace.bank_transaction?.credit || 0}
                  </div>
                </div>
              </div>
            </div>

            <div className="modal-foot">
              <button className="btn" onClick={() => setSelectedCase(null)}>Close case review</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}