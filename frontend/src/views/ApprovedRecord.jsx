import { useEffect, useState } from "react";
import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
import EmptyState from "../components/EmptyState.jsx";
import ErrorState from "../components/ErrorState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import RecordFields from "../components/RecordFields.jsx";
import RecordSummary from "../components/RecordSummary.jsx";
import Skeleton from "../components/Skeleton.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import StatCard from "../components/StatCard.jsx";
import ValidationSummary from "../components/ValidationSummary.jsx";
import { downloadJson } from "../components/format.js";
import { friendlyMessage, requestIdOf } from "../components/errors.js";
import { exportRecord, getRecord } from "../api/client";
import { statusLabel, statusTone } from "../api/types";

/** Approved record (route #/record/:id/approved) — Stitch 4feece87 on the
 * real record detail response. Approval strip shows backend facts only
 * (reviewer id, timestamp, document hash); per-field confidence badges
 * replace any aggregate accuracy claim, and no legal-ownership statement
 * is made anywhere. Non-approved records get an honest state, never a
 * fabricated approval. Export uses the canonical backend JSON with
 * exporting/success/failure states.
 */
export default function ApprovedRecord({ recordId }) {
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");
  const [errorRef, setErrorRef] = useState("");
  const [exportState, setExportState] = useState("idle");
  const [exportError, setExportError] = useState("");
  const [dirty, setDirty] = useState(0);

  function isAbort(err) {
    return err instanceof DOMException && err.name === "AbortError";
  }

  useEffect(() => {
    const controller = new AbortController();
    const signal = controller.signal;
    // GET /api/v1/records/{id} — record + extracted fields + validation +
    // source document in one call. Failure replaces everything (ErrorState).
    getRecord(recordId, { signal })
      .then((d) => {
        if (signal.aborted) return;
        setDetail(d);
        setError("");
      })
      .catch((err) => {
        if (isAbort(err) || signal.aborted) return;
        setError(friendlyMessage(err));
        setErrorRef(requestIdOf(err));
      });
    return () => controller.abort();
  }, [recordId, dirty]);

  async function download() {
    if (exportState === "exporting") return; // duplicate click: ignore
    setExportState("exporting");
    setExportError("");
    try {
      const payload = await exportRecord(recordId);
      downloadJson(`record-${recordId.slice(0, 8)}.json`, payload);
      setExportState("done");
    } catch (err) {
      setExportState("error");
      setExportError(friendlyMessage(err));
    }
  }

  if (error && !detail) {
    return (
      <div>
        <PageHeader title="Approved record" />
        <div className="panel">
          <ErrorState title="Record unavailable" message={error} requestId={errorRef || undefined} onRetry={() => { setError(""); setErrorRef(""); setDirty((n) => n + 1); }} />
          <p><a href="#/records">Back to documents</a></p>
        </div>
      </div>
    );
  }

  if (!detail) {
    return (
      <div>
        <PageHeader title="Approved record" />
        <div className="panel"><Skeleton lines={8} /></div>
      </div>
    );
  }

  const { record, extracted_fields: fields, validation, document } = detail;

  if (record.status !== "APPROVED") {
    return (
      <div>
        <PageHeader title="Approved record" />
        <div className="panel">
          <EmptyState title="Record is not approved">
            This record is currently {record.status}. The approved-record view unlocks after approval.
          </EmptyState>
          <p><a href={`#/record/${record.id}`}>Open review workspace</a></p>
        </div>
      </div>
    );
  }

  const issues = validation || [];

  return (
    <div className="vstack">
      <PageHeader
        title="Approved record"
        sub={document ? document.file_name : ""}
        meta={
          <>
            <span>Record <code className="tnum">{record.id.slice(0, 8)}…</code></span>
            <StatusBadge tone={statusTone(record.status)}>{statusLabel(record.status)}</StatusBadge>
          </>
        }
        actions={
          <div className="review-top-actions">
            {document && <a href={`#/document/${document.id}/extract`}>View source document</a>}
            <a href={`#/record/${record.id}/audit`}>View audit</a>
          </div>
        }
      />

      {exportState === "done" && <Alert tone="success" title="Export complete">The record file has been downloaded.</Alert>}
      {exportState === "error" && <Alert tone="error" title="Export failed">{exportError}</Alert>}

      <div className="stat-grid">
        <StatCard
          label="Approved by"
          value={record.approved_by ? `${record.approved_by.slice(0, 8)}…` : "—"}
          sub="Reviewer ID from the approval event"
        />
        <StatCard
          label="Approved at"
          value={record.approved_at ? new Date(record.approved_at).toLocaleString() : "—"}
          sub="Approval timestamp"
        />
        <StatCard
          label="Document SHA-256"
          value={document && document.checksum ? `${document.checksum.slice(0, 12)}…` : "—"}
          sub="Source bytes fingerprint"
        />
      </div>

      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Record summary</h2>
            <p className="panel-sub">Human-readable highlights. The full technical payload stays one click away via Export JSON.</p>
          </div>
        </div>
        <RecordSummary
          rows={[
            { label: "Record status", value: <StatusBadge tone={statusTone(record.status)}>{statusLabel(record.status)}</StatusBadge> },
            { label: "Owner", value: record.owner_name },
            { label: "Survey number", value: record.survey_number },
            { label: "Area", value: record.area === null || record.area === undefined ? null : `${record.area}${record.area_unit ? ` ${record.area_unit}` : ""}` },
            { label: "Village", value: record.village },
            { label: "Tehsil", value: record.tehsil },
            { label: "District", value: record.district },
            { label: "Validation", value: issues.length === 0 ? "Passed" : `${issues.length} issue${issues.length === 1 ? "" : "s"}` },
            { label: "Approved by", value: record.approved_by ? `${record.approved_by.slice(0, 8)}…` : null },
            { label: "Approved at", value: record.approved_at ? new Date(record.approved_at).toLocaleString() : null },
            { label: "Last updated", value: record.updated_at ? new Date(record.updated_at).toLocaleString() : null },
          ]}
        />
        <div className="extract-actions">
          <Button variant="primary" disabled={exportState === "exporting"} onClick={download}>
            {exportState === "exporting" ? "Exporting…" : "Export JSON"}
          </Button>
        </div>
      </div>

      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Final structured record</h2>
            <p className="panel-sub">
              Values verified by the authorized reviewer. Approval records the verification
              decision — it does not certify legal ownership.
            </p>
          </div>
        </div>
        <RecordFields fields={fields} />
      </div>

      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Validation summary</h2>
            <p className="panel-sub">Checks recorded at the time of approval.</p>
          </div>
        </div>
        {issues.length === 0 && <Alert tone="success" title="No issues">Every verification check passed.</Alert>}
        {issues.length > 0 && <ValidationSummary issues={issues} />}
      </div>
    </div>
  );
}
