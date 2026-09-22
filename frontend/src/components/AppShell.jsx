import { isOperator } from "./roles.js";
import { useEffect, useRef, useState } from "react";
import { getHealthAi } from "../api/client";
import "../styles/shell.css";

const NAV = [
  {
    section: "Cadastral Operations",
    items: [
      { key: "dashboard", label: "Dashboard", href: "#/", icon: "grid" },
      { key: "documents", label: "Documents", href: "#/records", icon: "folder" },
      { key: "upload", label: "Upload", href: "#/upload", icon: "upload", operatorOnly: true },
      { key: "reviews", label: "Review Queue", href: "#/reviews", icon: "review", operatorOnly: true },
      { key: "analytics", label: "Analytics", href: "#/analytics", icon: "chart" },
      { key: "audit", label: "Audit Trail", href: "#/audit", icon: "history" },
    ],
  },
  {
    section: "Institutional Core",
    items: [
      { key: "settings", label: "Settings", href: "#/settings", icon: "settings" },
      { key: "help", label: "Help", href: "#/help", icon: "help" },
    ],
  },
];

function Icon({ name }) {
  const paths = {
    grid: "M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z",
    folder: "M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z",
    upload: "M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5",
    review: "M9 12.75L11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 01-1.043 3.296 3.745 3.745 0 01-3.296 1.043A3.745 3.745 0 0112 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 01-3.296-1.043 3.745 3.745 0 01-1.043-3.296A3.745 3.745 0 013 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 011.043-3.296 3.746 3.746 0 013.296-1.043A3.746 3.746 0 0112 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 013.296 1.043 3.746 3.746 0 011.043 3.296A3.745 3.745 0 0121 12z",
    chart: "M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z",
    history: "M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z",
    settings: "M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.28zM15 12a3 3 0 11-6 0 3 3 0 016 0z",
    help: "M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  };
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d={paths[name] || paths.grid} />
    </svg>
  );
}

/** Authenticated application shell — Stitch shell topology. Sidebar sections
 * match the Stitch nav exactly; only implemented routes resolve to views
 * (the rest land on an honest placeholder — never fake data).
 */
export default function AppShell({ active, user, onLogout, crumb, children }) {
  // Read-only users are not offered destinations whose every action the
  // backend would refuse. This is presentation only — RBAC stays server-side.
  const nav = NAV
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => !item.operatorOnly || isOperator(user)),
    }))
    .filter((group) => group.items.length > 0);
  const [drawer, setDrawer] = useState(false);
  const [engine, setEngine] = useState("");
  const abortRef = useRef(null);

  useEffect(() => {
    // One shell-level status read (public /health/ai, no secrets). Failure
    // hides the pill — never blocks the workspace.
    const controller = new AbortController();
    abortRef.current = controller;
    getHealthAi({ signal: controller.signal })
      .then((h) => {
        if (controller.signal.aborted) return;
        if (h && h.ai === "configured") {
          setEngine(`${h.provider || "ai"}${h.model ? ` • ${h.model}` : ""}`);
        }
      })
      .catch(() => {});
    return () => controller.abort();
  }, []);

  const initial = (user && user.email ? user.email : "?").slice(0, 1).toUpperCase();

  return (
    <div className="shell">
      {drawer && <button type="button" className="sidebar-scrim" aria-label="Close navigation" onClick={() => setDrawer(false)} />}
      <aside className={`sidebar${drawer ? " open" : ""}`} aria-label="Primary">
        <div>
          <div className="sidebar-brand">
            <div className="sidebar-brand-row">
              <span className="sidebar-brand-name">BHOOMI INTEL</span>
              <span className="sidebar-ps-chip">PS-26018</span>
            </div>
            <div className="sidebar-brand-sub">Intelligent Cadastral Extraction</div>
          </div>
          <hr className="sidebar-rule" />
          <nav className="sidebar-nav">
            {nav.map((group) => (
              <div key={group.section}>
                <span className="sidebar-section">{group.section}</span>
                {group.items.map((item) => (
                  <a
                    key={item.key}
                    href={item.href}
                    className={`sidebar-link${active === item.key ? " active" : ""}`}
                    aria-current={active === item.key ? "page" : undefined}
                    onClick={() => setDrawer(false)}
                  >
                    <Icon name={item.icon} />
                    {item.label}
                  </a>
                ))}
              </div>
            ))}
          </nav>
        </div>
        <div className="sidebar-user">
          <span className="sidebar-avatar" aria-hidden="true">{initial}</span>
          <div className="sidebar-user-meta">
            <div className="sidebar-user-email">{user ? user.email : ""}</div>
            <div className="sidebar-user-role">{user ? user.role : ""}</div>
          </div>
          <button type="button" className="sidebar-logout" onClick={onLogout}>Logout</button>
        </div>
      </aside>

      <div className="shell-main">
        <header className="topheader">
          <button type="button" className="hamburger" aria-label="Open navigation" onClick={() => setDrawer(true)}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path strokeLinecap="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>
          <div className="topheader-brand" aria-label="BHOOMI INTEL application">
            <span className="topheader-brand-mark" aria-hidden="true">◆</span>
            <span className="topheader-brand-copy"><strong>BHOOMI INTEL</strong><small>PS-26018 · Cadastral Intelligence</small></span>
          </div>
          <nav className="topheader-crumb" aria-label="Breadcrumb">{crumb}</nav>
          <div className="topheader-right">
            {engine && (
              <span className="health-pill" title="AI wiring reported by the backend">
                <span className="health-pill-dot" aria-hidden="true" />{engine}
              </span>
            )}
            <span className="topheader-user-context"><strong>{user?.name || user?.email || "Signed in"}</strong><small>{user?.role || "user"}</small></span>
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
