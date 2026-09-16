/**
 * Record-page load orchestration tests. Node environment, injected stub API
 * — proves the primary/secondary split: a forbidden secondary (audit 403)
 * can never sink the record view, 404 stays not-found, and the full
 * operator load still populates everything.
 */
import { describe, expect, it } from "vitest";

const { loadRecordPage } = await import("../components/recordLoad.js");

const RECORD = { id: "r1", status: "REVIEW_REQUIRED", document: { id: "d1" } };

function apiStub(overrides = {}) {
  const calls: string[] = [];
  const api = {
    getRecord: async () => {
      calls.push("getRecord");
      return RECORD;
    },
    getRecordAudit: async () => {
      calls.push("getRecordAudit");
      return [{ id: "a1" }];
    },
    getExtraction: async () => {
      calls.push("getExtraction");
      return { fields: [] };
    },
    getDocumentValidation: async () => {
      calls.push("getDocumentValidation");
      return { status: "READY", issues: [] };
    },
    listReviews: async () => {
      calls.push("listReviews");
      return [];
    },
    getReview: async () => {
      calls.push("getReview");
      return { verdict: "READY", approval_blocked: false };
    },
    ...overrides,
  };
  return { api, calls };
}

function httpError(status: number, message: string) {
  const err = new Error(message) as Error & { status: number };
  err.status = status;
  return err;
}

describe("loadRecordPage (primary/secondary split)", () => {
  it("record 200 + audit 403 renders the record with a permission state", async () => {
    const { api } = apiStub({ getRecordAudit: async () => { throw httpError(403, "INSUFFICIENT_ROLE: denied"); } });
    const res = await loadRecordPage(api, "r1", null);
    expect(res.aborted).toBe(false);
    expect(res.record).toEqual(RECORD);
    expect(res.recordError).toBeNull();
    expect(res.audit).toEqual([]);
    expect(res.auditState).toBe("forbidden");
  });

  it("record 404 is not-found and stops before secondary calls", async () => {
    const { api, calls } = apiStub({ getRecord: async () => { throw httpError(404, "RECORD_NOT_FOUND"); } });
    const res = await loadRecordPage(api, "missing", null);
    expect(res.record).toBeNull();
    expect(res.recordError?.kind).toBe("not-found");
    expect(res.recordError?.message).toBe("The requested record could not be found.");
    expect(calls).toEqual([]);
  });

  it("record 500 and network failures are server errors", async () => {
    const { api } = apiStub({ getRecord: async () => { throw httpError(500, "boom"); } });
    const res = await loadRecordPage(api, "r1", null);
    expect(res.recordError?.kind).toBe("server");
    const { api: api2 } = apiStub({ getRecord: async () => { throw new TypeError("Failed to fetch"); } });
    const res2 = await loadRecordPage(api2, "r1", null);
    expect(res2.recordError?.kind).toBe("server");
  });

  it("audit 500 keeps the record with an error state", async () => {
    const { api } = apiStub({ getRecordAudit: async () => { throw httpError(500, "db down"); } });
    const res = await loadRecordPage(api, "r1", null);
    expect(res.record).toEqual(RECORD);
    expect(res.auditState).toBe("error");
    expect(res.auditError).toBe("The server encountered a problem. Please try again.");
  });

  it("tasks-list 403 (operator) keeps record and task lookup silent", async () => {
    const { api } = apiStub({ listReviews: async () => { throw httpError(403, "INSUFFICIENT_ROLE"); } });
    const res = await loadRecordPage(api, "r1", null);
    expect(res.record).toEqual(RECORD);
    expect(res.taskId).toBe("");
    expect(res.review).toBeNull();
    expect(res.tasksState).toBe("forbidden");
  });

  it("extraction failure degrades to nulls with the record intact", async () => {
    const { api } = apiStub({
      getExtraction: async () => { throw httpError(404, "EXTRACTION_NOT_FOUND"); },
      getDocumentValidation: async () => { throw httpError(404, "EXTRACTION_NOT_FOUND"); },
    });
    const res = await loadRecordPage(api, "r1", null);
    expect(res.record).toEqual(RECORD);
    expect(res.extraction).toBeNull();
    expect(res.validation).toBeNull();
  });

  it("operator full load populates task, review, and audit", async () => {
    const task = { id: "t1", land_record_id: "r1" };
    const { api } = apiStub({
      listReviews: async (status: string) => (status === "PENDING" ? [task] : []),
      getReview: async () => ({ verdict: "NEEDS_REVIEW", approval_blocked: true }),
    });
    const res = await loadRecordPage(api, "r1", null);
    expect(res.recordError).toBeNull();
    expect(res.auditState).toBe("ok");
    expect(res.taskId).toBe("t1");
    expect(res.review?.approval_blocked).toBe(true);
  });

  it("failing review detail stays advisory with the task kept", async () => {
    const { api } = apiStub({
      listReviews: async () => [{ id: "t9", land_record_id: "r1" }],
      getReview: async () => { throw httpError(403, "denied"); },
    });
    const res = await loadRecordPage(api, "r1", null);
    expect(res.taskId).toBe("t9");
    expect(res.review).toBeNull();
  });

  it("aborted signal short-circuits without states", async () => {
    const { api, calls } = apiStub();
    const controller = new AbortController();
    controller.abort();
    const res = await loadRecordPage(api, "r1", controller.signal);
    expect(res.aborted).toBe(true);
    expect(res.record).toBeNull();
    expect(calls).toEqual(["getRecord"]);
  });

  it("includeTasks:false skips the task lookup (audit view)", async () => {
    const { api, calls } = apiStub();
    const res = await loadRecordPage(api, "r1", null, { includeTasks: false });
    expect(calls).not.toContain("listReviews");
    expect(res.record).toEqual(RECORD);
  });
});
