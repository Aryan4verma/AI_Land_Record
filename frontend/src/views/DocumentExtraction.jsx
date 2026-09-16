import { useEffect, useRef, useState } from "react";
import Button from "../components/Button.jsx";
import DocumentViewer from "../components/DocumentViewer.jsx";
import ErrorState from "../components/ErrorState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import RecordFields from "../components/RecordFields.jsx";
import RecordSummary from "../components/RecordSummary.jsx";
import ResultBanner from "../components/ResultBanner.jsx";
import Skeleton from "../components/Skeleton.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import ValidationSummary from "../components/ValidationSummary.jsx";
import { downloadJson } from "../components/format.js";
import { friendlyMessage, requestIdOf } from "../components/errors.js";
import {
  exportRecord,
  getDocument,
  getDocumentValidation,
  getExtraction,
  getUser,
  listReviews,
} from "../api/client";
import { statusLabel, statusTone } from "../api/types";import "../styles/extraction.css";

/** Map extraction fields to human summary rows (backend values verbatim).
 * reviewText is omitted when unknown (read-only users cannot list tasks).
 */
function summaryRows(byName, doc, validation, reviewText) {
  const valueOf = (name) => {
    const f = byName.get(name);
    return f ? f.value : null;
  };
  const area = valueOf("area");
  const areaUnit = valueOf("area_unit");
  return [
    { label: "Owner", value: valueOf("owner_name") },
    { label: "Survey number", value: valueOf("survey_number") },
    { label: "Area", value: area === null ? null : `${area}${areaUnit ? ` ${areaUnit}` : ""}` },
    { label: "Village", value: valueOf("village") },
    { label: "Tehsil", value: valueOf("tehsil") },
    { label: "District", value: valueOf("district") },
    { label: "Mutation number", value: valueOf("mutation_number") },
    { label: "Record date", value: valueOf("record_date") },
    { label: "Validation", value: validation ? validation.status : null },
    { label: "Review", value: reviewText === undefined ? null : reviewText },
    { label: "Source document", value: doc ? doc.file_name : null },
    { label: "Ingested", value: doc && doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleString() : null },
  ];
}

/** Extraction result (route #/document/:id/extract) — Stitch a21c29e7
 * two-pane workspace on real endpoints. Values, confidence, and validation
 * render backend data verbatim; "View evidence" appears only for fields
 * carrying actual OCR evidence; the viewer shows real metadata because no
 * file-download endpoint exists. Actions route to existing workflows only.
 */
export default function DocumentExtraction({ documentId }) {
  const [doc, setDoc] = useState(null);
  const [extraction, setExtraction] = useState(null);
  const [validation, setValidation] = useState(null);
  const [reviewTask, setReviewTask] = useState(undefined);
  const [evidenceFor, setEvidenceFor] = useState(null);
  const [shownId, setShownId] = useState(null);
  const [valFlash, setValFlash] = useState(false);
  const [error, setError] = useState("");
  const [errorRef, setErrorRef] = useState("");
  const [exporting, setExporting] = useState(false);
  const [dirty, setDirty] = useState(0);
  const validationRef = useRef(null);
  const flashTimer = useRef(null);

  function isAbort(err) {
    return err instanceof DOMException && err.name === "AbortError";
  }

  useEffect(() => {
    const controller = new AbortController();
    const signal = controller.signal;
    const opts = { signal };
    // One parallel load: metadata + extraction + validation. No partial
    // rendering on failure — the error state replaces everything. The
    // shownId gate below (set only on success) prevents stale-document
    // flashes without synchronous resets inside this effect.
    Promise.all([
      getDocument(documentId, opts),
      getExtraction(documentId, opts),
      getDocumentValidation(documentId, opts),
    ])
      .then(([d, ex, val]) => {
        if (signal.aborted) return;
        setDoc(d);
        setExtraction(ex);
        setValidation(val);
        setEvidenceFor(null);
        setShownId(documentId);
        setReviewTask(undefined);
        // Review state for the summary (operator-visible; read-only users get a
        // 403 here, which only means "unknown" — never an error state).
        if (ex.record_id) {
          Promise.all([listReviews("PENDING", opts), listReviews("IN_REVIEW", opts)])
            .then(([pending, inReview]) => {
              if (signal.aborted) return;
              setReviewTask([...pending, ...inReview].find((t) => t.land_record_id === ex.record_id) || null);
            })
            .catch(() => {
              if (!signal.aborted) setReviewTask(undefined);
            });
        } else {
          setReviewTask(null);
        }
      })
      .catch((err) => {
        if (isAbort(err) || signal.aborted) return;
        setError(friendlyMessage(err));
        setErrorRef(requestIdOf(err));
      });
    return () => controller.abort();
  }, [documentId, dirty]);

  async function downloadExport() {
    if (!extraction || !extraction.record_id || exporting) return;
    setExporting(true);
    setError("");
    try {
      // GET /api/v1/records/{id}/export — the backend's canonical JSON.
      const payload = await exportRecord(extraction.record_id);
      downloadJson(`record-${extraction.record_id.slice(0, 8)}.json`, payload);
    } catch (err) {
      setError(friendlyMessage(err));
    } finally {
      setExporting(false);
    }
  }

  function scrollToValidation() {
    const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    validationRef.current?.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
    // Brief highlight so arrival is perceptible (the anchor clears the
    // sticky header via scroll-margin-top in extraction.css).
    setValFlash(true);
    if (flashTimer.current) clearTimeout(flashTimer.current);
    flashTimer.current = setTimeout(() => setValFlash(false), 1700);
  }

  useEffect(() => () => {
    if (flashTimer.current) clearTimeout(flashTimer.current);
  }, []);

  if (error && !doc) {
    return (
      <div>
        <PageHeader title="Extraction result" />
        <div className="panel">
          <ErrorState title="Document unavailable" message={error} requestId={errorRef || undefined} onRetry={() => { setError(""); setErrorRef(""); setDirty((n) => n + 1); }} />
          <p><a href="#/records">Back to documents</a></p>
        </div>
      </div>
    );
  }

  if (!doc || !extraction || !validation || shownId !== documentId) {    return (
      <div>
        <PageHeader title="Extraction result" />
        <div className="extract-grid" aria-hidden="true">
          <div className="panel"><Skeleton lines={5} /></div>
          <div className="panel"><Skeleton lines={8} /></div>
        </div>
      </div>
    );
  }

  // UX-only role note: the review/audit destinations explain permissions
  // themselves; the backend still enforces every action.
  const role = getUser() ? getUser().role : "";
  const canReview = role === "operator" || role === "admin";

  return (
    <div>
      <PageHeader
        title="Extraction result"
        sub={doc.file_name}
        meta={
          <>
            <span>Doc <code className="tnum">{doc.id.slice(0, 8)}…</code></span>
            <span>SHA <code className="tnum">{doc.checksum ? `${doc.checksum.slice(0, 12)}…` : "—"}</code></span>
            <StatusBadge tone={statusTone(doc.processing_status)}>{statusLabel(doc.processing_status)}</StatusBadge>
            {error && <span>{error}</span>}
          </>
        }
      />
      <ResultBanner docStatus={doc.processing_status} validationStatus={validation.status} />
      <div className="extract-grid">
        <DocumentViewer document={doc} />

        <div className="panel">
          <div className="panel-head">
            <div>
              <h2>Extracted record ({extraction.fields.length} fields)</h2>
              <p className="panel-sub">Each value with how confident the system is, and whether it passed verification.</p>
            </div>
          </div>

          <RecordFields
            fields={extraction.fields}
            evidenceFor={evidenceFor}
            onToggleEvidence={setEvidenceFor}
          />

          <div ref={validationRef} className={`validation-anchor${valFlash ? " val-flash" : ""}`}>
            <div className="panel-head validation-head">
              <div>
                <h2>Validation</h2>
                <p className="panel-sub">Based on fixed verification rules.</p>
              </div>
            </div>
            <ValidationSummary status={validation.status} issues={validation.issues} />
          </div>

          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Record summary</h2>
                <p className="panel-sub">Human-readable highlights. The full technical payload stays one click away via Export JSON.</p>
              </div>
            </div>
            <RecordSummary
              rows={summaryRows(
                new Map(extraction.fields.map((f) => [f.field_name, f])),
                doc,
                validation,
                reviewTask === undefined
                  ? undefined
                  : reviewTask
                    ? `Open — ${reviewTask.status}`
                    : "No open review",
              )}
            />
          </div>

          <div className="extract-actions">
            <Button variant="secondary" onClick={downloadExport} disabled={exporting}>
              {exporting ? "Exporting…" : "Export JSON"}
            </Button>
            {extraction.record_id && (
              <a href={`#/record/${extraction.record_id}`}>Open review / adjudicate →</a>
            )}
            {extraction.record_id && (
              <a href={`#/record/${extraction.record_id}/audit`}>View audit</a>
            )}
            <Button variant="secondary" onClick={scrollToValidation}>View validation</Button>
          </div>
          {!canReview && extraction.record_id && (
            <p className="muted">Review, audit, and approval need an operator account — you are signed in as {role || "user"}.</p>
          )}
        </div>
      </div>
    </div>
  );
}
