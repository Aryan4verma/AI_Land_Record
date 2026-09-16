import { useEffect, useState } from "react";
import { getMe, getToken, getUser, logout as clientLogout, onSessionExpired, setUser } from "./api/client";
import Analytics from "./views/Analytics.jsx";
import AppShell from "./components/AppShell.jsx";
import ApprovedRecord from "./views/ApprovedRecord.jsx";
import AuthLanding from "./views/AuthLanding.jsx";
import Dashboard from "./views/Dashboard.jsx";
import DocumentExtraction from "./views/DocumentExtraction.jsx";
import DocumentProcessing from "./views/DocumentProcessing.jsx";
import RecordAudit from "./views/RecordAudit.jsx";
import Help from "./views/Help.jsx";
import Login from "./views/Login.jsx";
import Placeholder from "./views/Placeholder.jsx";
import Records from "./views/Records.jsx";
import RecordDetail from "./views/RecordDetail.jsx";
import Reviews from "./views/Reviews.jsx";
import Settings from "./views/Settings.jsx";
import SignUp from "./views/SignUp.jsx";
import Upload from "./views/Upload.jsx";

function route() {
  return window.location.hash || "#/";
}

const CRUMB_BASE = (
  <>
    <span>National Cadastre Portal</span>
    <span className="sep">/</span>
    <span>Adjudication Console</span>
    <span className="sep">/</span>
  </>
);

export default function App() {
  const [hash, setHash] = useState(route());
  const [user, setUserState] = useState(getUser());
  // False until the stored session (if any) is validated. Protected views
  // never mount — and never fire API calls — before this completes.
  const [authChecked, setAuthChecked] = useState(!getToken());

  useEffect(() => {
    const onChange = () => setHash(route());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  useEffect(() => {
    // Redirect here on session death. Guarded: setting the same hash does
    // not refire hashchange, so no redirect loop is possible.
    onSessionExpired(() => {
      setUserState(null);
      if (window.location.hash !== "#/login") window.location.hash = "#/login";
    });
    return () => onSessionExpired(null);
  }, []);

  useEffect(() => {
    // Session initialization: a stored token is only a claim until the
    // backend confirms it. Role display always comes from this response.
    if (!getToken()) return;
    getMe()
      .then((me) => {
        setUser(me);
        setUserState(me);
      })
      .catch((err) => {
        // An invalid/expired token is expected here: request() has already
        // cleared storage and redirected. Anything else is a real fault and
        // must not vanish — a silent catch here previously hid a
        // ReferenceError that stopped the session ever being restored.
        if (!(err && err.status)) console.error("session restore failed", err);
      })
      .finally(() => setAuthChecked(true));
  }, []);

  const authed = !!getToken() && authChecked;

  async function logout() {
    await clientLogout();
    setUserState(null);
    window.location.hash = "#/login";
  }

  // Full-bleed Stitch login: no shell chrome until authenticated.
  if (!!getToken() && !authChecked) {
    return <main><div className="card"><p>Checking session…</p></div></main>;
  }
  if (!authed || hash === "#/login" || hash === "#/auth" || hash === "#/sign-in") {
    // Unauthenticated entry lands on #/auth (Login or Sign in); #/login and
    // #/sign-in render their forms directly. All stay full-bleed.
    const entry = hash === "#/login" ? (
      <Login onLogin={(u) => { setUserState(u); window.location.hash = "#/"; }} />
    ) : hash === "#/sign-in" ? (
      <SignUp />
    ) : (
      <AuthLanding />
    );
    return <main>{entry}</main>;
  }

  let active = "dashboard";
  let crumb = <> {CRUMB_BASE} <strong>Dashboard</strong> </>;
  let view = <Dashboard />;
  if (hash === "#/records") {
    active = "documents";
    crumb = <> {CRUMB_BASE} <strong>Documents</strong> </>;
    view = <Records />;
  } else if (hash === "#/upload") {
    active = "upload";
    crumb = <> {CRUMB_BASE} <strong>Upload</strong> </>;
    view = <Upload />;
  } else if (hash === "#/reviews") {
    active = "reviews";
    crumb = <> {CRUMB_BASE} <strong>Review Queue</strong> </>;
    view = <Reviews />;
  } else if (hash.startsWith("#/record/") && hash.endsWith("/audit")) {
    active = "audit";
    crumb = <> {CRUMB_BASE} <strong>Audit Trail</strong> </>;
    view = <RecordAudit recordId={hash.slice("#/record/".length, -"/audit".length)} />;
  } else if (hash.startsWith("#/record/") && hash.endsWith("/approved")) {    active = "documents";
    crumb = <> {CRUMB_BASE} <strong>Approved Record</strong> </>;
    view = <ApprovedRecord recordId={hash.slice("#/record/".length, -"/approved".length)} />;
  } else if (hash.startsWith("#/record/")) {
    active = "documents";
    crumb = <> {CRUMB_BASE} <strong>Record</strong> </>;
    view = <RecordDetail recordId={hash.slice("#/record/".length)} />;
  } else if (hash.startsWith("#/document/") && hash.endsWith("/extract")) {
    active = "documents";
    crumb = <> {CRUMB_BASE} <strong>Extraction Result</strong> </>;
    view = <DocumentExtraction documentId={hash.slice("#/document/".length, -"/extract".length)} />;
  } else if (hash.startsWith("#/document/")) {
    active = "documents";
    crumb = <> {CRUMB_BASE} <strong>Processing</strong> </>;
    view = <DocumentProcessing documentId={hash.slice("#/document/".length)} />;
  } else if (hash === "#/analytics") {
    active = "analytics";
    crumb = <> {CRUMB_BASE} <strong>Analytics</strong> </>;
    view = <Analytics />;
  } else if (hash === "#/audit") {
    active = "audit";
    crumb = <> {CRUMB_BASE} <strong>Audit Trail</strong> </>;
    view = <Placeholder title="Audit Trail" note="Audit history is per-record: open any record from Documents, then follow View audit. No workspace-wide feed exists." />;
  } else if (hash === "#/settings") {
    active = "settings";
    crumb = <> {CRUMB_BASE} <strong>Settings</strong> </>;
    view = <Settings user={user} onLogout={logout} />;
  } else if (hash === "#/help") {
    active = "help";
    crumb = <> {CRUMB_BASE} <strong>Help</strong> </>;
    view = <Help />;
  }

  return (
    <AppShell active={active} user={user} onLogout={logout} crumb={crumb}>
      {view}
    </AppShell>
  );
}
