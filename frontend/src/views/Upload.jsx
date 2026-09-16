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

  return (
    <div>
      <PageHeader
        title="Upload document"
        sub="Upload a land record to begin AI-assisted digitization."
      />

      {!doc && (
        <div className="panel">
          <div
            className={`dropzone${dragging ? " dragging" : ""}`}
            role="button"
            tabIndex={0}
            aria-label="Choose a document to upload: PDF, PNG, JPEG, or TIFF up to 10 MB"
            onClick={() => inputRef.current?.click()}
            onKeyDown={(ev) => {
              if (ev.key === "Enter" || ev.key === " ") {
                ev.preventDefault();
                inputRef.current?.click();
              }
            }}
            onDragOver={(ev) => { ev.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(ev) => {
              ev.preventDefault();
              setDragging(false);
              pickFile(ev.dataTransfer.files && ev.dataTransfer.files[0]);
            }}
          >
            <span className="dropzone-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
            </span>
            <span className="dropzone-title">Drop your document here</span>
            <span className="dropzone-sub">or <u>choose a file</u></span>
            <span className="dropzone-formats">PDF, PNG, JPEG or TIFF · up to 10 MB</span>
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPT}
              hidden
              aria-hidden="true"
              tabIndex={-1}
              onChange={(ev) => pickFile(ev.target.files && ev.target.files[0])}
            />
          </div>

          {!file && (
            /* The page was otherwise an empty rectangle. Saying what happens
               next sets expectations and makes the wait feel intentional. */
            <ol className="upload-steps">
              {[
                { n: "1", t: "Read the document",
                  d: "The page is prepared and its text is recognised, including Hindi and Gujarati." },
                { n: "2", t: "Pull out the details",
                  d: "Owner, survey number, area, village and the rest of the record fields." },
                { n: "3", t: "Check the record",
                  d: "Fixed verification rules flag anything that needs a human to confirm it." },
                { n: "4", t: "You decide",
                  d: "Nothing is approved automatically. You review, correct and approve." },
              ].map((step) => (
                <li key={step.n}>
                  <span className="upload-steps-n" aria-hidden="true">{step.n}</span>
                  <span>
                    <span className="upload-steps-t">{step.t}</span>
                    <span className="upload-steps-d">{step.d}</span>
                  </span>
                </li>
              ))}
            </ol>
          )}

          {fileError && <Alert tone="error" title="Invalid file">{fileError}</Alert>}
          {error && <Alert tone="error" title="Upload failed">{error}</Alert>}

          {file && (
            <>
              <div className="filechip">
                <span className="filechip-icon" aria-hidden="true">
                  {(file.name.split(".").pop() || "").slice(0, 3).toUpperCase() || "•"}
                </span>
                <div className="filechip-meta">
                  <div className="filechip-name">{file.name}</div>
                  <div className="filechip-sub">{file.type || "unknown type"} • {formatSize(file.size)}</div>
                </div>
                <button type="button" className="filechip-remove" onClick={() => pickFile(null)} disabled={uploading}>
                  Remove
                </button>
              </div>

              <form onSubmit={uploadAndProcess}>
                <div className="upload-meta-grid">
                  <TextInput
                    label="Document type"
                    hint="Optional"
                    id="upload-doctype"
                    placeholder="e.g. khata"
                    value={documentType}
                    disabled={uploading}
                    maxLength={64}
                    onChange={(e) => setDocumentType(e.target.value)}
                  />
                  <TextInput
                    label="Language"
                    hint="Optional"
                    id="upload-language"
                    placeholder="e.g. en"
                    value={language}
                    disabled={uploading}
                    maxLength={32}
                    onChange={(e) => setLanguage(e.target.value)}
                  />
                </div>

                {demoEnabled && (
                  <fieldset className="upload-mode">
                    <legend>Processing mode</legend>
                    <div className="upload-mode-options">
                      {[
                        { value: "live", label: "Live",
                          hint: "Reads the document with the full pipeline." },
                        { value: "demo", label: "Demo",
                          hint: "Uses configured demonstration data for a known document." },
                      ].map((opt) => (
                        <label key={opt.value} className="upload-mode-option">
                          <input
                            type="radio"
                            name="processing-mode"
                            value={opt.value}
                            checked={mode === opt.value}
                            disabled={uploading}
                            onChange={() => setMode(opt.value)}
                          />
                          <span>
                            <span className="upload-mode-label">{opt.label}</span>
                            <span className="upload-mode-hint">{opt.hint}</span>
                          </span>
                        </label>
                      ))}
                    </div>
                    {mode === "demo" && (
                      <p className="upload-mode-note">
                        Demonstration mode. This reads configured demonstration data instead
                        of processing the document, and only works for the documents your
                        administrator has set up.
                      </p>
                    )}
                  </fieldset>
                )}
                {uploading && (
                  <div className="progressbar" role="progressbar" aria-label="Uploading document">
                    <div className="progressbar-indet" />
                  </div>
                )}
                <div className="upload-actions">
                  <Button type="button" variant="secondary" onClick={cancel}>
                    {uploading ? "Cancel upload" : "Cancel"}
                  </Button>
                  <Button type="submit" variant="primary" disabled={uploading}>
                    {uploading ? "Uploading…" : "Upload & Process"}
                  </Button>
                </div>
              </form>
            </>
          )}
        </div>
      )}

      {doc && (
        <div className="vstack">
          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Staged record</h2>
                <p className="panel-sub">Live status for this document.</p>
              </div>
              <Button variant="secondary" onClick={uploadAnother}>Upload another</Button>
            </div>
            {error && <Alert tone="error" title="Processing note">{error}</Alert>}
            <p className="tracker-id"><b>document_id:</b> <code className="tnum">{doc.id}</code></p>
            <p><a href={`#/document/${doc.id}`}>Open processing view</a></p>
            <p className="tracker-id muted">SHA-256 <code className="tnum">{shortHash(doc.checksum)}</code></p>
            <div className="tracker-row">
              <b>Status:</b>
              <StatusBadge tone={statusTone(status)}>{statusLabel(status) || "—"}</StatusBadge>
              {watching && <span className="muted">auto-refreshing…</span>}
              <Button variant="secondary" onClick={refresh}>Refresh status</Button>
              <Button variant="secondary" onClick={loadResults} disabled={resultsLoading}>
                {resultsLoading ? "Loading…" : "Load extraction + validation"}
              </Button>
            </div>
          </div>

          {resultsLoading && !extraction && (
            <div className="panel"><Skeleton lines={4} /></div>
          )}
          {resultsError && !extraction && (
            <div className="panel">
              <ErrorState title="Results unavailable" message={resultsError} requestId={resultsRef || undefined} onRetry={loadResults} />
            </div>
          )}
          {extraction && (
            <div className="panel">
              <div className="panel-head">
                <div>
                  <h2>Extracted fields ({extraction.fields.length})</h2>
                </div>
              </div>
              <DataTable columns={["Field", "Value", "Confidence"]}>
                {extraction.fields.map((f) => (
                  <tr key={f.field_name}>
                    <td><code>{f.field_name}</code></td>
                    <td>{f.value === null ? <span className="muted">Not found</span> : String(f.value)}</td>
                    <td><ConfidenceBadge value={f.confidence} /></td>
                  </tr>
                ))}
              </DataTable>
              {extraction.record_id && (
                <p><a href={`#/record/${extraction.record_id}`}>Open record {extraction.record_id.slice(0, 8)}…</a></p>
              )}
            </div>
          )}
          {validation && (
            <div className="panel">
              <div className="panel-head">
                <div>
                  <h2>Validation: {validation.status}</h2>
                </div>
              </div>
              {validation.issues.length === 0 && <EmptyState title="No issues">All deterministic checks passed.</EmptyState>}
              {validation.issues.length > 0 && <ValidationSummary status={validation.status} issues={validation.issues} />}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
