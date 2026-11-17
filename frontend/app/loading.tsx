export default function Loading() {
  return <main className="app-shell" aria-label="Loading SignalFlow AI">
    <header className="topbar"><div className="brand"><span className="brand-mark">S</span><span>SignalFlow <span className="brand-ai">AI</span></span></div><div className="global-search-wrap"><span className="search-icon">⌕</span><span className="loading-search-copy">Loading your workspace</span></div></header>
    <div className="loading-workspace"><aside className="loading-sidebar"><div className="loading-fab" /><div className="loading-nav" /><div className="loading-nav" /><div className="loading-nav" /><div className="loading-nav" /></aside><section className="loading-main"><div className="loading-title" /><div className="loading-subtitle" /><div className="loading-metrics"><i/><i/><i/></div><div className="loading-table"><i/><i/><i/><i/></div></section></div>
  </main>;
}
