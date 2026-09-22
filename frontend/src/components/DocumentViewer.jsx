import { useEffect, useState } from "react";
import { getDocumentPage } from "../api/client";
import { friendlyMessage, requestIdOf } from "./errors.js";
import ErrorState from "./ErrorState.jsx";
import Skeleton from "./Skeleton.jsx";
import StatusBadge from "./StatusBadge.jsx";
import { statusLabel } from "../api/types";

/** Bytes are an implementation detail; operators read KB/MB. */
function fileSize(bytes) {
  const n = Number(bytes);
  if (!Number.isFinite(n) || n <= 0) return "Not available";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${Math.round(n / 1024)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

/** Authenticated source-document pane. The image URL is an in-memory object
 * URL backed by the private page-rendering endpoint; storage paths never reach
 * the browser and are never shown as links.
 */
export default function DocumentViewer({ document, initialPage = 1, workspaceMode = false, evidenceCount = 0 }) {
  const [page, setPage] = useState(Math.max(1, Number(initialPage) || 1));
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [src, setSrc] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [errorRef, setErrorRef] = useState("");

  useEffect(() => {
    if (!document?.id) return undefined;
    const controller = new AbortController();
    let objectUrl = "";
    getDocumentPage(document.id, page, { signal: controller.signal })
      .then((blob) => {
        if (controller.signal.aborted) return;
        objectUrl = URL.createObjectURL(blob);
        setSrc(objectUrl);
      })
      .catch((err) => {
        if (controller.signal.aborted || err?.name === "AbortError") return;
        setError(friendlyMessage(err));
        setErrorRef(requestIdOf(err));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [document?.id, page]);

  function changePage(nextPage) {
    setPage(Math.max(1, Number(nextPage) || 1));
    setLoading(true);
    setError("");
    setErrorRef("");
    setSrc("");
  }

  function changeZoom(delta) {
    setZoom((current) => Math.min(2, Math.max(0.75, Number((current + delta).toFixed(2)))));
  }

  return (
    <section className="panel source-viewer" aria-label="Source document">
      <div className="panel-head source-viewer-head">
        <div>
          <span className="t-eyebrow">SOURCE DOCUMENT</span>
          <h2>Original document</h2>
          <p className="panel-sub">{document.file_name}</p>
        </div>
        <StatusBadge tone="processing">Private source</StatusBadge>
      </div>

      {workspaceMode && (
        <div className="source-viewer-strip" aria-label="Source evidence status">
          <span className="source-viewer-strip-label">SOURCE TRUTH</span>
          <span>{evidenceCount ? `${evidenceCount} cited field${evidenceCount === 1 ? "" : "s"}` : "No linked OCR evidence"}</span>
          <span className="source-viewer-strip-note">Private render · backend-authorized</span>
        </div>
      )}

      <div className={`source-stage${workspaceMode ? " source-stage-workspace" : ""}`} aria-live="polite" aria-busy={loading}>
        {loading && <Skeleton lines={6} />}
        {!loading && error && (
          <ErrorState title="Page unavailable" message={error} requestId={errorRef || undefined} />
        )}
        {!loading && !error && src && (
          <img
            src={src}
            alt={`Page ${page} of ${document.file_name}`}
            style={workspaceMode ? { transform: `scale(${zoom}) rotate(${rotation}deg)` } : undefined}
          />
        )}
      </div>

      <div className={`source-controls${workspaceMode ? " source-controls-workspace" : ""}`}>
        <button type="button" className="btn btn-secondary" disabled={page <= 1 || loading} onClick={() => changePage(page - 1)}>
          Previous
        </button>
        <label className="source-page-label" htmlFor={`source-page-${document.id}`}>
          Page
          <input
            id={`source-page-${document.id}`}
            className="source-page-input tnum"
            type="number"
            min="1"
            value={page}
            onChange={(event) => changePage(event.target.value)}
            aria-label="Source page number"
          />
        </label>
        <button type="button" className="btn btn-secondary" disabled={loading} onClick={() => changePage(page + 1)}>
          Next
        </button>
        {workspaceMode && (
          <div className="source-viewer-tools" aria-label="Source page view controls">
            <button type="button" className="btn btn-secondary" disabled={loading} onClick={() => changeZoom(-0.1)} aria-label="Zoom out">−</button>
            <span className="source-zoom tnum" aria-live="polite">{Math.round(zoom * 100)}%</span>
            <button type="button" className="btn btn-secondary" disabled={loading} onClick={() => changeZoom(0.1)} aria-label="Zoom in">+</button>
            <button type="button" className="btn btn-secondary" disabled={loading} onClick={() => { setZoom(1); setRotation(0); }}>Fit</button>
            <button type="button" className="btn btn-secondary" disabled={loading} onClick={() => setRotation((current) => (current + 90) % 360)} aria-label="Rotate page">Rotate</button>
          </div>
        )}
      </div>
      <p className="source-note">Rendered securely from private storage. Page availability is validated by the backend.{workspaceMode && evidenceCount === 0 ? " OCR coordinates are not available for this record." : ""}</p>

      <details className="source-meta">
        <summary>Document facts</summary>
        <dl className="kv">
          <div><dt>Type</dt><dd>{document.file_type}</dd></div>
          <div><dt>Size</dt><dd className="tnum">{fileSize(document.file_size)}</dd></div>
          <div><dt>SHA-256</dt><dd><code className="tnum">{document.checksum ? `${document.checksum.slice(0, 16)}…` : "Not available"}</code></dd></div>
          <div><dt>Document type</dt><dd>{document.document_type || "Not available"}</dd></div>
          <div><dt>Status</dt><dd>{statusLabel(document.processing_status)}</dd></div>
        </dl>
      </details>
    </section>
  );
}
