import { useEffect, useRef, useState } from "react";
import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
import { isOperator } from "../components/roles.js";
import EmptyState from "../components/EmptyState.jsx";
import ErrorState from "../components/ErrorState.jsx";
import PageHeader from "../components/PageHeader.jsx";
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

/** Document processing (route #/document/:id) — Stitch 3ddcbec7 stage list
 * driven by the aggregate backend document status. Per-stage timing, worker
 * telemetry, and event streams are not exposed by the backend and are
 * never rendered. Success continues to the record; failure offers one
 * explicit manual retry plus a way back.
 */
export default function DocumentProcessing({ documentId }) {
  const [doc, setDoc] = useState(null);
  const [status, setStatus] = useState("");
  const [recordId, setRecordId] = useState(null);
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
      setRecordId(ex.record_id || null);
    } catch {
      // No extracted record yet (e.g. terminal edge states) — the status
      // badge remains the source of truth; no link is rendered.
      setRecordId(null);
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
      setRecordId(null);
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
    setRecordId(null);
    Promise.all([
      getDocument(documentId, { signal }),
      getDocumentStatus(documentId, { signal }),
    ])
      .then(([full, s]) => {
        if (signal.aborted) return;
        setDoc(full);
        setStatus(s.status);
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
      <div>
        <PageHeader title="Processing document" />
        <div className="panel">
          <ErrorState title="Document unavailable" message={error} requestId={errorRef || undefined} onRetry={() => setDirty((n) => n + 1)} />
          <p><a href="#/records">Back to documents</a></p>
        </div>
      </div>
    );
  }

  if (!doc) {
    return (
      <div>
        <PageHeader title="Processing document" />
        <div className="panel"><Skeleton lines={6} /></div>
      </div>
    );
  }

  const view = processingSteps(status);
  const retryable = RETRYABLE.has(status) && !watching;

  return (
    <div>
      <PageHeader
        title="Processing document"
        sub={doc.file_name}
      />
      <div className="proc-grid">
        <div className="panel">
          <div className="panel-head">
            <div>
              <h2>Cadastral ingestion pipeline</h2>
              <p className="panel-sub">
                <code className="tnum">{doc.id.slice(0, 8)}…</code> • {doc.file_type} • Live status comes from the backend document record; per-stage timing is not exposed.
              </p>
            </div>
            <StatusBadge tone={statusTone(status)}>{statusLabel(status) || "—"}</StatusBadge>
          </div>
          {error && <Alert tone="error" title="Processing note">{error}</Alert>}
          <ProcessingStepper steps={view.steps} />
          <div className="proc-actions">
            {retryable && (
              <Button variant="primary" disabled={busy || !canProcess} onClick={start}>
                {busy ? "Starting…" : status === "UPLOADED" ? "Start processing" : "Retry processing"}
              </Button>
            )}
            {watching && <span className="muted">auto-refreshing…</span>}
            <a href="#/records">Back to documents</a>
          </div>
        </div>

        <div className="panel">
          {view.failed ? (
            <>
              <div className="panel-head"><div><h2>Processing failed</h2></div></div>
              <Alert tone="error" title={status === "VALIDATION_FAILED" ? "Validation failed" : "Processing failed"}>
                The backend pipeline ended in state {status}. No record was produced. Retry once explicitly, or return to the repository.
              </Alert>
              <div className="proc-actions">
                {retryable && (
                  <Button variant="primary" disabled={busy || !canProcess} onClick={start}>
                    {busy ? "Starting…" : "Retry processing"}
                  </Button>
                )}
                <a href="#/records">Back to documents</a>
              </div>
            </>
          ) : view.terminal ? (
            <>
              <div className="panel-head"><div><h2>Processing complete</h2></div></div>
              <Alert tone="success" title={status}>Processing finished. Continue to the extracted record.</Alert>
              <div className="proc-actions">
                {recordId ? (
                  <a href={`#/document/${doc.id}/extract`}>View extraction result</a>
                ) : (
                  <EmptyState title="Resolving record link">The extracted record link is not available yet.</EmptyState>
                )}
              </div>
            </>
          ) : (
            <>
              <div className="panel-head"><div><h2>Current step</h2></div></div>
              <p>
                {status === "UPLOADED"
                  ? "Document stored. Start processing to run the AI pipeline."
                  : "The AI pipeline is running. This view refreshes automatically until the backend reports a terminal state."}
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
