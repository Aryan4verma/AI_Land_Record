/** Decoupled record-page loading. The record itself is PRIMARY: only its
 * failure decides between the not-found and server-error states. Audit,
 * extraction/validation, and review-task lookups are SECONDARY — each fails
 * independently into its own state and can never sink the record view.
 * In particular an audit 403 (read-only `user` role, by backend design) becomes
 * `auditState: "forbidden"` (a permission state), never "record unavailable".
 *
 * `api` is the injected client surface (getRecord, getRecordAudit,
 * getExtraction, getDocumentValidation, listReviews, getReview, createReview
 * is NOT used here) so tests can stub every layer: record 200 + audit 403,
 * record 404, network failures, and full operator loads.
 * Messages are user-facing (central friendlyMessage mapping); backend
 * request IDs ride alongside for the muted reference line.
 */
import { friendlyMessage, requestIdOf } from "./errors.js";
export function isAbortError(err) {
  return err instanceof DOMException && err.name === "AbortError";
}

/**
 * @typedef {Object} RecordPageResult
 * @property {boolean} aborted
 * @property {any} record
 * @property {{ kind: "not-found" | "server", message: string } | null} recordError
 * @property {string} recordRequestId
 * @property {any[]} audit
 * @property {"ok" | "forbidden" | "error"} auditState
 * @property {string} auditError
 * @property {string} auditRequestId
 * @property {any} extraction
 * @property {any} validation
 * @property {string} taskId
 * @property {any} review
 * @property {"ok" | "forbidden" | "error"} tasksState
 * @property {string} tasksError
 */

/**
 * @param {Record<string, (id: string, opts?: any) => Promise<any>>} api
 * @param {string} recordId
 * @param {AbortSignal | null | undefined} [signal]
 * @param {{ includeTasks?: boolean }} [options]
 * @returns {Promise<RecordPageResult>}
 */
export async function loadRecordPage(api, recordId, signal, options = {}) {
  const includeTasks = options.includeTasks !== false;
  const out = {
    aborted: false,
    record: null,
    recordError: null,
    recordRequestId: "",
    audit: [],
    auditState: "ok",
    auditError: "",
    auditRequestId: "",
    extraction: null,
    validation: null,
    taskId: "",
    review: null,
    tasksState: "ok",
    tasksError: "",
  };

  // PRIMARY — the only call that can fail the whole page.
  let detail;
  try {
    detail = await api.getRecord(recordId, { signal });
  } catch (err) {
    if (isAbortError(err) || (signal && signal.aborted)) return { ...out, aborted: true };
    out.recordError = {
      kind: err && err.status === 404 ? "not-found" : "server",
      message: friendlyMessage(err),
    };
    out.recordRequestId = requestIdOf(err);
    return out;
  }
  if (signal && signal.aborted) return { ...out, aborted: true };
  out.record = detail;

  // SECONDARY — audit trail. A 403 is the designed read-only outcome and
  // becomes a permission state; anything else is a plain load error.
  try {
    out.audit = await api.getRecordAudit(recordId, { signal });
  } catch (err) {
    if (isAbortError(err) || (signal && signal.aborted)) return { ...out, aborted: true };
    out.audit = [];
    out.auditState = err && err.status === 403 ? "forbidden" : "error";
    out.auditError = friendlyMessage(err);
    out.auditRequestId = requestIdOf(err);
  }

  // SECONDARY — extraction + validation for the source document. Best
  // effort, exactly as before: failure leaves both null, silently.
  if (detail.document) {
    try {
      const [ex, val] = await Promise.all([
        api.getExtraction(detail.document.id, { signal }),
        api.getDocumentValidation(detail.document.id, { signal }),
      ]);
      if (signal && signal.aborted) return { ...out, aborted: true };
      out.extraction = ex;
      out.validation = val;
    } catch (err) {
      if (isAbortError(err) || (signal && signal.aborted)) return { ...out, aborted: true };
      out.extraction = null;
      out.validation = null;
    }
  }

  // SECONDARY — this record's open review task plus its backend detail.
  // Read-only users are forbidden from listing tasks (403 by design): that only
  // means no task is visible, never a page failure.
  if (includeTasks) {
    try {
      const [pending, inReview] = await Promise.all([
        api.listReviews("PENDING", { signal }),
        api.listReviews("IN_REVIEW", { signal }),
      ]);
      if (signal && signal.aborted) return { ...out, aborted: true };
      const mine = [...pending, ...inReview].find((t) => t.land_record_id === recordId);
      out.taskId = mine ? mine.id : "";
      if (mine) {
        try {
          const review = await api.getReview(mine.id, { signal });
          if (signal && signal.aborted) return { ...out, aborted: true };
          out.review = review;
        } catch {
          // Review detail stays advisory; record state remains authoritative.
          if (!signal || !signal.aborted) out.review = null;
        }
      }
    } catch (err) {
      if (isAbortError(err) || (signal && signal.aborted)) return { ...out, aborted: true };
      out.taskId = "";
      out.review = null;
      out.tasksState = err && err.status === 403 ? "forbidden" : "error";
      out.tasksError = friendlyMessage(err);
    }
  }

  return out;
}
