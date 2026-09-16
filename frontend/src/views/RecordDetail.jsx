import { describeAuditEvent } from "../components/audit.js";
import { timeAgo } from "../components/format.js";
import { useEffect, useRef, useState } from "react";
import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
import DataTable from "../components/DataTable.jsx";
import DocumentViewer from "../components/DocumentViewer.jsx";
import EmptyState from "../components/EmptyState.jsx";
import ErrorState from "../components/ErrorState.jsx";
import Modal from "../components/Modal.jsx";
import PageHeader from "../components/PageHeader.jsx";
import ReviewField from "../components/ReviewField.jsx";
import Skeleton from "../components/Skeleton.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import TextInput from "../components/TextInput.jsx";
import ValidationSummary from "../components/ValidationSummary.jsx";
import {
  approveRecord,
  completeReview,
  correctField,
  createReview,
  createSubmitGuard,
  getDocumentValidation,
  getExtraction,
  getRecord,
  getRecordAudit,
  getReview,
  getUser,
  listReviews,
  rejectRecord,
} from "../api/client";
import { FIELD_GROUPS, correctionValue, isTerminalRecord } from "../api/fields";
import { friendlyMessage, requestIdOf } from "../components/errors.js";
import { loadRecordPage } from "../components/recordLoad.js";
import { statusLabel, statusTone } from "../api/types";
import "../styles/review.css";

function hasEvidence(f) {
  if (!f) return false;
  return (
    (f.bounding_box !== null && f.bounding_box !== undefined) ||
    Boolean(f.source_text) ||
    (f.source_page !== null && f.source_page !== undefined)
  );
}

/** Human review workspace (route #/record/:id) — Stitch a002d440 two-pane
 * layout on the verified review workflow. AI assists, the human verifies,
 * the system records: every mutation goes through the real correction /
 * complete / approve / reject endpoints and the view reloads authoritative
 * state afterward. No approval logic lives here — the backend alone decides
 * (409s surface verbatim). The backend exposes no record versioning, so
 * concurrent edits resolve last-write-wins; drafts are component-local and
 * never cleared by reloads.
 */
/** A record is identified by what it describes, not by its internal id.
 * Falls back through owner -> survey number -> village so the header is
 * never empty, and only uses the id when the record carries nothing else. */
function recordTitle(record) {
  const owner = (record.owner_name || "").trim();
  const survey = (record.survey_number || "").trim();
  if (owner && survey) return `${owner} · ${survey}`;
  if (owner) return owner;
  if (survey) return `Survey ${survey}`;
  const village = (record.village || "").trim();
  if (village) return `Record in ${village}`;
  return "Land record";
}

export default function RecordDetail({ recordId }) {
  const [detail, setDetail] = useState(null);
  const [extraction, setExtraction] = useState(null);
  const [validation, setValidation] = useState(null);
  const [audit, setAudit] = useState([]);
  const [auditState, setAuditState] = useState("ok");
  const [tasksNotice, setTasksNotice] = useState("");
  const [taskId, setTaskId] = useState("");
  const [review, setReview] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [errorRef, setErrorRef] = useState("");
  const [notFound, setNotFound] = useState(false);
  const [modal, setModal] = useState(null);
  const [rejectReason, setRejectReason] = useState("");
  const [mutating, setMutating] = useState(false);
  // Aborts in-flight loads when recordId changes or the view unmounts,
  // so stale responses can never overwrite current state.
  const abortRef = useRef(null);
  // Synchronous double-submit guards (busy state alone races same-tick clicks).
  const correctGuard = useRef(null);
  if (!correctGuard.current) correctGuard.current = createSubmitGuard();
  const completeGuard = useRef(null);
  if (!completeGuard.current) completeGuard.current = createSubmitGuard();
  const decideGuard = useRef(null);
  if (!decideGuard.current) decideGuard.current = createSubmitGuard();

  async function load() {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const signal = controller.signal;
    setError("");
    setErrorRef("");
    setMessage("");
    setNotFound(false);
    // Decoupled orchestration: the record is primary (404 vs server error
    // decided here alone); audit/tasks/extraction degrade independently,
    // so an audit 403 can never sink the record view again.
    const api = { getRecord, getRecordAudit, getExtraction, getDocumentValidation, listReviews, getReview };
    const res = await loadRecordPage(api, recordId, signal);
    if (res.aborted || controller.signal.aborted) return;
    if (res.recordError) {
      setDetail(null);
      setNotFound(res.recordError.kind === "not-found");
      setError(res.recordError.message);
      setErrorRef(res.recordRequestId);
      return;
    }
    setDetail(res.record);
    setAudit(res.audit);
    setAuditState(res.auditState);
    setExtraction(res.extraction);
    setValidation(res.validation);
    setTaskId(res.taskId);
    setReview(res.review);
    setTasksNotice(res.tasksState === "error" ? res.tasksError : "");
  }

  useEffect(() => {
    load();
    return () => abortRef.current?.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recordId]);

  async function ensureReview(reason) {
    // POST /api/v1/reviews {land_record_id, reason, priority}
    const t = await createReview({ land_record_id: recordId, reason: reason || "QA review", priority: "MEDIUM" });
    setTaskId(t.id);
    return t.id;
  }

  async function saveCorrection(name, draft, reason) {
    if (!correctGuard.current.tryAcquire()) return; // duplicate click: ignore
    setMutating(true);
    try {
      const tid = taskId || (await ensureReview(reason));
      // PATCH /api/v1/reviews/{id}/fields/{field} {value, reason};
      // empty input clears the value (null). The backend revalidates and
      // persists; this view then reloads everything authoritative.
      await correctField(tid, name, { value: correctionValue(draft), reason });
      setMessage(`Corrected ${name}. Validation re-ran.`);
      await load();
    } finally {
      correctGuard.current.release();
      setMutating(false);
    }
  }

  async function complete() {
    if (!taskId || !completeGuard.current.tryAcquire()) return;
    setMutating(true);
    setError("");
    setErrorRef("");
    try {
      // POST /api/v1/reviews/{id}/complete — backend permits or rejects (409)
      await completeReview(taskId);
      setMessage("Review completed.");
      await load();
    } catch (err) {
      setError(friendlyMessage(err));
      setErrorRef(requestIdOf(err));
    } finally {
      completeGuard.current.release();
      setMutating(false);
    }
  }

  async function decide(kind, reason) {
    if (!decideGuard.current.tryAcquire()) return; // duplicate click: ignore
    setMutating(true);
    setError("");
    setErrorRef("");
    try {
      // POST /api/v1/records/{id}/approve | /reject — the backend alone
      // decides whether the record is approvable; its verdict is displayed,
      // never computed here.
      const res =
        kind === "approve"
          ? await approveRecord(recordId, reason || undefined)
          : await rejectRecord(recordId, reason);
      setMessage(`Record ${statusLabel(res.status).toLowerCase()}.`);
      setModal(null);
      if (kind === "approve") {
        // The approved-record route now exists — continue there.
        window.location.hash = `#/record/${recordId}/approved`;
        return;
      }
      await load();
    } catch (err) {
      setError(friendlyMessage(err));
      setErrorRef(requestIdOf(err));
    } finally {
      decideGuard.current.release();
      setMutating(false);
    }
  }

  if (!detail && !error) {
    return (
      <div>
        <PageHeader title="Review record" />
        <div className="extract-grid" aria-hidden="true">
          <div className="panel"><Skeleton lines={5} /></div>
          <div className="panel"><Skeleton lines={8} /></div>
        </div>
      </div>
    );
  }

  if (!detail) {
    return (
      <div>
        <PageHeader title="Review record" />
        <div className="panel">
          <ErrorState
            title={notFound ? "Record not found" : "Record unavailable"}
            message={error}
            requestId={errorRef || undefined}
            onRetry={load}
          />
        </div>
      </div>
    );
  }

  const record = detail.record;
  const terminal = isTerminalRecord(record.status);
  // UX-only role gating: the backend still enforces every mutation.
  // Read-only users see values; review actions explain the operator requirement
  // instead of navigating into guaranteed 403s.
  const role = getUser() ? getUser().role : "";
  const canReview = role === "operator" || role === "admin";
  const extractedByName = new Map((extraction ? extraction.fields : []).map((f) => [f.field_name, f]));
  const corrections = audit.filter((a) => a.action === "FIELD_CORRECTED").length;
  const blocking = validation
    ? validation.issues.filter((i) => i.severity === "ERROR" || i.severity === "CRITICAL").length
    : 0;

  return (
    <div>
      <PageHeader
        title={recordTitle(record)}
        sub={record.document ? record.document.file_name : ""}
        meta={
          <>
            <StatusBadge tone={statusTone(record.status)}>{statusLabel(record.status)}</StatusBadge>
            {review && <span>Check result: {statusLabel(review.verdict)}</span>}
            {taskId && <span>Review <code className="tnum">{taskId.slice(0, 8)}…</code></span>}
          </>
        }
        actions={!terminal && canReview && (
          <div className="review-top-actions">
            <Button variant="secondary" disabled={mutating} onClick={() => { setRejectReason(""); setModal("reject"); }}>
              Reject
            </Button>
            <Button variant="primary" disabled={mutating} onClick={() => setModal("approve")}>
              Approve record
            </Button>
          </div>
        )}
      />

      {message && <Alert tone="success">{message}</Alert>}
      {error && <Alert tone="error" title="Request failed">{error}</Alert>}
      {!terminal && !canReview && (
        <Alert tone="info" title="Operator role required">
          You are signed in as {role || "a read-only role"}. Record values below are read-only for
          you — corrections, review completion, and approve/reject need an operator account. The
          backend enforces this on every action.
        </Alert>
      )}
      {terminal && (
        <Alert tone="info" title={`Record ${statusLabel(record.status).toLowerCase()}`}>
          This record is final and can no longer be changed.{" "}
          {record.status === "APPROVED" && <a href={`#/record/${record.id}/approved`}>View approved record</a>}
        </Alert>
      )}
      {review && review.approval_blocked && !terminal && (
        <Alert tone="error" title="Approval is currently blocked by the backend">
          Correct the flagged fields first — the approve call will otherwise be rejected.
        </Alert>
      )}

      <div className="extract-grid">
        <div className="vstack">
          {detail.document && <DocumentViewer document={detail.document} />}
        </div>

        <div className="vstack">
          {FIELD_GROUPS.map((group) => (
            <div key={group.title} className="panel">
              <div className="panel-head">
                <div>
                  <h2>{group.title}</h2>
                </div>
              </div>
              {group.fields.map((name) => {
                const f = extractedByName.get(name);
                return (
                  <ReviewField
                    key={name}
                    name={name}
                    value={record[name]}
                    confidence={f ? f.confidence : null}
                    validationStatus={f ? f.validation_status : null}
                    evidence={f && hasEvidence(f) ? f : null}
                    disabled={mutating || terminal || !canReview}
                    onSave={saveCorrection}
                  />
                );
              })}
            </div>
          ))}

          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Validation</h2>
                <p className="panel-sub">Based on fixed verification rules.</p>
              </div>
              {canReview && (
                <Button variant="secondary" disabled={!taskId || mutating} onClick={complete}>
                  {mutating ? "Working…" : "Complete review"}
                </Button>
              )}
            </div>
            {tasksNotice && <p className="muted">Open review tasks could not be checked: {tasksNotice}</p>}
            {!validation && <p className="muted">No validation result for this record.</p>}
            {validation && <ValidationSummary status={validation.status} issues={validation.issues} />}
          </div>

          <div className="panel">
            <div className="panel-head">
              <div>
                <h2>Audit history</h2>
                <p className="panel-sub">Every decision recorded by the system. <a href={`#/record/${record.id}/audit`}>Open full audit trail</a></p>
              </div>
            </div>
            {auditState === "forbidden" && (
              <Alert tone="info" title="Audit history needs the operator role">
                You are signed in as {role || "a read-only role"}. The audit trail stays enforced
                server-side — switch to an operator account to inspect it.
              </Alert>
            )}
            {auditState !== "forbidden" && audit.length === 0 && <EmptyState title="No audit entries" />}
            {auditState !== "forbidden" && audit.length > 0 && (
              <DataTable columns={["Activity", "By", "Change", "When"]}>
                {audit.map((a) => {
                  const e = describeAuditEvent(a);
                  return (
                    <tr key={a.id}>
                      <td>
                        <span className="t-value">{e.title}</span>
                        {e.description && <div className="t-meta">{e.description}</div>}
                      </td>
                      <td className="muted">{e.source}</td>
                      <td>
                        {e.changes
                          ? e.changes.map((c) => (
                              <div key={c.label} className="t-meta">
                                {c.old} → <b>{c.neu}</b>
                              </div>
                            ))
                          : <span className="t-absent">—</span>}
                      </td>
                      <td className="muted" title={a.timestamp}>{timeAgo(a.timestamp)}</td>
                    </tr>
                  );
                })}
              </DataTable>
            )}
          </div>
        </div>
      </div>

      {modal === "approve" && (
        <Modal
          title="Approve this record?"
          confirmLabel="Approve & commit record"
          busy={mutating}
          onCancel={() => { if (!mutating) setModal(null); }}
          onConfirm={() => decide("approve", "")}
        >
          <p>
            Approval confirms that you, the authorized reviewer, have reviewed and accepted
            the current record. It does not certify legal ownership — it records your
            verification decision in the audit journal.
          </p>
          <div className="modal-facts">
            {extraction ? extraction.fields.length : 0} fields extracted • {corrections} manual correction(s) logged • {blocking} unresolved blocking discrepanc{blocking === 1 ? "y" : "ies"}
          </div>
          {review && review.approval_blocked && (
            <p><b>This record cannot be approved yet.</b> Resolve the items flagged for attention first.</p>
          )}
        </Modal>
      )}

      {modal === "reject" && (
        <Modal
          title="Reject record adjudication"
          confirmLabel="Reject record"
          danger
          busy={mutating}
          confirmDisabled={rejectReason.trim() === ""}
          onCancel={() => { if (!mutating) { setModal(null); setRejectReason(""); } }}
          onConfirm={() => decide("reject", rejectReason.trim())}
        >
          <p>Rejecting returns this record for re-scan or archival retrieval. A reason is required for audit documentation.</p>
          <TextInput
            label="Rejection reason"
            hint="Required"
            id="reject-reason"
            value={rejectReason}
            disabled={mutating}
            placeholder="e.g. Illegible archival scan"
            onChange={(e) => setRejectReason(e.target.value)}
          />
        </Modal>
      )}
    </div>
  );
}
