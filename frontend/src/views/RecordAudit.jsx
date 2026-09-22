import { useEffect, useState } from "react";
import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
import EmptyState from "../components/EmptyState.jsx";
import ErrorState from "../components/ErrorState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import Skeleton from "../components/Skeleton.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { describeAuditEvent } from "../components/audit.js";
import { loadRecordPage } from "../components/recordLoad.js";
import { downloadJson } from "../components/format.js";
import { getRecord, getRecordAudit } from "../api/client";
import { statusLabel, statusTone } from "../api/types";

function eventText(event) {
  const changes = (event.changes || []).flatMap((change) => [change.label, change.old, change.neu]);
  return [event.title, event.source, event.actor, event.description, ...changes].join(" ").toLowerCase();
}

function eventCategory(event) {
  return event.source === "Officer" ? "OFFICER" : "SYSTEM";
}

function displayChange(event, key) {
  const change = event.changes && event.changes[0];
  if (!change) return "—";
  return change[key];
}

/** Record audit trail (route #/record/:id/audit) — Stitch b1d6d3e8 timeline
 * on live per-record audit rows. The backend exposes no workspace-wide
 * feed, so this screen is record-scoped by design; the sidebar entry lands
 * on a picker state instead of fake global events. Summary, stats, source
 * filter, and sort all derive from the loaded rows. Read-only: no mutating
 * audit operation exists backend-side.
 */
export default function RecordAudit({ recordId }) {
  const [detail, setDetail] = useState(null);
  const [events, setEvents] = useState(null);
  const [auditForbidden, setAuditForbidden] = useState(false);
  const [error, setError] = useState("");
  const [errorRef, setErrorRef] = useState("");
  const [notFound, setNotFound] = useState(false);
  const [source, setSource] = useState("");
  const [order, setOrder] = useState("NEWEST");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("ALL");
  const [proofOpen, setProofOpen] = useState(false);
  const [dirty, setDirty] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const signal = controller.signal;
    // Decoupled orchestration (no task lookup needed here): the record
    // summary renders even when the audit call is forbidden for operators.
    const api = { getRecord, getRecordAudit };
    loadRecordPage(api, recordId, signal, { includeTasks: false }).then((res) => {
      if (res.aborted || signal.aborted) return;
      if (res.recordError) {
        setDetail(null);
        setNotFound(res.recordError.kind === "not-found");
        setError(res.recordError.message);
        setErrorRef(res.recordRequestId);
        return;
      }
      setDetail(res.record);
      setEvents(res.audit.map(describeAuditEvent));
      setAuditForbidden(res.auditState === "forbidden");
      setNotFound(false);
      setError(res.auditState === "error" ? res.auditError : "");
      setErrorRef(res.auditState === "error" ? res.auditRequestId : "");
      setErrorRef(res.auditState === "error" ? res.auditRequestId : "");
    });
    return () => controller.abort();
  }, [recordId, dirty]);

  if (error && !detail) {
    return (
      <div>
        <PageHeader title="Audit trail" />
        <div className="panel">
          <ErrorState
            title={notFound ? "Record not found" : "Audit unavailable"}
            message={error}
            requestId={errorRef || undefined}
            onRetry={() => { setError(""); setErrorRef(""); setDirty((n) => n + 1); }}
          />
          <p><a href="#/records">Back to documents</a></p>
        </div>
      </div>
    );
  }

  if (!detail || !events) {
    return (
      <div>
        <PageHeader title="Audit trail" />
        <div className="panel"><Skeleton lines={6} /></div>
      </div>
    );
  }

  const record = detail.record;
  const docMeta = detail.document;
  const visible = events
    .filter((e) => !source || e.source === source)
    .filter((e) => category === "ALL" || eventCategory(e) === category)
    .filter((e) => !query.trim() || eventText(e).includes(query.trim().toLowerCase()))
    .sort((a, b) => {
      const cmp = (a.timestamp || "").localeCompare(b.timestamp || "");
      return order === "NEWEST" ? -cmp : cmp;
    });
  const corrections = events.filter((e) => e.title === "Field corrected").length;
  const officerEvents = events.filter((e) => e.source === "Officer").length;
  const systemEvents = events.length - officerEvents;

  function exportAudit() {
    if (!events.length || auditForbidden) return;
    downloadJson(`audit-${record.id.slice(0, 8)}.json`, {
      record_id: record.id,
      exported_at: new Date().toISOString(),
      events,
    });
  }

  return (
    <div className="audit-screen">
      <section className="audit-pagehead">
        <div className="audit-breadcrumb">CONSOLE <span>/</span> COMPLIANCE &amp; GOVERNANCE <span>/</span> <strong>SOVEREIGN AUDIT TRAIL</strong></div>
        <div className="audit-pagehead-row">
          <div>
            <div className="audit-chain-badge"><span aria-hidden="true">●</span> APPEND-ONLY AUDIT CONTRACT · {auditForbidden ? "ACCESS RESTRICTED" : "EVENTS LOADED"}</div>
            <h1>Statutory Cadastral Audit Trail &amp; Mutation Log</h1>
            <p>Chronological record of machine processing, deterministic checks, and authorized officer actions for this land record.</p>
          </div>
          <div className="audit-page-actions">
            <Button variant="secondary" onClick={() => setProofOpen((value) => !value)}>{proofOpen ? "Hide integrity details" : "Integrity details"}</Button>
            <Button variant="primary" disabled={!events.length || auditForbidden} onClick={exportAudit}>Export audit JSON</Button>
          </div>
        </div>
      </section>

      <section className="audit-context-strip">
        <div className="audit-focus-record">
          <span className="audit-focus-label">RECORD IN FOCUS</span>
          <strong>{record.survey_number || `Record ${record.id.slice(0, 8)}…`}</strong>
          <span>{[record.village, record.tehsil, record.district].filter(Boolean).join(" · ") || "Jurisdiction not supplied"}</span>
          <code>{docMeta ? docMeta.file_name : "Source document unavailable"}</code>
        </div>
        <div className="audit-summary-metrics">
          <div><span>Total audited</span><strong>{events.length}</strong></div>
          <div><span>Officer events</span><strong className="is-accent">{officerEvents}</strong></div>
          <div><span>System events</span><strong>{systemEvents}</strong></div>
          <div><span>Corrections</span><strong className={corrections ? "is-warning" : ""}>{corrections}</strong></div>
        </div>
        <div className="audit-integrity-summary">
          <div><span>Storage posture</span><strong>Append-only</strong></div>
          <div><span>Proof metadata</span><strong>Not exposed by API</strong></div>
          <div><span>Record status</span><strong><StatusBadge tone={statusTone(record.status)}>{statusLabel(record.status)}</StatusBadge></strong></div>
        </div>
      </section>

      {proofOpen && (
        <section className="audit-proof-panel" aria-live="polite">
          <div><span className="audit-proof-icon" aria-hidden="true">◇</span><div><h2>Cryptographic proof metadata</h2><p>The current audit endpoint returns append-only event rows only. Hashes, signatures, Merkle branches, and chain tips are not part of the live API contract, so no proof value is displayed.</p></div></div>
          <StatusBadge tone="neutral">Not available</StatusBadge>
        </section>
      )}

      <section className="audit-controls panel">
        <div className="audit-search-wrap"><label htmlFor="audit-search">Filter by node, field, actor or citation</label><input id="audit-search" className="input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search this record's events…" /></div>
        <div className="audit-filter-tabs" role="tablist" aria-label="Audit event source">
          {[
            ["ALL", `All (${events.length})`],
            ["OFFICER", `Officer (${officerEvents})`],
            ["SYSTEM", `System / pipeline (${systemEvents})`],
          ].map(([value, label]) => <button key={value} type="button" className={category === value ? "is-active" : ""} onClick={() => setCategory(value)}>{label}</button>)}
        </div>
        <div className="audit-control-row">
          <label htmlFor="audit-source">Source</label>
          <select id="audit-source" className="input" value={source} onChange={(e) => setSource(e.target.value)}><option value="">All sources</option><option value="Officer">Reviewer &amp; officer</option><option value="Pipeline">System / pipeline</option></select>
          <label htmlFor="audit-order">Order</label>
          <select id="audit-order" className="input" value={order} onChange={(e) => setOrder(e.target.value)}><option value="NEWEST">Newest first</option><option value="OLDEST">Oldest first</option></select>
          <span className="audit-window">Window: <code>{record.updated_at ? new Date(record.updated_at).toLocaleDateString() : "Current record lifecycle"}</code></span>
        </div>
      </section>

      <section className="audit-ledger panel">
        <div className="audit-ledger-head"><div><h2>Cadastral ledger timeline</h2><p className="panel-sub">Read-only chronological view. Values and citations come from stored audit rows.</p></div><span>{visible.length} of {events.length} visible</span></div>
        {error && !auditForbidden && <ErrorState title="Refresh failed" message={error} requestId={errorRef || undefined} onRetry={() => { setError(""); setErrorRef(""); setDirty((n) => n + 1); }} />}
        {auditForbidden && (
          <Alert tone="info" title="Audit history needs the operator role">
            The record summary above stays visible, but the event trail is enforced
            server-side — switch to an operator account to inspect it.
          </Alert>
        )}
        {!auditForbidden && visible.length === 0 && (
          <EmptyState title={events.length === 0 ? "No audit events yet" : "No matching events"}>
            {events.length === 0
              ? "Events appear here as the pipeline and reviewers act on this record."
              : "No events match the current source filter."}
          </EmptyState>
        )}
        {!auditForbidden && visible.length > 0 && (
          <div className="audit-ledger-list">
            {visible.map((event) => (
              <article key={event.id} className={`audit-ledger-row audit-row-${event.source.toLowerCase()}`}>
                <div className="audit-ledger-time"><strong>{event.timestamp ? new Date(event.timestamp).toLocaleDateString() : "—"}</strong><code>{event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : "—"}</code><span>{event.id.slice(0, 10)}…</span></div>
                <div className="audit-ledger-actor"><strong>{event.actor}</strong><span>{event.source === "Officer" ? "Authorized officer" : "System / pipeline"}</span><StatusBadge tone={event.source === "Officer" ? "review" : "processing"}>{event.source}</StatusBadge></div>
                <div className="audit-ledger-event"><strong>{event.title}</strong><span>{event.description || "Recorded workflow event"}</span></div>
                <div className="audit-ledger-target"><span>Changed value</span><strong>{event.changes?.[0]?.label || "Record state"}</strong></div>
                <div className="audit-ledger-change"><span>{displayChange(event, "old")}</span><b aria-hidden="true">→</b><strong>{displayChange(event, "neu")}</strong></div>
                <div className="audit-ledger-citation"><span>Stored audit row</span><p>{event.description || "No additional citation supplied by the API."}</p></div>
              </article>
            ))}
          </div>
        )}
        {!auditForbidden && events.length > 0 && (
          <Alert tone="info" title="Append-only">
            Audit rows are never edited or deleted through any API; this screen has no mutating actions by design.
          </Alert>
        )}
      </section>

      <footer className="audit-footer-note"><span aria-hidden="true">⚖</span><strong>Statutory legal admissibility</strong><span>This application preserves the audit rows returned by the backend. Digital signatures and Merkle proofs require explicit backend support.</span><StatusBadge tone={statusTone(record.status)}>{statusLabel(record.status)}</StatusBadge><a href={`#/record/${record.id}`}>Back to record</a></footer>
    </div>
  );
}
