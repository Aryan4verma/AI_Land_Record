import { useEffect, useState } from "react";
import Alert from "../components/Alert.jsx";
import AuditTimeline from "../components/AuditTimeline.jsx";
import Button from "../components/Button.jsx";
import EmptyState from "../components/EmptyState.jsx";
import ErrorState from "../components/ErrorState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import Select from "../components/Select.jsx";
import Skeleton from "../components/Skeleton.jsx";
import StatCard from "../components/StatCard.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { describeAuditEvent } from "../components/audit.js";
import { loadRecordPage } from "../components/recordLoad.js";
import { getRecord, getRecordAudit } from "../api/client";
import { statusLabel, statusTone } from "../api/types";

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
    .sort((a, b) => {
      const cmp = (a.timestamp || "").localeCompare(b.timestamp || "");
      return order === "NEWEST" ? -cmp : cmp;
    });
  const corrections = events.filter((e) => e.title === "Field corrected").length;

  return (
    <div className="vstack">
      <PageHeader
        title="Audit trail"
        sub="Every recorded event for this record, oldest to newest as stored."
        meta={
          <>
            <span>Record <code className="tnum">{record.id.slice(0, 8)}…</code></span>
            <StatusBadge tone={statusTone(record.status)}>{statusLabel(record.status)}</StatusBadge>
          </>
        }
        actions={
          <div className="review-top-actions">
            <a href={`#/record/${record.id}`}>Back to record</a>
            <Button variant="secondary" onClick={() => window.print()}>Print</Button>
          </div>
        }
      />

      <div className="stat-grid">
        <StatCard label="Document ID" value={docMeta ? `${docMeta.id.slice(0, 8)}…` : `${record.document_id.slice(0, 8)}…`} sub={docMeta && docMeta.file_name ? docMeta.file_name : "Source document"} />
        <StatCard label="Document type" value={(docMeta && docMeta.document_type) || "—"} sub={`Status: ${record.status}`} />
        <StatCard label="Last updated" value={record.updated_at ? new Date(record.updated_at).toLocaleDateString() : "—"} sub={record.updated_at ? new Date(record.updated_at).toLocaleTimeString() : "No updates yet"} />
        <StatCard label="Total events" value={String(events.length)} sub={`${corrections} manual correction(s)`} />
      </div>

      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Events</h2>
            <p className="panel-sub">Read-only. Corrections show original → updated values from the stored rows.</p>
          </div>
        </div>
        <form className="filterbar" onSubmit={(e) => e.preventDefault()}>
          <Select label="Source" id="audit-source" value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="">All sources</option>
            <option value="Officer">Reviewer &amp; officer</option>
            <option value="Pipeline">System / pipeline</option>
          </Select>
          <Select label="Sort order" id="audit-order" value={order} onChange={(e) => setOrder(e.target.value)}>
            <option value="NEWEST">Newest first</option>
            <option value="OLDEST">Oldest first</option>
          </Select>
        </form>
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
        {!auditForbidden && visible.length > 0 && <AuditTimeline events={visible} />}
        {!auditForbidden && events.length > 0 && (
          <Alert tone="info" title="Append-only">
            Audit rows are never edited or deleted through any API; this screen has no mutating actions by design.
          </Alert>
        )}
      </div>
    </div>
  );
}
