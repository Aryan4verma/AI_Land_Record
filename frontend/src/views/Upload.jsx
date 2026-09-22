import { useEffect, useRef, useState } from "react";
import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
import ConfidenceBadge from "../components/ConfidenceBadge.jsx";
import DataTable from "../components/DataTable.jsx";
import EmptyState from "../components/EmptyState.jsx";
import ErrorState from "../components/ErrorState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import Skeleton from "../components/Skeleton.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import TextInput from "../components/TextInput.jsx";
import ValidationSummary from "../components/ValidationSummary.jsx";
import { isOperator } from "../components/roles.js";
import { clearLastDocumentId, createSubmitGuard, getDocument, getDocumentStatus, getDocumentValidation, getExtraction, getHealthAi, getLastDocumentId, getUser, isProcessingTerminal, setLastDocumentId, startProcessing, uploadDocument } from "../api/client";
import { statusLabel, statusTone, uploadFileCheck } from "../api/types";
import { friendlyMessage, requestIdOf } from "../components/errors.js";
import "../styles/upload.css";
/** Status poll cadence/cap while a document is being processed (~5 min max). */
const POLL_INTERVAL_MS = 3000;
const POLL_MAX_ATTEMPTS = 100;
const ACCEPT = ".pdf,.png,.jpg,.jpeg,.tif,.tiff";

const LOCAL_ERROR_TEXT = {
  UNSUPPORTED_FILE_TYPE: "Unsupported file type. Accepted: PDF, PNG, JPEG, TIFF.",
  FILE_TYPE_MISMATCH: "The file extension and its content type disagree — pick a matching file.",
  FILE_TOO_LARGE: "File exceeds the 10 MB limit enforced by the backend.",
};

function formatSize(bytes) {
  if (!Number.isFinite(bytes)) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function shortHash(checksum) {
  return checksum ? `${checksum.slice(0, 12)}…` : "—";
}

/** Upload document (route #/upload) — Stitch babc23151d0e41268b20a9ccd4801eb6
 * on the real upload contract. Instant client checks mirror the backend
 * (type/size); the backend re-validates everything and stays authoritative.
 * Upload & Process uploads, starts the backend pipeline, then tracks the
 * backend-created document — processing completion is never fabricated.
 */
export default function Upload() {
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [documentType, setDocumentType] = useState("");
  // Processing mode is per-request state, never a global toggle: one
  // operator choosing Demo must not affect anybody else.
  const [mode, setMode] = useState("live");
  const [demoEnabled, setDemoEnabled] = useState(false);

  useEffect(() => {
    // The server decides whether Demo Mode exists at all; this only hides a
    // control the backend would refuse anyway.
    let cancelled = false;
    getHealthAi()
      .then((h) => { if (!cancelled) setDemoEnabled(!!h.demo_enabled); })
      .catch(() => { /* capability unknown -> selector stays hidden */ });
    return () => { cancelled = true; };
  }, []);
  const [language, setLanguage] = useState("");
  const [fileError, setFileError] = useState("");
  const [doc, setDoc] = useState(null);
  const [status, setStatus] = useState("");
  const [extraction, setExtraction] = useState(null);
  const [validation, setValidation] = useState(null);
  const [resultsError, setResultsError] = useState("");
  const [resultsRef, setResultsRef] = useState("");
  const [resultsLoading, setResultsLoading] = useState(false);
  const [error, setError] = useState("");
  const [phase, setPhase] = useState("idle");
  // File object only — bytes are never read into React state.
  const [watching, setWatching] = useState(false);
  const inputRef = useRef(null);
  const submitGuard = useRef(null);
  if (!submitGuard.current) submitGuard.current = createSubmitGuard();
  const uploadAbort = useRef(null);
  const pollTimer = useRef(null);

  function stopPolling() {
    if (pollTimer.current) {
      clearInterval(pollTimer.current);
      pollTimer.current = null;
    }
    setWatching(false);
  }

  function pickFile(next) {
    setError("");
    setFileError("");
    if (!next) {
      setFile(null);
      return;
    }
    const code = uploadFileCheck(next.name, next.size, next.type || "");
    if (code) {
      setFile(null);
      setFileError(LOCAL_ERROR_TEXT[code]);
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    setFile(next);
    setPhase("selected");
  }

  function clearSelection() {
    uploadAbort.current?.abort();
    uploadAbort.current = null;
    stopPolling();
    setFile(null);
    setFileError("");
    setError("");
    setPhase("idle");
    if (inputRef.current) inputRef.current.value = "";
  }

  function cancel() {
    // Secondary action: abort an in-flight upload, otherwise clear selection.
    if (phase === "uploading") {
      uploadAbort.current?.abort();
      return;
    }
    clearSelection();
  }

  async function loadResultsFor(docId) {
    // GET extraction + validation for the processed document
    const [ex, val] = await Promise.all([getExtraction(docId), getDocumentValidation(docId)]);
    setExtraction(ex);
    setValidation(val);
  }

  async function loadResults() {
    if (!doc) return;
    setResultsError("");
    setResultsRef("");
    setResultsLoading(true);
    try {
      await loadResultsFor(doc.id);
    } catch (err) {
      setResultsError(friendlyMessage(err));
      setResultsRef(requestIdOf(err));
    } finally {
      setResultsLoading(false);
    }
  }

  async function refresh() {
    if (!doc) return;
    setError("");
    try {
      // GET /api/v1/documents/{id}/status — backend remains source of truth
      const s = await getDocumentStatus(doc.id);
      setStatus(s.status);
      setDoc({ ...doc, processing_status: s.status });
    } catch (err) {
      setError(friendlyMessage(err));
    }
  }

  function startStatusPolling(docId, docSnapshot) {
    stopPolling();
    setWatching(true);
    let attempts = 0;
    pollTimer.current = setInterval(async () => {
      attempts += 1;
      try {
        const s = await getDocumentStatus(docId);
        setStatus(s.status);
        if (docSnapshot) setDoc({ ...docSnapshot, processing_status: s.status });
        if (isProcessingTerminal(s.status)) {
          stopPolling();
          // Terminal state reached: load persisted results automatically.
          setResultsLoading(true);
          try {
            await loadResultsFor(docId);
            setResultsError("");
            setResultsRef("");
          } catch (err) {
            // FAILED docs have no extraction yet (404); surface, don't fabricate.
            setResultsError(friendlyMessage(err));
            setResultsRef(requestIdOf(err));
          } finally {
            setResultsLoading(false);
          }
        } else if (attempts >= POLL_MAX_ATTEMPTS) {
          stopPolling();
          setError("Still processing after ~5 minutes. Use Refresh status to check again.");
        }
      } catch (err) {
        stopPolling();
        setError(friendlyMessage(err));
      }
    }, POLL_INTERVAL_MS);
  }

  async function uploadAndProcess(e) {
    e.preventDefault();
    if (!file || !submitGuard.current.tryAcquire()) return; // duplicate click: ignore
    setError("");
    setPhase("uploading");
    const controller = new AbortController();
    uploadAbort.current = controller;
    try {
      // POST /api/v1/documents (multipart) -> 201 {document_id, status}
      const created = await uploadDocument(
        file,
        {
          ...(documentType.trim() ? { documentType: documentType.trim() } : {}),
          ...(language.trim() ? { language: language.trim() } : {}),
        },
        { signal: controller.signal },
      );
      // The document identity comes from the backend response — never invented.
      const full = await getDocument(created.document_id);
      setDoc(full);
      setStatus(full.processing_status);
      setExtraction(null);
      setValidation(null);
      setResultsError("");
      setResultsRef("");
      setLastDocumentId(full.id);
      setPhase("tracking");
      // Primary action continues straight into the backend pipeline.
      await startProcessing(full.id, mode);
      await refresh();
      startStatusPolling(full.id, full);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        setError("Upload cancelled.");
        setPhase(file ? "selected" : "idle");
      } else {
        setError(friendlyMessage(err));
        setPhase(doc ? "tracking" : "selected");
      }
    } finally {
      uploadAbort.current = null;
      submitGuard.current.release();
    }
  }

  function uploadAnother() {
    stopPolling();
    clearLastDocumentId();
    setDoc(null);
    setStatus("");
    setExtraction(null);
    setValidation(null);
    setResultsError("");
    setResultsRef("");
    clearSelection();
  }

  // Restore the last document across refresh/navigation; stop polling on unmount.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const lastId = getLastDocumentId();
      if (!lastId) return;
      try {
        const [full, s] = await Promise.all([getDocument(lastId), getDocumentStatus(lastId)]);
        if (cancelled) return;
        setDoc(full);
        setStatus(s.status);
        setError("");
        setPhase("tracking");
        if (!isProcessingTerminal(s.status)) startStatusPolling(lastId, full);
      } catch {
        // Document gone (or DB reset): drop the stale reference, don't fabricate.
        if (!cancelled) {
          clearLastDocumentId();
          setDoc(null);
          setStatus("");
        }
      }
    })();
    return () => {
      cancelled = true;
      if (pollTimer.current) {
        clearInterval(pollTimer.current);
        pollTimer.current = null;
      }
      uploadAbort.current?.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const uploading = phase === "uploading";

  // Uploading and processing are operator-only. Rather than render a form
  // whose submit the backend would reject with 403, say so plainly.
  if (!isOperator(getUser())) {
    return (
      <>
        <PageHeader title="Upload" subtitle="Add a land record to the workspace" />
        <Alert tone="info" title="Operator access required">
          Your account has read-only access. Uploading and processing documents need an
          operator account. You can still search, open and export records.
        </Alert>
      </>
    );
  }

  const terminal = !!doc && isProcessingTerminal(status);
  const currentStage = !doc ? "upload" : terminal ? "review" : "pipeline";
  const selectedName = doc?.file_name || file?.name || "No instrument selected";
  const selectedType = doc?.file_type || file?.type || "Awaiting file selection";
  const selectedSize = doc ? formatSize(doc.file_size) : file ? formatSize(file.size) : "—";
  const integrity = doc?.checksum ? `SHA-256: ${shortHash(doc.checksum)}` : file ? "Backend hash generated after upload" : "Hash generated on secure upload";

  function stageClass(stage) {
    if (currentStage === stage) return "is-active";
    if ((stage === "upload" && currentStage !== "upload") || (stage === "pipeline" && currentStage === "review")) return "is-complete";
    return "";
  }

  function openPicker() {
    inputRef.current?.click();
  }

  return (
    <div className="upload-view">
      <section className="upload-workflow-bar" aria-label="Ingestion workflow">
        <div className="upload-workflow-track">
          <span className="upload-eyebrow">Workflow stage:</span>
          <span className={`upload-stage ${stageClass("upload")}`}><i />1. Upload &amp; pre-inspection</span>
          <span className="upload-stage-arrow" aria-hidden="true">→</span>
          <span className={`upload-stage ${stageClass("pipeline")}`}>2. Pipeline extraction</span>
          <span className="upload-stage-arrow" aria-hidden="true">→</span>
          <span className={`upload-stage ${stageClass("review")}`}>3. Review &amp; adjudication</span>
        </div>
        <div className="upload-security-strip">
          <span className="upload-version">NLRMP ingestion</span>
          <span><b aria-hidden="true">◆</b> SHA-256 integrity logging</span>
        </div>
      </section>

      <section className="upload-pagehead">
        <div>
          <h1>Ingest Cadastral Record &amp; Deed Instruments</h1>
          <p>Statutory land document ingestion, OCR, and deterministic validation pipeline.</p>
        </div>
        <div className="upload-page-actions">
          <a href="#/audit" className="upload-compact-button">⌁ <span>Ingestion logs</span></a>
          {doc && <button type="button" className="upload-compact-button" onClick={uploadAnother}>＋ <span>Upload another</span></button>}
        </div>
      </section>

      <div className="upload-grid">
        <div className="upload-left-column">
          <section className="upload-card">
            <header className="upload-card-header">
              <h2><span aria-hidden="true">⇧</span> Upload cadastral instrument</h2>
              <span className="upload-card-code">{doc ? `Document: ${doc.id.slice(0, 8)}…` : "Private source storage"}</span>
            </header>
            {!file && !doc ? (
              <div className="upload-card-body">
                <div
                  className={`upload-dropzone${dragging ? " is-dragging" : ""}`}
                  role="button"
                  tabIndex={0}
                  aria-label="Choose a document to upload: PDF, PNG, JPEG, or TIFF up to 10 MB"
                  onClick={openPicker}
                  onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openPicker(); } }}
                  onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={(event) => { event.preventDefault(); setDragging(false); pickFile(event.dataTransfer.files && event.dataTransfer.files[0]); }}
                >
                  <span className="upload-dropzone-icon" aria-hidden="true">▧</span>
                  <strong>Drop a certified land record or scan here</strong>
                  <p>Upload a supported source document for server-side integrity checks and processing.</p>
                  <span className="upload-browse-button">▣ Browse institutional files</span>
                  <input ref={inputRef} type="file" accept={ACCEPT} hidden aria-hidden="true" tabIndex={-1} onChange={(event) => pickFile(event.target.files && event.target.files[0])} />
                  <div className="upload-capability-grid">
                    <div><span>Formats</span><strong>PDF · PNG · JPEG · TIFF</strong></div>
                    <div><span>Max threshold</span><strong>10 MB per file</strong></div>
                    <div><span>Validation</span><strong>Type + magic bytes</strong></div>
                    <div><span>Integrity</span><strong>SHA-256 on upload</strong></div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="upload-card-body upload-uploaded-source">
                <div className="upload-source-summary">
                  <span className="upload-file-icon" aria-hidden="true">{(selectedName.split(".").pop() || "FILE").slice(0, 3).toUpperCase()}</span>
                  <div className="upload-source-copy">
                    <strong title={selectedName}>{selectedName}</strong>
                    <span>{selectedType} · {selectedSize}</span>
                    <small className={doc ? "is-verified" : ""}>{doc ? "✓ Backend document created" : "✓ Local type and size checks passed"}</small>
                  </div>
                  {!doc && <button type="button" className="upload-link-button" onClick={() => pickFile(null)} disabled={uploading}>Remove</button>}
                </div>
                <div className="upload-integrity-row"><span>Integrity status</span><code>{integrity}</code></div>
              </div>
            )}
            {fileError && <div className="upload-inline-alert"><Alert tone="error" title="Invalid file">{fileError}</Alert></div>}
            {error && !doc && <div className="upload-inline-alert"><Alert tone="error" title="Upload failed">{error}</Alert></div>}
          </section>

          {(file || doc) && (
            <section className="upload-card">
              <header className="upload-card-header">
                <h2><span className="is-success" aria-hidden="true">✓</span> Currently selected &amp; staged instrument</h2>
                <StatusBadge tone={doc ? statusTone(status) : "processing"}>{doc ? statusLabel(status) : "Ready for upload"}</StatusBadge>
              </header>
              <div className="upload-card-body">
                <div className="upload-facts-grid">
                  <div><span>Source type</span><strong>{selectedType}</strong></div>
                  <div><span>File size</span><strong>{selectedSize}</strong></div>
                  <div><span>Document state</span><strong>{doc ? statusLabel(status) : "Awaiting upload"}</strong></div>
                  <div><span>Source hash</span><strong>{doc?.checksum ? shortHash(doc.checksum) : "Generated on upload"}</strong></div>
                </div>
                <div className="upload-inspector-row">
                  <span>Source evidence remains private and linked to the processing record.</span>
                  {doc ? <a href={`#/document/${doc.id}`}>Open processing view ↗</a> : <span>Not yet stored</span>}
                </div>
              </div>
            </section>
          )}
        </div>

        <div className="upload-right-column">
          <section className="upload-card upload-controls-card">
            <header className="upload-card-header">
              <h2><span aria-hidden="true">⚙</span> Pre-processing &amp; jurisdiction</h2>
              <span className="upload-card-code">Server-authoritative</span>
            </header>
            <form className="upload-card-body" onSubmit={uploadAndProcess}>
              <div className="upload-readonly-grid">
                <div><span>Storage</span><strong>Private document bucket</strong></div>
                <div><span>Backend guard</span><strong>Auth + MIME + bytes</strong></div>
              </div>
              <div className="upload-form-grid">
                <TextInput label="Document type" hint="Optional" id="upload-doctype" placeholder="e.g. khata" value={documentType} disabled={uploading || !!doc} maxLength={64} onChange={(event) => setDocumentType(event.target.value)} />
                <TextInput label="Language" hint="Optional" id="upload-language" placeholder="e.g. en" value={language} disabled={uploading || !!doc} maxLength={32} onChange={(event) => setLanguage(event.target.value)} />
              </div>
              {demoEnabled && !doc && (
                <fieldset className="upload-mode upload-mode-stitch">
                  <legend>Pipeline processing mode</legend>
                  <div className="upload-mode-options">
                    <label className={`upload-mode-option${mode === "live" ? " is-selected" : ""}`}><input type="radio" name="processing-mode" value="live" checked={mode === "live"} disabled={uploading} onChange={() => setMode("live")} /><span><b>Live pipeline</b><small>Reads the uploaded document.</small></span></label>
                    <label className={`upload-mode-option${mode === "demo" ? " is-selected" : ""}`}><input type="radio" name="processing-mode" value="demo" checked={mode === "demo"} disabled={uploading} onChange={() => setMode("demo")} /><span><b>Demo mode</b><small>Uses configured demonstration data.</small></span></label>
                  </div>
                  {mode === "demo" && <p className="upload-mode-note">Demonstration mode bypasses external OCR/AI only where configured. Validation, persistence, review, approval and audit remain real.</p>}
                </fieldset>
              )}
              <div className="upload-notice"><span aria-hidden="true">◆</span><p><strong>Integrity notice:</strong> uploaded bytes are revalidated by the backend and the stored document receives an audit-preserving checksum.</p></div>
              {uploading && <div className="progressbar" role="progressbar" aria-label="Uploading document"><div className="progressbar-indet" /></div>}
              {!doc ? (
                <div className="upload-control-actions">
                  <Button type="button" variant="secondary" onClick={cancel}>{uploading ? "Cancel upload" : "Clear"}</Button>
                  <Button type="submit" variant="primary" disabled={!file || uploading}>{uploading ? "Uploading…" : "Start pipeline processing →"}</Button>
                </div>
              ) : (
                <div className="upload-control-actions upload-control-actions-wrap">
                  <Button type="button" variant="secondary" onClick={refresh}>Refresh status</Button>
                  <Button type="button" variant="secondary" onClick={loadResults} disabled={resultsLoading}>{resultsLoading ? "Loading…" : "Load extraction + validation"}</Button>
                  {watching && <span className="upload-watching">Auto-refreshing status…</span>}
                </div>
              )}
            </form>
          </section>

          {doc && error && <div className="upload-inline-alert"><Alert tone="error" title="Processing note">{error}</Alert></div>}
          {doc && resultsLoading && !extraction && <section className="upload-card upload-results-card"><Skeleton lines={4} /></section>}
          {doc && resultsError && !extraction && <section className="upload-card upload-results-card"><ErrorState title="Results unavailable" message={resultsError} requestId={resultsRef || undefined} onRetry={loadResults} /></section>}
          {extraction && <section className="upload-card upload-results-card"><header className="upload-card-header"><h2>Extracted fields ({extraction.fields.length})</h2></header><div className="upload-results-body"><DataTable columns={["Field", "Value", "Confidence"]}>{extraction.fields.map((field) => <tr key={field.field_name}><td><code>{field.field_name}</code></td><td>{field.value === null ? <span className="muted">Not found</span> : String(field.value)}</td><td><ConfidenceBadge value={field.confidence} /></td></tr>)}</DataTable>{extraction.record_id && <p><a href={`#/record/${extraction.record_id}`}>Open record {extraction.record_id.slice(0, 8)}…</a></p>}</div></section>}
          {validation && <section className="upload-card upload-results-card"><header className="upload-card-header"><h2>Validation: {validation.status}</h2></header><div className="upload-results-body">{validation.issues.length === 0 ? <EmptyState title="No issues">All deterministic checks passed.</EmptyState> : <ValidationSummary status={validation.status} issues={validation.issues} />}</div></section>}
        </div>
      </div>

      <section className="upload-card upload-log-card">
        <header className="upload-card-header"><h2><span aria-hidden="true">↶</span> Recent ingestion log</h2><a href="#/audit">Full audit log ↗</a></header>
        <div className="upload-log-wrap">
          <table className="upload-log-table"><thead><tr><th>Instrument file name</th><th>Document ID</th><th>Storage / workflow status</th><th>Ingestion timestamp</th><th>Integrity</th><th>Audit trail</th></tr></thead><tbody>
            {doc ? <tr><td><span className="upload-file-glyph" aria-hidden="true">▧</span> {doc.file_name}</td><td><code>{doc.id.slice(0, 12)}…</code></td><td><StatusBadge tone={statusTone(status)}>{statusLabel(status)}</StatusBadge></td><td><code>{doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleString() : "—"}</code></td><td><span className="upload-log-integrity">✓ SHA-256 stored</span></td><td><a href={`#/record/${doc.id}/audit`}>View dossier</a></td></tr> : <tr><td colSpan="6" className="upload-log-empty">No completed ingestion in this session. Select a supported source document to begin.</td></tr>}
          </tbody></table>
        </div>
      </section>
    </div>
  );
}
