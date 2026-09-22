import { useEffect, useRef, useState } from "react";
import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
import { isOperator } from "../components/roles.js";
import EmptyState from "../components/EmptyState.jsx";
import ErrorState from "../components/ErrorState.jsx";
import ProcessingStepper from "../components/ProcessingStepper.jsx";
import Skeleton from "../components/Skeleton.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { createSubmitGuard, getDocument, getDocumentStatus, getExtraction, getUser, isProcessingTerminal, startProcessing } from "../api/client";
import { friendlyMessage, requestIdOf } from "../components/errors.js";
import { processingSteps, statusLabel, statusTone } from "../api/types";
import "../styles/processing.css";

/** Status poll cadence/cap (~5 min max; manual retry after that — the view
 * never retries silently or forever).
 */
const POLL_INTERVAL_MS = 3000;
const POLL_MAX_ATTEMPTS = 100;

const RETRYABLE = new Set(["UPLOADED", "VALIDATION_FAILED", "FAILED"]);

function formatExecutionTime(value) {
  if (!value) return "Not reported";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Not reported" : date.toLocaleString();
}

/** Document processing (route #/document/:id) — Stitch 3ddcbec7 stage list
 * driven by the aggregate backend document status. Per-stage timing, worker
 * telemetry, and event streams are not exposed by the backend and are
 * never rendered. Success continues to the record; failure offers one
 * explicit manual retry plus a way back.
 */
export default function DocumentProcessing({ documentId }) {
  const [doc, setDoc] = useState(null);
  const [status, setStatus] = useState("");
  const [statusInfo, setStatusInfo] = useState(null);
  const [recordId, setRecordId] = useState(null);
  const [extraction, setExtraction] = useState(null);
  const [error, setError] = useState("");
  const [errorRef, setErrorRef] = useState("");
  const [busy, setBusy] = useState(false);
  const [watching, setWatching] = useState(false);
  const [dirty, setDirty] = useState(0);
  const guard = useRef(null);
  if (!guard.current) guard.current = createSubmitGuard();
  const pollTimer = useRef(null);

  function isAbort(err) {
    return err instanceof DOMException && err.name === "AbortError";
  }

  function stopPolling() {
    if (pollTimer.current) {
      clearInterval(pollTimer.current);
      pollTimer.current = null;
    }
    setWatching(false);
  }

  // Single poller: one timer, stopped on terminal state, cap, or unmount.
  // Auth/network failures stop polling and surface — never spin silently.
  function poll(docId) {
    stopPolling();
    setWatching(true);
    let attempts = 0;
    pollTimer.current = setInterval(async () => {
      attempts += 1;
      try {
        const s = await getDocumentStatus(docId);
        setStatus(s.status);
        setStatusInfo(s);
        setDoc((d) => (d ? { ...d, processing_status: s.status } : d));
        if (isProcessingTerminal(s.status)) {
          stopPolling();
          if (!RETRYABLE.has(s.status)) resolveRecord(docId);
        } else if (attempts >= POLL_MAX_ATTEMPTS) {
          stopPolling();
          setError("Still processing after ~5 minutes. Retry the status check or come back later.");
        }
      } catch (err) {
        stopPolling();
        setError(friendlyMessage(err));
        setErrorRef(requestIdOf(err));
      }
    }, POLL_INTERVAL_MS);
  }

  async function resolveRecord(docId) {
    try {
      const ex = await getExtraction(docId);
      setExtraction(ex);
      setRecordId(ex.record_id || null);
    } catch {
      // No extracted record yet (e.g. terminal edge states) — the status
      // badge remains the source of truth; no link is rendered.
      setRecordId(null);
      setExtraction(null);
    }
  }

  const canProcess = isOperator(getUser());

  async function start() {
    if (!guard.current.tryAcquire()) return; // duplicate click: ignore
    setBusy(true);
    setError("");
    setErrorRef("");
    try {
      // POST /api/v1/documents/{id}/process — backend guards duplicates (409
      // while PROCESSING) and permits restarts from UPLOADED/FAILED states.
      await startProcessing(documentId);
      const s = await getDocumentStatus(documentId);
      setStatus(s.status);
      setStatusInfo(s);
      setRecordId(null);
      setExtraction(null);
      if (!isProcessingTerminal(s.status)) poll(documentId);
      else if (!RETRYABLE.has(s.status)) resolveRecord(documentId);
    } catch (err) {
      setError(friendlyMessage(err));
      setErrorRef(requestIdOf(err));
    } finally {
      guard.current.release();
      setBusy(false);
    }
  }

  useEffect(() => {
    const controller = new AbortController();
    const signal = controller.signal;
    setError("");
    setErrorRef("");
    setDoc(null);
    setStatusInfo(null);
    setRecordId(null);
    setExtraction(null);
    Promise.all([
      getDocument(documentId, { signal }),
      getDocumentStatus(documentId, { signal }),
    ])
      .then(([full, s]) => {
        if (signal.aborted) return;
        setDoc(full);
        setStatus(s.status);
        setStatusInfo(s);
        if (!isProcessingTerminal(s.status)) poll(full.id);
        else if (!RETRYABLE.has(s.status)) resolveRecord(full.id);
      })
      .catch((err) => {
        if (isAbort(err) || signal.aborted) return;
        setError(friendlyMessage(err));
        setErrorRef(requestIdOf(err));
      });
    return () => {
      controller.abort();
      if (pollTimer.current) {
        clearInterval(pollTimer.current);
        pollTimer.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId, dirty]);

  if (error && !doc) {
    return (
      <div className="processing-view">
        <section className="processing-dossier-head"><h1>Ingestion pipeline</h1><span className="processing-header-code">Document unavailable</span></section>
        <section className="panel processing-error-panel">
          <ErrorState title="Document unavailable" message={error} requestId={errorRef || undefined} onRetry={() => setDirty((n) => n + 1)} />
          <p><a href="#/records">Back to documents</a></p>
        </section>
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="processing-view">
        <section className="processing-dossier-head"><h1>Ingestion pipeline</h1><span className="processing-header-code">Loading document context</span></section>
        <section className="panel processing-loading-panel"><Skeleton lines={6} /></section>
      </div>
    );
  }

  const view = processingSteps(status, statusInfo?.error_code);
  const retryable = RETRYABLE.has(status) && !watching;
  const statusText = statusLabel(status) || "Unknown state";
  const currentStage = view.failed ? "exception" : view.terminal ? "review" : status === "UPLOADED" ? "staging" : "pipeline";
  const previewFields = extraction?.fields?.slice(0, 6) || [];
  const startedAt = statusInfo?.started_at;
  const completedAt = statusInfo?.completed_at;

  function trackClass(stage) {
    return currentStage === stage ? "is-active" : ((stage === "staging" && currentStage !== "staging") || (stage === "pipeline" && currentStage === "review") ? "is-complete" : "");
  }

  return (
    <div className="processing-view">
      <section className="processing-stage-track">
        <div className="processing-track-label"><span className="processing-track-icon" aria-hidden="true">⌘</span><div><span>Workflow staging track</span><strong>PS-26018 cadastral pipeline</strong></div></div>
        <div className="processing-track-steps" aria-label="Processing stages">
          <span className={`processing-track-step ${trackClass("staging")}`}><i />1. Document staging</span><b aria-hidden="true">→</b>
          <span className={`processing-track-step ${trackClass("pipeline")}`}>2. Statutory pipeline processing</span><b aria-hidden="true">→</b>
          <span className={`processing-track-step ${trackClass("review")}`}>3. Cadastral adjudication queue</span>
        </div>
      </section>

      <section className="processing-dossier-head">
        <div className="processing-dossier-context">
          <span className="processing-document-icon" aria-hidden="true">▧</span>
          <div>
            <div className="processing-context-tags"><span>DOCUMENT {doc.id.slice(0, 12)}…</span><span>{doc.file_type || "Unknown type"}</span><span>{status || doc.processing_status || "Unknown state"}</span></div>
            <h1>Cadastral ingestion pipeline: processing &amp; verification</h1>
            <p>Execution trace for <strong>{doc.file_name}</strong> · source document remains private.</p>
          </div>
        </div>
        <div className="processing-meta-grid">
          <div><span>Started at</span><strong>{formatExecutionTime(startedAt)}</strong></div>
          <div><span>Completed at</span><strong>{formatExecutionTime(completedAt)}</strong></div>
          <div><span>Job reference</span><strong>{statusInfo?.job_id ? `${statusInfo.job_id.slice(0, 12)}…` : "Not reported"}</strong></div>
          <div><span>Worker telemetry</span><strong>Not exposed</strong></div>
        </div>
      </section>

      <div className="processing-main-grid">
        <section className="panel processing-engine-panel">
          <header className="processing-section-header"><div><h2>Statutory processing engine architecture</h2><p>Sequential gates mapped from the persisted document status.</p></div><span className="processing-sequential-tag">{view.failed ? "EXCEPTION" : view.terminal ? "COMPLETE" : "SEQUENTIAL"}</span></header>
          {error && <Alert tone="error" title="Processing note">{error}</Alert>}
          <ProcessingStepper steps={view.steps} />
          <div className={`processing-outcome ${view.failed ? "is-failed" : view.terminal ? "is-complete" : ""}`}>
            <StatusBadge tone={statusTone(status)}>{statusText}</StatusBadge>
            <p>{view.failed ? "The backend recorded a failure state. No new progress is assumed; retry remains explicit and operator-authorized." : view.terminal ? "The backend has reached a terminal state. Continue to the extracted record when the record link is available." : status === "UPLOADED" ? "The document is stored and waiting for an operator to start processing." : "Processing is active. This page refreshes from the backend status endpoint."}</p>
            {view.failed && statusInfo?.error_message && <p className="processing-failure-reason"><strong>Reason:</strong> {statusInfo.error_message}</p>}
            <div className="processing-action-row">
              {retryable && <Button variant="primary" disabled={busy || !canProcess} onClick={start}>{busy ? "Starting…" : status === "UPLOADED" ? "Start pipeline processing" : "Retry processing"}</Button>}
              {recordId && <a className="processing-cta" href={`#/document/${doc.id}/extract`}>{status === "REVIEW_REQUIRED" ? "Open adjudication review →" : "View extraction result →"}</a>}
              <a href="#/records">Back to documents</a>
            </div>
          </div>
        </section>

        <aside className="processing-side-column">
          <section className="panel processing-entities-panel">
            <header className="processing-section-header"><div><h2>Extracted entity preview</h2><p>Persisted extraction fields only.</p></div><span className="processing-sequential-tag">{extraction ? `${extraction.fields.length} FIELDS` : "NOT LOADED"}</span></header>
            {previewFields.length > 0 ? (
              <div className="processing-entity-list">{previewFields.map((field) => <div className="processing-entity-row" key={field.field_name}><span>{field.field_name.replaceAll("_", " ")}</span><strong>{field.value === null || field.value === "" ? "Not found" : String(field.value)}</strong>{field.confidence !== null && field.confidence !== undefined && <small>{Math.round(field.confidence * 100)}%</small>}</div>)}</div>
            ) : (
              <EmptyState title="No extraction preview available">The persisted extraction response has not been loaded for this document state.</EmptyState>
            )}
            {recordId && <a className="processing-entity-link" href={`#/document/${doc.id}/extract`}>Open complete extraction ↗</a>}
          </section>

          <section className="processing-stream-panel" aria-label="Execution status stream">
            <header><span><i /> Live status &amp; execution stream</span><small>backend source</small></header>
            <div className="processing-stream">
              <div><time>STATUS</time><strong>{statusText}</strong><span>{watching ? "Polling active" : "Polling paused"}</span></div>
              {startedAt && <div><time>STARTED</time><strong>{formatExecutionTime(startedAt)}</strong><span>Persisted status timestamp</span></div>}
              {completedAt && <div><time>COMPLETED</time><strong>{formatExecutionTime(completedAt)}</strong><span>Persisted status timestamp</span></div>}
              {statusInfo?.error_code && <div className="is-error"><time>ERROR CODE</time><strong>{statusInfo.error_code}</strong><span>Safe backend diagnostic</span>{statusInfo.error_message && <small>{statusInfo.error_message}</small>}</div>}
              <p className="processing-stream-note">Per-stage events, percentages, node metrics, and raw provider logs are not exposed by the current API.</p>
            </div>
          </section>
        </aside>
      </div>

      <footer className="processing-footer"><span>Document: <strong>{doc.file_name}</strong></span><span>SHA-256: <strong>{doc.checksum ? `${doc.checksum.slice(0, 12)}…` : "Not reported"}</strong></span><span>Record link: <strong>{recordId ? "Available" : "Not available"}</strong></span><span className="processing-footer-note">No fabricated telemetry</span></footer>
    </div>
  );
}
