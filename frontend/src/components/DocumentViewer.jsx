import { statusLabel } from "../api/types";
import EmptyState from "./EmptyState.jsx";

/** Source-document pane. The backend exposes document metadata only — no
 * file-download endpoint exists, so scan bytes cannot be rendered. This
 * panel shows real metadata and says so explicitly instead of faking a
 * scan image or rendering dead viewer controls.
 */
/** Bytes are an implementation detail; operators read KB/MB. */
function fileSize(bytes) {
  const n = Number(bytes);
  if (!Number.isFinite(n) || n <= 0) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${Math.round(n / 1024)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentViewer({ document }) {
  return (
    <div className="panel">
      <div className="panel-head">
        <div>
          <h2>Original document</h2>
          <p className="panel-sub">{document.file_name}</p>
        </div>
      </div>
      <dl className="kv">
        <div><dt>Type</dt><dd>{document.file_type}</dd></div>
        <div><dt>Size</dt><dd className="tnum">{fileSize(document.file_size)}</dd></div>
        <div><dt>SHA-256</dt><dd><code className="tnum">{document.checksum ? `${document.checksum.slice(0, 16)}…` : "—"}</code></dd></div>
        <div><dt>Document type</dt><dd>{document.document_type || "—"}</dd></div>
        <div><dt>Status</dt><dd>{statusLabel(document.processing_status)}</dd></div>
      </dl>
      <EmptyState title="Scan preview unavailable">
        In-browser scan rendering needs a file-download endpoint the backend does not expose; source bytes stay in private storage. Page navigation, zoom, and fullscreen arrive with that endpoint.
      </EmptyState>
    </div>
  );
}
