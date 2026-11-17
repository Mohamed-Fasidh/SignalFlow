"use client";
import { type FormEvent, type PointerEvent as ReactPointerEvent, useCallback, useEffect, useMemo, useState, useRef } from "react";

type Account = {
  id: string; name: string; domain: string; industry?: string | null;
  employee_count?: number | null; country?: string | null; score: number;
  priority?: "low" | "normal" | "high" | "critical"; is_pinned?: boolean; tier?: "unknown" | "smb" | "mid_market" | "enterprise"; crm_synced_at?: string | null;
  score_reasons: Array<{ signal_id?: string; type: string; points: number; evidence: string; source: string }>;
};
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const DEMO_TENANT = process.env.NEXT_PUBLIC_DEMO_TENANT_ID || "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";

export default function Home() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [query, setQuery] = useState("");
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [industry, setIndustry] = useState("B2B SaaS");
  const [accountTier, setAccountTier] = useState<"unknown"|"smb"|"mid_market"|"enterprise">("unknown");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [undoArchiveId, setUndoArchiveId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null);
  const [signalType, setSignalType] = useState("security_hiring");
  const [signalDescription, setSignalDescription] = useState("");
  const [signalSource, setSignalSource] = useState("");
  const [actionBusy, setActionBusy] = useState(false);
  const [utilityPanel, setUtilityPanel] = useState<"help" | "settings" | "apps" | "calendar" | "notes" | "tasks" | "contacts" | "audit" | "duplicates" | "webhooks" | "research" | null>(null);
  const [notes, setNotes] = useState("");
  const [taskDone, setTaskDone] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [online, setOnline] = useState(true);
  const [searchOpen, setSearchOpen] = useState(false);
  const [highIntentOnly, setHighIntentOnly] = useState(false);
  const [crmSyncedOnly, setCrmSyncedOnly] = useState(false);
  const [enterpriseOnly, setEnterpriseOnly] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [activeRow, setActiveRow] = useState(0);
  const [tableScrollTop, setTableScrollTop] = useState(0);
  const [hasMoreAccounts, setHasMoreAccounts] = useState(true);
  const [density, setDensity] = useState<"comfortable" | "compact">("compact");
  const [researchBrief, setResearchBrief] = useState<Record<string, unknown> | null>(null);
  const [researchJobStatus, setResearchJobStatus] = useState<string>("");
  const [remoteMatches, setRemoteMatches] = useState<Account[]>([]);
  const [loadingMore, setLoadingMore] = useState(false);
  const [panelData, setPanelData] = useState<unknown[]>([]);
  const [hubspotStatus, setHubspotStatus] = useState<{configured:boolean;webhook_secret_configured:boolean;last_webhook_at:string|null}>({configured:false,webhook_secret_configured:false,last_webhook_at:null});
  const searchRef = useRef<HTMLInputElement>(null);

  const headers = useMemo(() => ({ "X-Tenant-ID": DEMO_TENANT, "Content-Type": "application/json" }), []);
  const filtered = accounts.filter(a => (!highIntentOnly || a.score >= 70) && (!crmSyncedOnly || Boolean(a.crm_synced_at)) && (!enterpriseOnly || a.tier === "enterprise") && `${a.name} ${a.domain} ${a.industry || ""}`.toLowerCase().includes(query.toLowerCase()));
  const average = accounts.length ? Math.round(accounts.reduce((sum, a) => sum + a.score, 0) / accounts.length) : 0;
  const signalCount = accounts.reduce((sum, account) => sum + (account.score_reasons?.length || 0), 0);
  const rowHeight = density === "compact" ? 48 : 56;
  const virtualStart = Math.max(0, Math.floor(tableScrollTop / rowHeight) - 8);
  const virtualEnd = Math.min(filtered.length, virtualStart + 30);
  const visibleAccounts = filtered.slice(virtualStart, virtualEnd);
  const loadAccounts = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const filterParams = new URLSearchParams(); if (crmSyncedOnly) filterParams.set("crm_synced", "true"); if (enterpriseOnly) filterParams.set("tier", "enterprise");
      const response = await fetch(`${API}/api/v1/leads/prioritized?limit=100&offset=0&${filterParams.toString()}`, { headers });
      if (!response.ok) throw new Error(`API returned ${response.status}. Start the stack and seed demo data.`);
      const firstPage = await response.json() as Account[];
      setAccounts(firstPage); setHasMoreAccounts(firstPage.length === 100); setTableScrollTop(0);
    } catch (e) { setError(e instanceof Error ? e.message : "Unable to load accounts"); }
    finally { setLoading(false); }
  }, [headers, crmSyncedOnly, enterpriseOnly]);
  const loadMoreAccounts = useCallback(async () => {
    if (loadingMore || !hasMoreAccounts || loading) return;
    setLoadingMore(true);
    try {
      const filterParams = new URLSearchParams(); if (crmSyncedOnly) filterParams.set("crm_synced", "true"); if (enterpriseOnly) filterParams.set("tier", "enterprise");
      const response = await fetch(`${API}/api/v1/leads/prioritized?limit=100&offset=${accounts.length}&${filterParams.toString()}`, { headers });
      if (!response.ok) throw new Error(`API returned ${response.status}`);
      const nextPage = await response.json() as Account[];
      setAccounts(current => [...current, ...nextPage]); setHasMoreAccounts(nextPage.length === 100);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load more accounts"); }
    finally { setLoadingMore(false); }
  }, [accounts.length, hasMoreAccounts, headers, loading, loadingMore, crmSyncedOnly, enterpriseOnly]);
  useEffect(() => { void loadAccounts(); }, [loadAccounts]);
  useEffect(() => {
    let alive = true;
    const refresh = async () => { try { const response = await fetch(`${API}/api/v1/integrations/hubspot/status`, { headers }); if (response.ok && alive) setHubspotStatus(await response.json()); } catch { /* API unavailable; keep last known state */ } };
    void refresh(); const timer = window.setInterval(refresh, 60000);
    return () => { alive = false; window.clearInterval(timer); };
  }, [headers]);
  useEffect(() => {
    if (!searchOpen || !query.trim()) { setRemoteMatches([]); return; }
    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch(`${API}/api/v1/accounts?q=${encodeURIComponent(query.trim())}&limit=8`, { headers });
        if (response.ok) setRemoteMatches(await response.json() as Account[]);
      } catch { setRemoteMatches([]); }
    }, 220);
    return () => window.clearTimeout(timer);
  }, [API, headers, query, searchOpen]);
  useEffect(() => {
    if (selectedAccount) {
      const updated = accounts.find(account => account.id === selectedAccount.id);
      if (updated) setSelectedAccount(updated);
    }
  }, [accounts, selectedAccount]);
  useEffect(() => {
    setOnline(navigator.onLine);
    const onlineHandler = async () => {
      setOnline(true);
      try {
        const queued = JSON.parse(window.localStorage.getItem("signalflow-offline-queue") || "[]") as Array<{path:string;body:unknown;label:string}>;
        if (!queued.length) return;
        const remaining = [] as typeof queued;
        for (const item of queued) {
          try {
            const response = await fetch(`${API}${item.path}`, { method: "POST", headers, body: JSON.stringify(item.body) });
            if (!response.ok) { remaining.push(item); continue; }
          } catch { remaining.push(item); }
        }
        window.localStorage.setItem("signalflow-offline-queue", JSON.stringify(remaining));
        if (remaining.length < queued.length) { setNotice(`${queued.length - remaining.length} queued change(s) synced.`); void loadAccounts(); }
        if (remaining.length) setError(`${remaining.length} queued change(s) could not sync yet.`);
      } catch { setError("Could not sync offline changes. Check browser storage and reconnect."); }
    };
    const offlineHandler = () => setOnline(false);
    window.addEventListener("online", onlineHandler);
    window.addEventListener("offline", offlineHandler);
    return () => { window.removeEventListener("online", onlineHandler); window.removeEventListener("offline", offlineHandler); };
  }, [headers, loadAccounts]);
  useEffect(() => {
    try {
      setDarkMode(window.localStorage.getItem("signalflow-theme") === "dark");
      setNotes(window.localStorage.getItem("signalflow-notes") || "");
      setTaskDone(window.localStorage.getItem("signalflow-task-done") === "true");
    } catch { /* storage may be unavailable */ }
  }, []);
  useEffect(() => { try { window.localStorage.setItem("signalflow-notes", notes); } catch { /* storage may be unavailable */ } }, [notes]);
  useEffect(() => { try { window.localStorage.setItem("signalflow-task-done", String(taskDone)); } catch { /* storage may be unavailable */ } }, [taskDone]);
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const typing = target && (["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName) || target.isContentEditable);
      if (event.key === "/" && !typing) { event.preventDefault(); searchRef.current?.focus(); setSearchOpen(true); }
      if (event.key === "?" && !typing) { event.preventDefault(); setUtilityPanel("help"); }
      if (event.key === "Escape") { setSelectedAccount(null); setUtilityPanel(null); setSearchOpen(false); (document.activeElement as HTMLElement | null)?.blur?.(); }
      if (!typing && filtered.length && (event.key === "j" || event.key === "ArrowDown")) { event.preventDefault(); setActiveRow(i => Math.min(filtered.length - 1, i + 1)); }
      if (!typing && filtered.length && (event.key === "k" || event.key === "ArrowUp")) { event.preventDefault(); setActiveRow(i => Math.max(0, i - 1)); }
      if (!typing && filtered[activeRow] && event.key === "Enter") { event.preventDefault(); openAccount(filtered[activeRow]); }
      if (!typing && filtered[activeRow] && event.key.toLowerCase() === "x") { event.preventDefault(); const id = filtered[activeRow].id; setSelectedIds(ids => ids.includes(id) ? ids.filter(value => value !== id) : [...ids, id]); }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [filtered, activeRow]);
  useEffect(() => {
    setActiveRow(0); setTableScrollTop(0);
    const viewport = document.querySelector<HTMLElement>(".virtual-table-viewport");
    if (viewport) viewport.scrollTop = 0;
  }, [query, highIntentOnly, crmSyncedOnly, enterpriseOnly]);
  useEffect(() => {
    document.querySelector<HTMLElement>(`[data-row-index="${activeRow}"]`)?.scrollIntoView({ block: "nearest" });
  }, [activeRow]);
  useEffect(() => {
    if (!notice) return;
    const timeout = window.setTimeout(() => { setNotice(""); setUndoArchiveId(null); }, 4500);
    return () => window.clearTimeout(timeout);
  }, [notice]);


  function openAccount(account: Account) { setResearchBrief(null); setResearchJobStatus(""); setSelectedAccount(account); }

  function queueOfflineRequest(path: string, body: unknown, label: string) {
    try {
      const queue = JSON.parse(window.localStorage.getItem("signalflow-offline-queue") || "[]") as Array<{path:string;body:unknown;label:string}>;
      queue.push({ path, body, label });
      window.localStorage.setItem("signalflow-offline-queue", JSON.stringify(queue));
      setNotice(`${label} queued. It will sync when you reconnect.`);
      return true;
    } catch { setError("Offline storage is unavailable. Reconnect before saving this change."); return false; }
  }

  async function addSignal(event: FormEvent) {
    event.preventDefault();
    if (!selectedAccount) return;
    const previousAccounts = accounts;
    const signalWeights: Record<string, number> = { compliance_requirement: 25, security_hiring: 20, enterprise_expansion: 20, funding: 15, icp_fit: 10, other: 0 };
    const optimisticPoints = Math.round((signalWeights[signalType] || 0) * 0.8);
    const optimisticSignal = { type: signalType, points: optimisticPoints, evidence: signalDescription, source: "dashboard" };
    setAccounts(current => current.map(account => account.id === selectedAccount.id ? { ...account, score: Math.min(100, account.score + optimisticPoints), score_reasons: [...(account.score_reasons || []), optimisticSignal] } : account));
    const signalBody = { account_id: selectedAccount.id, signal_type: signalType, description: signalDescription, source_url: signalSource || null, source_name: "dashboard", confidence: 80 };
    if (!navigator.onLine) { if (queueOfflineRequest("/api/v1/signals", signalBody, "Buying signal")) { setSignalDescription(""); setSignalSource(""); } else setAccounts(previousAccounts); return; }
    setActionBusy(true); setError(""); setNotice("");
    try {
      const response = await fetch(`${API}/api/v1/signals`, { method: "POST", headers,
        body: JSON.stringify({ account_id: selectedAccount.id, signal_type: signalType,
          description: signalDescription, source_url: signalSource || null, source_name: "dashboard", confidence: 80 }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
      setSignalDescription(""); setSignalSource("");
      setNotice("Buying signal saved and account score recalculated.");
      await loadAccounts();
    } catch (e) { setAccounts(previousAccounts); setError(e instanceof Error ? e.message : "Could not save buying signal"); }
    finally { setActionBusy(false); }
  }

  async function runAccountAction(action: "research" | "hubspot-sync", accountOverride?: Account) {
    const activeAccount = accountOverride || selectedAccount;
    if (!activeAccount) return;
    setActionBusy(true); setError(""); setNotice("");
    try {
      const response = await fetch(`${API}/api/v1/accounts/${activeAccount.id}/${action}`, { method: "POST", headers });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
      if (action === "research") {
        setResearchJobStatus("queued");
        let finalJob: Record<string, unknown> | null = null;
        for (let attempt = 0; attempt < 80; attempt++) {
          await new Promise(resolve => window.setTimeout(resolve, 1500));
          const poll = await fetch(`${API}/api/v1/research/jobs/${data.research_job_id}`, { headers });
          const job = await poll.json() as Record<string, unknown>;
          if (!poll.ok) throw new Error(String(job.detail || "Could not read research job status"));
          setResearchJobStatus(String(job.status || "running"));
          if (job.status === "completed" || job.status === "failed") { finalJob = job; break; }
        }
        if (!finalJob) throw new Error("Research is still running. Reopen the account to check its result shortly.");
        if (finalJob.status === "failed") throw new Error(String(finalJob.error || "AI research task failed"));
        setResearchBrief((finalJob.result || {}) as Record<string, unknown>);
        setResearchJobStatus("completed");
        setNotice("AI research brief generated.");
      } else {
        setNotice(`HubSpot company synced: ${data.hubspot_id}.`);
        void fetch(`${API}/api/v1/integrations/hubspot/status`, { headers }).then(r => r.ok ? r.json() : null).then(status => { if (status) setHubspotStatus(status); });
        await loadAccounts();
      }
    } catch (e) { setResearchJobStatus("failed"); setError(e instanceof Error ? e.message : `Could not run ${action}`); }
    finally { setActionBusy(false); }
  }

  async function createAccount(event: FormEvent) {
    event.preventDefault();
    const previousAccounts = accounts;
    const optimisticAccount: Account = { id: `pending-${Date.now()}`, name, domain, industry: industry || null, score: 0, score_reasons: [] };
    setAccounts(current => [...current, optimisticAccount]);
    const accountBody = { name, domain, industry: industry || null, tier: accountTier };
    if (!navigator.onLine) { if (queueOfflineRequest("/api/v1/accounts", accountBody, "New account")) { setName(""); setDomain(""); } else setAccounts(previousAccounts); return; }
    setSaving(true); setNotice(""); setError("");
    try {
      const response = await fetch(`${API}/api/v1/accounts`, { method: "POST", headers,
        body: JSON.stringify({ name, domain, industry: industry || null, tier: accountTier }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
      setName(""); setDomain(""); setAccountTier("unknown"); setNotice("Account created. Add buying signals through the API to calculate its score.");
      await loadAccounts();
    } catch (e) { setAccounts(previousAccounts); setError(e instanceof Error ? e.message : "Could not create account"); }
    finally { setSaving(false); }
  }

  async function pinAccount(account: Account) {
    const next = !account.is_pinned;
    const snapshot = accounts;
    setAccounts(rows => rows.map(row => row.id === account.id ? { ...row, is_pinned: next } : row));
    try {
      const response = await fetch(`${API}/api/v1/accounts/${account.id}/pin`, { method: "PATCH", headers, body: JSON.stringify({ pinned: next }) });
      if (!response.ok) throw new Error(`Pin update failed (${response.status})`);
      setNotice(next ? "Account pinned." : "Account unpinned.");
    } catch (e) { setAccounts(snapshot); setError(e instanceof Error ? e.message : "Could not update pin"); }
  }

  async function openDataPanel(panel: "audit" | "duplicates" | "webhooks" | "research") {
    setUtilityPanel(panel); setPanelData([]);
    const endpoint = panel === "audit" ? "/api/v1/audit/events" : panel === "duplicates" ? "/api/v1/duplicates" : panel === "research" ? "/api/v1/research/jobs" : "/api/v1/webhooks/events";
    try {
      const response = await fetch(`${API}${endpoint}`, { headers });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
      setPanelData(data as unknown[]);
    } catch (e) { setError(e instanceof Error ? e.message : `Could not load ${panel}`); }
  }

  async function archiveSignal(signalId?: string) {
    if (!selectedAccount || !signalId) return;
    const snapshot = accounts;
    setAccounts(current => current.map(a => a.id === selectedAccount.id ? { ...a, score_reasons: a.score_reasons.filter(r => r.signal_id !== signalId) } : a));
    setUndoArchiveId(signalId); setNotice("Signal archived");
    try {
      const response = await fetch(`${API}/api/v1/signals/${signalId}/archive`, { method: "PATCH", headers });
      if (!response.ok) throw new Error(`Archive failed (${response.status})`);
      await loadAccounts();
    } catch (e) { setAccounts(snapshot); setUndoArchiveId(null); setError(e instanceof Error ? e.message : "Could not archive signal"); }
  }

  async function undoArchive() {
    if (!undoArchiveId) return;
    const response = await fetch(`${API}/api/v1/signals/${undoArchiveId}/restore`, { method: "PATCH", headers });
    if (!response.ok) { setError("Could not restore the buying signal"); return; }
    setUndoArchiveId(null); setNotice("Buying signal restored."); await loadAccounts();
  }

  async function pushHubSpotNote() {
    if (!selectedAccount) return;
    const brief = `${selectedAccount.name}\n\n${String(researchBrief?.summary || "Account research brief")}\n\nBuying triggers: ${selectedAccount.score_reasons.map(r => r.evidence).join("; ")}`;
    try {
      const response = await fetch(`${API}/api/v1/accounts/${selectedAccount.id}/hubspot-note`, { method: "POST", headers, body: JSON.stringify({ body: brief }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
      setNotice(`Research note pushed to HubSpot (${data.note_id}).`);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not push note to HubSpot"); }
  }

  async function mergeAccounts(sourceId: string, targetId: string) {
    if (!window.confirm("Merge the source account and its signals into the target account? This cannot be undone.")) return;
    const snapshot = accounts;
    setAccounts(rows => rows.filter(row => row.id !== sourceId));
    try {
      const response = await fetch(`${API}/api/v1/accounts/${sourceId}/merge/${targetId}`, { method: "POST", headers });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || `Merge failed (${response.status})`);
      setNotice("Duplicate accounts merged."); await loadAccounts(); await openDataPanel("duplicates");
    } catch (e) { setAccounts(snapshot); setError(e instanceof Error ? e.message : "Could not merge accounts"); }
  }

  function toggleTheme() {
    setDarkMode(value => { const next = !value; try { window.localStorage.setItem("signalflow-theme", next ? "dark" : "light"); } catch { /* storage may be unavailable */ } return next; });
  }
  function ripple(event: ReactPointerEvent<HTMLElement>) {
    const target = event.target instanceof Element ? event.target.closest("button") : null;
    if (!target) return;
    const rect = target.getBoundingClientRect();
    target.style.setProperty("--ripple-x", `${event.clientX - rect.left}px`);
    target.style.setProperty("--ripple-y", `${event.clientY - rect.top}px`);
  }

  return <main className={`app-shell${darkMode ? " theme-dark" : ""}${collapsed ? " nav-collapsed" : ""}`} onPointerDown={ripple}>
    {actionBusy && <div className="task-progress" role="progressbar" aria-label="Working on account action" />}
    <header className="topbar">
      <button className="icon-button menu-toggle" aria-label="Toggle navigation" aria-expanded={!collapsed} onClick={() => { if (window.innerWidth <= 820) document.body.classList.toggle("nav-open"); else setCollapsed(value => !value); }}><span className="material-symbols-outlined">menu</span></button>
      <a className="brand" href="#" aria-label="SignalFlow AI home"><span className="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24" width="24" height="24" fill="none"><path d="M4 7.2 12 3l8 4.2v9.6L12 21l-8-4.2V7.2Z" stroke="currentColor" strokeWidth="1.7"/><path d="m7.5 12 3 3 6-6" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"/></svg></span><span>SignalFlow <span className="brand-ai">AI</span></span></a>
      <div className="global-search-wrap"><span className="material-symbols-outlined search-icon">search</span><input ref={searchRef} id="global-search" className="global-search" aria-label="Search accounts" aria-expanded={searchOpen} aria-controls="search-suggestions" placeholder="Search accounts, domains or industries" value={query} onFocus={() => setSearchOpen(true)} onBlur={() => window.setTimeout(() => setSearchOpen(false), 140)} onChange={e => setQuery(e.target.value)} /><button className={`search-filter-chip${highIntentOnly ? " selected" : ""}`} aria-pressed={highIntentOnly} onClick={() => setHighIntentOnly(value => !value)}>Intent: high</button><button className={`search-filter-chip${crmSyncedOnly ? " selected" : ""}`} aria-pressed={crmSyncedOnly} onClick={() => setCrmSyncedOnly(value => !value)}>CRM: synced</button><button className={`search-filter-chip${enterpriseOnly ? " selected" : ""}`} aria-pressed={enterpriseOnly} onClick={() => setEnterpriseOnly(value => !value)}>Tier: enterprise</button><kbd>/</kbd>{searchOpen && query && <div className="search-suggestions" id="search-suggestions" role="listbox"><div className="suggestion-label">Matching accounts</div>{(remoteMatches.length ? remoteMatches : filtered.slice(0,5)).map(account => <button key={account.id} role="option" onMouseDown={() => { openAccount(account); setSearchOpen(false); }}><span className="material-symbols-outlined">business</span><span><strong>{account.name}</strong><small>{account.domain}</small></span></button>)}{filtered.length === 0 && <p>No matching accounts</p>}</div>}</div>
      <div className="top-actions"><button className={`sync-health${hubspotStatus.configured ? " connected" : ""}`} title="Open HubSpot webhook deliveries" onClick={() => void openDataPanel("webhooks")}><i/>{hubspotStatus.configured ? "HubSpot · connected" : "HubSpot · setup required"}{hubspotStatus.last_webhook_at ? ` · ${new Date(hubspotStatus.last_webhook_at).toLocaleString()}` : ""}</button><button className="icon-button" aria-label="Keyboard shortcuts" title="Keyboard shortcuts" aria-expanded={utilityPanel === "help"} onClick={() => setUtilityPanel(utilityPanel === "help" ? null : "help")}><span className="material-symbols-outlined">keyboard</span></button><button className="icon-button theme-toggle" aria-label={darkMode ? "Switch to light theme" : "Switch to dark theme"} title={darkMode ? "Light theme" : "Dark theme"} onClick={toggleTheme}><span className="material-symbols-outlined">{darkMode ? "light_mode" : "dark_mode"}</span></button><button className="icon-button" aria-label="Settings" title="Settings" aria-expanded={utilityPanel === "settings"} onClick={() => setUtilityPanel(utilityPanel === "settings" ? null : "settings")}><span className="material-symbols-outlined">settings</span></button><button className="icon-button apps-button" aria-label="Workspace apps" title="Workspace apps" aria-expanded={utilityPanel === "apps"} onClick={() => setUtilityPanel(utilityPanel === "apps" ? null : "apps")}><span className="material-symbols-outlined">apps</span></button><button className="profile-button workspace-avatar-ring" aria-label="Demo workspace profile" title="Demo workspace profile" onClick={() => setUtilityPanel("settings")}>S</button></div>
    </header>
    <div className="workspace-layout">
      <aside className="sidebar" aria-label="Main navigation">
        <button className="new-button" onClick={() => document.getElementById("create-account")?.scrollIntoView({behavior:"smooth",block:"center"})}><span>＋</span> Add account</button>
        <div className="nav-section-label">Workspace</div>
        <button className="nav-item active" aria-current="page" title="Priority accounts"><span className="material-symbols-outlined nav-icon">domain</span><span>Priority accounts</span></button>
        
        <button className="nav-item" onClick={() => document.getElementById("accounts-panel")?.scrollIntoView({behavior:"smooth"})}><span className="material-symbols-outlined nav-icon">sensors</span><span>Buying signals</span><span className="nav-count">{signalCount}</span></button>
        <button className="nav-item" onClick={() => void openDataPanel("research")}><span className="material-symbols-outlined nav-icon">psychology</span><span>AI research briefs</span></button><button className="nav-item" onClick={() => void openDataPanel("duplicates")}><span className="material-symbols-outlined nav-icon">merge</span><span>Duplicate & merge queue</span></button><button className="nav-item" onClick={() => document.getElementById("integrations-panel")?.scrollIntoView({behavior:"smooth"})}><span className="material-symbols-outlined nav-icon">hub</span><span>CRM & integrations</span></button><button className="nav-item" onClick={() => void openDataPanel("audit")}><span className="material-symbols-outlined nav-icon">history</span><span>Audit logs</span></button>
        <div className="sidebar-spacer" />
        <div className="workspace-card"><span className="workspace-dot" /><span><strong>Demo workspace</strong><small>Synthetic sample data</small></span><span className="more">⋮</span></div>
      </aside>
      <section className="main-area"><div className="workspace-card-shell">
        <div className="page-heading"><div><div className="breadcrumb">Workspace <span>›</span> Overview</div><h1>Good evening</h1><p className="subtitle">Here’s what’s happening across your revenue pipeline.</p></div><button className="tonal-button" onClick={() => void loadAccounts()} disabled={loading}><span className="material-symbols-outlined">refresh</span> Refresh</button></div>
        <div className="metrics">
          <article className="metric-card"><div className="metric-top"><span>Prioritized accounts</span><span className="metric-icon blue material-symbols-outlined">domain</span></div><strong>{loading ? "—" : accounts.length}</strong><small>In this workspace</small></article>
          <article className="metric-card"><div className="metric-top"><span>High-intent accounts</span><span className="metric-icon green material-symbols-outlined">trending_up</span></div><strong>{loading ? "—" : accounts.filter(a => a.score >= 70).length}</strong><small>Score of 70 or higher</small></article>
          <article className="metric-card"><div className="metric-top"><span>Average lead score</span><span className="metric-icon amber material-symbols-outlined">monitoring</span></div><strong>{loading ? "—" : average}</strong><small>Evidence-based score</small></article>
        </div>
        <section className="surface-panel" id="accounts-panel">
          <div className="panel-heading"><div><h2>Accounts to prioritize</h2><p>Ranked by explainable buying-signal score</p></div><span className="result-count">{filtered.length} accounts</span></div>
          <div className="table-toolbar"><label className="bulk-select"><input type="checkbox" aria-label="Select all visible accounts" checked={visibleAccounts.length > 0 && visibleAccounts.every(account => selectedIds.includes(account.id))} onChange={event => setSelectedIds(ids => event.target.checked ? Array.from(new Set([...ids, ...visibleAccounts.map(account => account.id)])) : ids.filter(id => !visibleAccounts.some(account => account.id === id)))} /> Select</label><div className="table-search"><span className="material-symbols-outlined">search</span><input aria-label="Filter accounts" placeholder="Filter this list" value={query} onChange={e => setQuery(e.target.value)} /></div><button className="icon-button" aria-label="Refresh accounts" onClick={() => void loadAccounts()}><span className="material-symbols-outlined">refresh</span></button><label className="density-control">Density <select value={density} onChange={event => setDensity(event.target.value as "comfortable" | "compact")}><option value="compact">Compact</option><option value="comfortable">Comfortable</option></select></label></div>
          {error && <div className="alert error" role="alert"><span>!</span>{error}</div>}
          {loading && <div className="skeleton-list" aria-label="Loading accounts">{[1,2,3,4].map(n => <div className="skeleton-row" key={n}><i/><span><b/><em/></span><b/></div>)}</div>}
          {!loading && !error && filtered.length === 0 && <div className="empty-state"><span className="empty-illustration material-symbols-outlined">domain_disabled</span><strong>No matching accounts</strong><p>Try a different search or create a company record.</p><button className="primary-button" onClick={() => document.getElementById("create-account")?.scrollIntoView({behavior:"smooth"})}>Create account</button></div>}
          {!loading && filtered.length > 0 && <div className="account-table" role="table" aria-label="Prioritized accounts" aria-rowcount={filtered.length + 1}>
            <div className="table-header" role="row" aria-rowindex={1}><span role="columnheader">Company</span><span role="columnheader">Industry</span><span role="columnheader">Signals</span><span role="columnheader">Lead score</span><span role="columnheader" aria-label="Actions" /></div>
            <div className="virtual-table-viewport" role="rowgroup" aria-label="Account records" onScroll={event => { const node = event.currentTarget; setTableScrollTop(node.scrollTop); if (node.scrollTop + node.clientHeight >= node.scrollHeight - 180) void loadMoreAccounts(); }}>
            {virtualStart > 0 && <div className="virtual-spacer" role="presentation" style={{height:virtualStart * rowHeight}} />}
            {visibleAccounts.map((a, index) => <div className={`account-row ${density === "comfortable" ? "comfortable-row" : "compact-row"}${virtualStart + index === activeRow ? " keyboard-active" : ""}${selectedIds.includes(a.id) ? " row-selected" : ""}`} role="row" aria-rowindex={virtualStart + index + 2} aria-selected={selectedIds.includes(a.id)} data-row-index={virtualStart + index} key={a.id}>
              <div className="company-cell" role="cell"><label className="row-select" aria-label={`Select ${a.name}`}><input type="checkbox" checked={selectedIds.includes(a.id)} onChange={() => setSelectedIds(ids => ids.includes(a.id) ? ids.filter(value => value !== a.id) : [...ids, a.id])} /></label><div className="company-avatar">{a.name.slice(0,1).toUpperCase()}</div><span><strong>{a.name}</strong><small>{a.domain}</small></span></div>
              <span className="industry-cell" role="cell">{a.industry || "Not specified"}</span><span className="signal-count" role="cell">{a.score_reasons?.length || 0} signals</span>
              <span className="score-cell" role="cell"><strong className={`score-pill ${a.score >= 70 ? "score-high" : "score-normal"}`}>{a.score} · {a.score >= 70 ? "High intent" : "Developing"}</strong></span>
              <span role="cell" className="row-actions"><button className="row-action" title="Open account brief" aria-label={`Manage ${a.name}`} onClick={() => openAccount(a)}>Open</button><button className="row-action" title="Run AI research" aria-label={`Run AI research for ${a.name}`} onClick={() => { openAccount(a); void runAccountAction("research", a); }}><span className="material-symbols-outlined">auto_awesome</span></button><button className="row-action" title="Sync to HubSpot" aria-label={`Sync ${a.name} to HubSpot`} onClick={() => { openAccount(a); void runAccountAction("hubspot-sync", a); }}><span className="material-symbols-outlined">sync</span></button><button className={`row-action${a.is_pinned ? " pinned" : ""}`} title={a.is_pinned ? "Unpin account" : "Pin account"} aria-label={a.is_pinned ? `Unpin ${a.name}` : `Pin ${a.name}`} onClick={() => void pinAccount(a)}><span className="material-symbols-outlined">push_pin</span></button></span>
            </div>)}
            {virtualEnd < filtered.length && <div className="virtual-spacer" role="presentation" style={{height:(filtered.length - virtualEnd) * rowHeight}} />}
            {loadingMore && <div className="load-more-state" role="status">Loading more accounts…</div>}
            </div>
          </div>}
        </section>
        {selectedAccount && <section className="surface-panel detail-panel" role="complementary" aria-label="Account research side panel">
          <div className="panel-heading"><div><div className="section-kicker">AI account research</div><h2>{selectedAccount.name}</h2><p>{selectedAccount.domain} · {selectedAccount.industry || "Industry not set"}</p><label className="priority-picker">Priority <select value={selectedAccount.priority || "normal"} onChange={async event => { const value = event.target.value as "low"|"normal"|"high"|"critical"; setSelectedAccount({...selectedAccount,priority:value}); setAccounts(rows => rows.map(row => row.id === selectedAccount.id ? {...row,priority:value} : row)); const response = await fetch(`${API}/api/v1/accounts/${selectedAccount.id}/priority`, {method:"PATCH",headers,body:JSON.stringify({priority:value})}); if (!response.ok) { setError("Could not update account priority"); void loadAccounts(); } else setNotice("Account priority updated."); }}><option value="low">Low</option><option value="normal">Normal</option><option value="high">High</option><option value="critical">Critical</option></select></label></div><button className="icon-button" aria-label="Close account panel" onClick={() => setSelectedAccount(null)}>×</button></div>
          <div className="research-brief">{researchJobStatus && <p className="research-job-state" role="status">Research status · {researchJobStatus}</p>}<h3>Company overview</h3><p>{String(researchBrief?.summary || `${selectedAccount.name} operates in ${selectedAccount.industry || "an unclassified industry"}. Review the evidence below before outreach.`)}</p><h3>Recent buying triggers</h3><ul>{selectedAccount.score_reasons?.length ? selectedAccount.score_reasons.map((reason, index) => <li key={`${reason.type}-${index}`}>{reason.evidence || reason.type} <span>+{reason.points} {reason.signal_id && <button type="button" className="text-action" onClick={() => void archiveSignal(reason.signal_id)}>Archive</button>}</span></li>) : <li>No buying signals have been recorded yet.</li>}</ul><h3>Potential pain points</h3><ul>{Array.isArray(researchBrief?.potential_pain_points) && researchBrief.potential_pain_points.length ? (researchBrief.potential_pain_points as string[]).map((point, index) => <li key={index}>{point}</li>) : <li>Research has not identified validated pain points yet.</li>}</ul><h3>Research caveats</h3><p>{Array.isArray(researchBrief?.caveats) ? (researchBrief.caveats as string[]).join(" ") : "Use only verified evidence before personalizing outreach."}</p><h3>Recommended outreach angle</h3><p>Lead with a business outcome connected to a verified signal. Avoid presenting inferred pain points as confirmed facts.</p><div className="research-actions"><button className="tonal-button" type="button" onClick={() => void navigator.clipboard?.writeText(`${selectedAccount.name}\n${selectedAccount.score_reasons.map(reason => reason.evidence).join("\n")}`)}>Copy brief</button><button className="tonal-button" type="button" disabled={actionBusy} onClick={() => void runAccountAction("research")}>Regenerate</button><button className="tonal-button" type="button" disabled={actionBusy} onClick={() => void pushHubSpotNote()}>Push note to HubSpot</button></div></div><form className="signal-form" onSubmit={addSignal}>
            <label>Buying signal type<select value={signalType} onChange={e => setSignalType(e.target.value)}><option value="security_hiring">Security hiring</option><option value="compliance_requirement">Compliance requirement</option><option value="enterprise_expansion">Enterprise expansion</option><option value="funding">Funding</option><option value="icp_fit">ICP fit</option><option value="other">Other</option></select></label>
            <label className="wide-field">Evidence description<textarea required minLength={5} maxLength={4000} value={signalDescription} onChange={e => setSignalDescription(e.target.value)} placeholder="Describe the observable buying signal…" /></label>
            <label className="wide-field">Evidence URL (optional)<input type="url" value={signalSource} onChange={e => setSignalSource(e.target.value)} placeholder="https://source.example/article" /></label>
            <div className="form-actions"><button className="primary-button" disabled={actionBusy || !signalDescription.trim()} type="submit">{actionBusy ? "Saving…" : "Add signal and rescore"}</button><button className="tonal-button" type="button" disabled={actionBusy} onClick={() => void runAccountAction("research")}>Generate AI research brief</button><button className="tonal-button" type="button" disabled={actionBusy} onClick={() => void runAccountAction("hubspot-sync")}>Sync to HubSpot</button></div>
          </form>
        </section>}
        <section className="surface-panel create-panel" id="create-account">
          <div className="panel-heading"><div><h2>Create an account</h2><p>Add a company to your revenue workspace.</p></div></div>
          <form className="account-form" onSubmit={createAccount}>
            <label>Company name<input required maxLength={240} value={name} onChange={e => setName(e.target.value)} placeholder="Acme Security" /></label>
            <label>Company domain<input required maxLength={255} value={domain} onChange={e => setDomain(e.target.value)} placeholder="acme.com" /></label>
            <label>Industry<input maxLength={120} value={industry} onChange={e => setIndustry(e.target.value)} placeholder="B2B SaaS" /></label>
            <label>Company tier<select value={accountTier} onChange={e => setAccountTier(e.target.value as "unknown"|"smb"|"mid_market"|"enterprise")}><option value="unknown">Not classified</option><option value="smb">SMB</option><option value="mid_market">Mid-market</option><option value="enterprise">Enterprise</option></select></label>
            <button className="primary-button" disabled={saving} type="submit">{saving ? "Creating…" : "Create account"}</button>
          </form>
        </section>
        <section className="surface-panel integration-panel" id="integrations-panel"><div className="panel-heading"><div><h2>Connected tools</h2><p>Bring CRM context into your account workflow.</p></div></div><div className="integration-row"><div className="hubspot-mark">H</div><span><strong>HubSpot</strong><small>CRM company sync · {hubspotStatus.webhook_secret_configured ? "Webhook signature verification enabled" : "Webhook signature secret not configured"}</small></span><span className="connection-state">{hubspotStatus.configured ? "Connected" : "Setup required"}</span></div></section>
        <p className="footer-note">SignalFlow AI · GTM intelligence workspace · Demo data is synthetic</p></div></section>
      <aside className="companion-bar" aria-label="Companion shortcuts"><button aria-label="Calendar" title="Calendar" aria-expanded={utilityPanel === "calendar"} onClick={() => setUtilityPanel(utilityPanel === "calendar" ? null : "calendar")}>▦</button><button aria-label="Notes" title="Notes" aria-expanded={utilityPanel === "notes"} onClick={() => setUtilityPanel(utilityPanel === "notes" ? null : "notes")}>▧</button><button aria-label="Tasks" title="Tasks" aria-expanded={utilityPanel === "tasks"} onClick={() => setUtilityPanel(utilityPanel === "tasks" ? null : "tasks")}>☑</button><button aria-label="Contacts" title="Contacts" aria-expanded={utilityPanel === "contacts"} onClick={() => setUtilityPanel(utilityPanel === "contacts" ? null : "contacts")}>♙</button></aside>
    </div>
    {utilityPanel && <div className="utility-scrim" onClick={() => setUtilityPanel(null)}><section className="utility-panel" role="dialog" aria-modal="true" aria-labelledby="utility-title" onClick={event => event.stopPropagation()} onKeyDown={event => {
      if (event.key !== "Tab") return;
      const focusable = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('button:not([disabled]),input:not([disabled]),textarea:not([disabled]),select:not([disabled]),a[href]'));
      if (!focusable.length) return;
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }}>
      <div className="panel-heading"><div><div className="section-kicker">SignalFlow AI</div><h2 id="utility-title">{{help:"Help & shortcuts",settings:"Workspace settings",apps:"Workspace apps",calendar:"Calendar",notes:"Workspace notes",tasks:"Tasks",contacts:"Contacts",audit:"Audit logs",duplicates:"Duplicate review queue",webhooks:"Webhook deliveries",research:"AI research briefs"}[utilityPanel]}</h2></div><button className="icon-button" aria-label="Close panel" autoFocus onClick={() => setUtilityPanel(null)}>×</button></div>
      {utilityPanel === "help" && <div className="utility-content"><p>Use SignalFlow AI to prioritize target accounts from explainable buying signals.</p><h3>Keyboard shortcuts</h3><p><kbd>/</kbd> Focus account search</p><p><kbd>Esc</kbd> Close the account or utility panel</p><p><kbd>j</kbd> / <kbd>k</kbd> Move through account rows</p><p><kbd>x</kbd> Select the focused account</p><p><kbd>?</kbd> Open this shortcut guide</p><h3>Getting started</h3><ol><li>Create an account with a company domain.</li><li>Open Manage to add evidence-backed buying signals.</li><li>Review the recalculated lead score and reasons.</li></ol><p className="muted">Demo data is synthetic. Connect production identity and CRM credentials before using customer data.</p></div>}
      {utilityPanel === "settings" && <div className="utility-content"><h3>Appearance</h3><div className="setting-row"><span>Color theme</span><button className="tonal-button" onClick={toggleTheme}>{darkMode ? "Switch to light" : "Switch to dark"}</button></div><h3>Environment</h3><div className="setting-row"><span>API endpoint</span><code>{API}</code></div><div className="setting-row"><span>Workspace mode</span><strong>Demo tenant</strong></div><div className="setting-row"><span>Account records loaded</span><strong>{accounts.length}</strong></div><p className="muted">Tenant identity is supplied by the demo configuration. Do not expose demo tenant headers in a public production deployment.</p><button className="tonal-button" onClick={() => { setUtilityPanel(null); void loadAccounts(); }}>Refresh workspace data</button></div>}
      {utilityPanel === "apps" && <div className="utility-content app-launcher"><button onClick={() => { setUtilityPanel(null); document.getElementById("accounts-panel")?.scrollIntoView({behavior:"smooth"}); }}>▤ <span><strong>Accounts</strong><small>Prioritized company records</small></span></button><button onClick={() => { setUtilityPanel(null); document.getElementById("integrations-panel")?.scrollIntoView({behavior:"smooth"}); }}>⇄ <span><strong>Integrations</strong><small>CRM connection status</small></span></button><button onClick={() => { setUtilityPanel(null); document.getElementById("create-account")?.scrollIntoView({behavior:"smooth"}); }}>＋ <span><strong>Create account</strong><small>Add a target company</small></span></button></div>}
      {(utilityPanel === "audit" || utilityPanel === "duplicates" || utilityPanel === "webhooks" || utilityPanel === "research") && <div className="utility-content data-inspector">
        {panelData.length === 0 && <p className="muted">No records found, or the service is still loading.</p>}
        {utilityPanel === "duplicates" && panelData.map((item, index) => { const pair = item as {source:{id:string;name:string;domain:string};target:{id:string;name:string;domain:string};similarity:number}; return <article className="inspector-row" key={index}><strong>{pair.source.name} ↔ {pair.target.name}</strong><small>{pair.source.domain} · {pair.target.domain} · {Math.round(pair.similarity*100)}% name similarity</small><button className="tonal-button" onClick={() => void mergeAccounts(pair.source.id,pair.target.id)}>Merge into {pair.target.name}</button></article>; })}
        {utilityPanel === "audit" && panelData.map((item,index) => { const row = item as {id:string;action:string;actor:string;resource_id:string;created_at:string;details:Record<string,unknown>}; return <article className="inspector-row" key={row.id}><strong>{row.action}</strong><small>{row.actor} · {row.resource_id}</small><code>{row.created_at}</code><pre>{JSON.stringify(row.details,null,2)}</pre></article>; })}
        {utilityPanel === "research" && panelData.map((item,index) => { const row = item as {id:string;account_id:string;status:string;created_at:string;result?:{summary?:string};error?:string}; return <article className="inspector-row" key={row.id}><strong>Research · {row.status}</strong><small>Account {row.account_id} · {row.created_at}</small>{row.result?.summary && <p>{row.result.summary}</p>}{row.error && <p className="error-copy">{row.error}</p>}</article>; })}
        {utilityPanel === "webhooks" && panelData.map((item,index) => { const row = item as {id:string;event_id:string;event_type:string;received_at:string;payload:unknown}; return <details className="inspector-row" key={row.id}><summary><strong>{row.event_type}</strong><small>{row.event_id} · {row.received_at}</small></summary><pre>{JSON.stringify(row.payload,null,2)}</pre></details>; })}
      </div>}
      {utilityPanel === "calendar" && <div className="utility-content"><p>There are no scheduled GTM activities in this demo workspace yet.</p><p className="muted">Connect a calendar integration to view meetings and account events here.</p></div>}
      {utilityPanel === "notes" && <div className="utility-content"><label className="utility-label">Personal workspace note<textarea value={notes} onChange={event => setNotes(event.target.value)} rows={7} placeholder="Capture a reminder for this session…" /></label><p className="muted">Notes remain in this open browser session and are not saved to the server.</p></div>}
      {utilityPanel === "tasks" && <div className="utility-content"><label className="task-check"><input type="checkbox" checked={taskDone} onChange={event => setTaskDone(event.target.checked)} /> Review high-intent accounts</label><p className="muted">A sample task to demonstrate the workspace task panel. Task state is local to this session.</p></div>}
      {utilityPanel === "contacts" && <div className="utility-content"><p>Contacts are not yet enabled in this demo.</p><p className="muted">Contact records will be available after a CRM contacts integration is configured.</p></div>}
    </section></div>}
    {!online && <div className="offline-banner" role="status"><span className="material-symbols-outlined">cloud_off</span>You are offline. Queued account changes will sync when you reconnect.</div>}
    {notice && <div className="snackbar" role="status"><span className="snackbar-check">✓</span>{notice}<button onClick={() => undoArchiveId ? void undoArchive() : setNotice("")} aria-label={undoArchiveId ? "Undo signal archive" : "Dismiss notification"}>{undoArchiveId ? "Undo" : "Dismiss"}</button></div>}
  </main>;
}
