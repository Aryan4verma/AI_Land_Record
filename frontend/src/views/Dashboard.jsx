import { useEffect, useRef, useState } from "react";
import EmptyState from "../components/EmptyState.jsx";
import ErrorState from "../components/ErrorState.jsx";
import { timeAgo } from "../components/format.js";
import { friendlyMessage, requestIdOf } from "../components/errors.js";
import Skeleton from "../components/Skeleton.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { getUser, getDashboardSummary, getDashboardValidation, searchRecords } from "../api/client";
import { isOperator } from "../components/roles.js";
import { statusLabel, statusTone } from "../api/types";
import "../styles/dashboard.css";

function sumCounts(map) {
  return Object.values(map || {}).reduce((total, value) => total + (Number(value) || 0), 0);
}

function countOf(map, key) {
  return Number(map && map[key]) || 0;
}

function displayValue(value) {
  return value === null || value === undefined || value === "" ? "—" : value;
}

function recordLabel(record) {
  return record.survey_number || record.khasra_number || record.khata_number || "Unidentified parcel";
}

function recordAction(record) {
  const status = (record.status || "").toUpperCase();
  if (status === "REVIEW_REQUIRED") return "Review dossier";
  if (status === "READY_FOR_APPROVAL") return "Open for approval";
  if (status === "APPROVED") return "View approved record";
  return "Open dossier";
}

function StatTile({ className = "", label, value, detail, badge, children }) {
  return (
    <section className={`dashboard-stat-tile ${className}`}>
      <div className="dashboard-stat-head"><span>{label}</span>{badge && <b>{badge}</b>}</div>
      <div className="dashboard-stat-value">{value}<small>{detail}</small></div>
      {children && <div className="dashboard-stat-foot">{children}</div>}
    </section>
  );
}

function OperationalRow({ record }) {
  const owner = record.owner_name || "Owner not extracted";
  const location = [record.village, record.tehsil].filter(Boolean).join(" · ");
  const status = record.status || "";
  return (
    <tr>
      <td className="dashboard-select-cell"><input type="checkbox" aria-label={`Select ${recordLabel(record)}`} /></td>
      <td><a className="dashboard-parcel" href={`#/record/${record.id}`}>{recordLabel(record)}</a><code>{record.id}</code></td>
      <td><strong>{owner}</strong><small>{record.father_or_spouse_name || "Owner relationship not extracted"}</small></td>
      <td><span>{location || "Location not extracted"}</span><small>{record.district || "District not extracted"}</small></td>
      <td><StatusBadge tone={statusTone(status)}>{statusLabel(status) || "Status unavailable"}</StatusBadge><small>{record.land_classification || "Classification not extracted"}</small></td>
      <td><span>{timeAgo(record.updated_at || record.created_at)}</span><small className="tnum">Record {String(record.id).slice(0, 12)}</small></td>
      <td className="dashboard-action-cell"><a href={`#/record/${record.id}`}>{recordAction(record)} <span aria-hidden="true">↗</span></a></td>
    </tr>
  );
}

/** Stitch Operator Dashboard on live backend aggregates. Counts and rows come
 * from dashboard/records APIs. Stitch-only GIS geometry and demo metrics are
 * not invented when the current API does not provide them.
 */
export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [errorRef, setErrorRef] = useState("");
  const [dirty, setDirty] = useState(0);
  const abortRef = useRef(null);

  function isAbort(err) { return err instanceof DOMException && err.name === "AbortError"; }

  useEffect(() => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const signal = controller.signal;
    const opts = { signal };
    Promise.all([getDashboardSummary(opts), getDashboardValidation(opts), searchRecords({ page: 1, limit: 8 }, opts)])
      .then(([summary, validation, records]) => {
        if (signal.aborted) return;
        setData({ summary, validation, records, syncedAt: new Date() });
      })
      .catch((err) => {
        if (isAbort(err) || signal.aborted) return;
        setError(friendlyMessage(err));
        setErrorRef(requestIdOf(err));
      });
    return () => controller.abort();
  }, [dirty]);

  if (error && !data) {
    return (
      <div className="dashboard-screen">
        <div className="dashboard-commandbar"><div><span className="dashboard-kicker">SIH-2026 / PS-26018</span><h1>Cadastral Operations &amp; Verification Dashboard</h1></div></div>
        <div className="panel"><ErrorState title="Dashboard unavailable" message={error} requestId={errorRef || undefined} onRetry={() => { setError(""); setErrorRef(""); setData(null); setDirty((n) => n + 1); }} /></div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="dashboard-screen">
        <div className="dashboard-commandbar"><div><span className="dashboard-kicker">SIH-2026 / PS-26018</span><h1>Cadastral Operations &amp; Verification Dashboard</h1><p>Loading the current operational aggregates.</p></div></div>
        <div className="dashboard-stat-grid" aria-hidden="true">{[0, 1, 2, 3, 4].map((i) => <div className="dashboard-stat-tile" key={i}><Skeleton lines={3} /></div>)}</div>
        <div className="dashboard-panel"><Skeleton lines={8} /></div>
      </div>
    );
  }

  const { summary, validation, records, syncedAt } = data;
  const operator = isOperator(getUser());
  const recordsTotal = sumCounts(summary.records_by_status);
  const approved = countOf(summary.records_by_status, "APPROVED");
  const ready = countOf(summary.records_by_status, "READY_FOR_APPROVAL");
  const issuesTotal = sumCounts(validation.issues_by_severity);
  const pendingReview = Number(summary.open_reviews) || 0;
  const processing = countOf(summary.documents_by_status, "PROCESSING");
  const uploaded = countOf(summary.documents_by_status, "UPLOADED");
  const avgConf = summary.average_confidence === null || summary.average_confidence === undefined ? "—" : `${Math.round(summary.average_confidence * 100)}%`;
  const firstRecord = records.items[0] || null;
  const warningIssues = countOf(validation.issues_by_severity, "WARNING");
  const criticalIssues = Math.max(0, issuesTotal - warningIssues);

  return (
    <div className="dashboard-screen">
      <section className="dashboard-commandbar">
        <div className="dashboard-command-copy">
          <div className="dashboard-command-meta"><span className="dashboard-kicker">SIH-2026 / PS-26018</span><span>•</span><span>STATE CADASTRAL INTELLIGENCE CONSOLE</span><span>•</span><strong>AI Proposes • Rules Validate • Humans Decide</strong></div>
          <h1>Cadastral Operations &amp; Verification Dashboard</h1>
          <p>Real-time deed ingestion, cadastral validation, and statutory review queue for the current workspace.</p>
        </div>
        <div className="dashboard-command-actions">
          <a href="#/records" className="dashboard-secondary-action"><span aria-hidden="true">⌕</span>Search Records</a>
          {operator && <a href="#/reviews" className="dashboard-secondary-action"><span aria-hidden="true">☷</span>Review Queue <b>{pendingReview}</b></a>}
          {operator && <a href="#/upload" className="dashboard-primary-action"><span aria-hidden="true">↑</span>Upload Document</a>}
        </div>
      </section>

      <div className="dashboard-stat-grid">
        <StatTile className="dashboard-stat-review" label="Pending Review" badge="Action required" value={pendingReview} detail="records in queue"><span>Open reviews</span><strong>{pendingReview}</strong><span>Validation issues</span><strong>{issuesTotal}</strong></StatTile>
        <StatTile className="dashboard-stat-failed" label="Validation Issues" badge="Attention" value={String(issuesTotal).padStart(2, "0")} detail="open findings"><span>Critical / blocking</span><strong>{criticalIssues}</strong><span>Warnings</span><strong>{warningIssues}</strong></StatTile>
        <StatTile className="dashboard-stat-ready" label="Ready for Approval" badge="Backend status" value={ready} detail="records">{operator && <a href="#/records?status=READY_FOR_APPROVAL">Open ready records</a>}</StatTile>
        <StatTile className="dashboard-stat-neutral" label="Documents Ingested" badge={avgConf === "—" ? undefined : `${avgConf} avg`} value={summary.documents_total} detail="documents"><span>Processing</span><strong>{processing}</strong><span>Awaiting processing</span><strong>{uploaded}</strong></StatTile>
        <StatTile className="dashboard-stat-approved" label="Approved Records" badge="Backend status" value={approved} detail={`of ${recordsTotal} records`}><a href="#/records?status=APPROVED">Browse approved records</a></StatTile>
      </div>

      <section className="dashboard-panel dashboard-operational-panel">
        <div className="dashboard-filterbar"><div className="dashboard-tabs"><span className="dashboard-tab-active">ALL OPERATIONAL RECORDS <b>{records.total}</b></span><span>NEEDS ATTENTION <b>{pendingReview}</b></span><span>HIGH SIGNAL <b>{criticalIssues}</b></span></div><div className="dashboard-filter-summary"><span>Updated {timeAgo(syncedAt.toISOString())}</span><span>•</span><span>Page {records.page} / {Math.max(1, Math.ceil(records.total / records.limit))}</span></div></div>
        <div className={`dashboard-alert-strip ${issuesTotal > 0 ? "is-alert" : ""}`}><span aria-hidden="true">{issuesTotal > 0 ? "⚠" : "✓"}</span><span>{issuesTotal > 0 ? `${issuesTotal} validation finding${issuesTotal === 1 ? "" : "s"} require review before statutory approval.` : "No open validation findings are reported by the backend."}</span><a href="#/records">Open records ↗</a></div>
        {records.items.length === 0 ? <EmptyState title="No operational records">Upload a document to start the digitization pipeline.</EmptyState> : (
          <div className="dashboard-table-scroll"><table className="dashboard-ops-table"><thead><tr><th scope="col"><input type="checkbox" aria-label="Select visible records" /></th><th scope="col">Survey / Khasra<br />or record ID</th><th scope="col">Owner /<br />Khathedars</th><th scope="col">Village &amp;<br />Taluka</th><th scope="col">Statutory status<br />&amp; classification</th><th scope="col">Updated</th><th scope="col">Adjudication action</th></tr></thead><tbody>{records.items.map((record) => <OperationalRow key={record.id} record={record} />)}</tbody></table></div>
        )}
        <div className="dashboard-table-footer"><span>Showing {records.items.length} of {records.total} records</span><span>{records.items.length > 0 ? "Select a row to open its evidence dossier." : ""}</span><a href="#/records">Open full records directory →</a></div>
      </section>

      <div className="dashboard-lower-grid">
        <section className="dashboard-panel dashboard-dossier-panel"><div className="dashboard-panel-title"><div><span className="dashboard-panel-eyebrow">Active case dossier</span><h2>{firstRecord ? recordLabel(firstRecord) : "No active case"}</h2></div>{firstRecord && <StatusBadge tone={statusTone(firstRecord.status)}>{statusLabel(firstRecord.status)}</StatusBadge>}</div>{firstRecord ? <><div className="dashboard-dossier-target"><span>Current cadastral target</span><strong>{recordLabel(firstRecord)} — {displayValue(firstRecord.village || firstRecord.tehsil || firstRecord.district)}</strong><code>Record ID: {firstRecord.id}</code></div><div className="dashboard-dossier-diagnostic"><span>Record data available</span><strong>{[firstRecord.owner_name, firstRecord.area, firstRecord.land_classification].filter(Boolean).length} populated key attributes</strong><p>Open the dossier for extracted evidence, deterministic validation findings, and the authoritative workflow actions.</p></div><a className="dashboard-dossier-action" href={`#/record/${firstRecord.id}`}>Open evidence dossier →</a></> : <EmptyState title="No active case">The backend returned no records for the current workspace.</EmptyState>}</section>
        <section className="dashboard-panel dashboard-gis-panel"><div className="dashboard-panel-title"><div><span className="dashboard-panel-eyebrow">Cadastral vector overlay</span><h2>GIS sync area</h2></div><span className="dashboard-gis-status">API geometry unavailable</span></div><div className="dashboard-gis-canvas" aria-label="Cadastral GIS overlay unavailable"><div className="dashboard-gis-grid" aria-hidden="true" /><div className="dashboard-gis-empty"><span aria-hidden="true">⌖</span><strong>No geometry returned</strong><p>The current dashboard contract provides record and validation data, but no parcel polygon coordinates.</p></div></div><div className="dashboard-gis-footer"><span>Source: current records API</span><span>Raw coordinates preserved when supplied</span></div></section>
      </div>
    </div>
  );
}
