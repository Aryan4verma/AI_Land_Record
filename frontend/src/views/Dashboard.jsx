import { useEffect, useRef, useState } from "react";
import DataTable from "../components/DataTable.jsx";
import EmptyState from "../components/EmptyState.jsx";
import ErrorState from "../components/ErrorState.jsx";
import { timeAgo } from "../components/format.js";
import { friendlyMessage, requestIdOf } from "../components/errors.js";
import PageHeader from "../components/PageHeader.jsx";
import Skeleton from "../components/Skeleton.jsx";
import StatCard from "../components/StatCard.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { getDashboardSummary, getDashboardValidation, searchRecords } from "../api/client";
import { statusLabel, statusTone } from "../api/types";

function sumCounts(map) {
  return Object.values(map || {}).reduce((a, b) => a + (Number(b) || 0), 0);
}

/** Stitch Dashboard (577666b56d964c3f81e8e4b089e99447) on live backend
 * aggregates. Every number comes from /api/v1/dashboard/* or /records;
 * sections without a backend source render an empty state, never fiction.
 */
export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [errorRef, setErrorRef] = useState("");
  const [dirty, setDirty] = useState(0);
  const abortRef = useRef(null);

  function isAbort(err) {
    return err instanceof DOMException && err.name === "AbortError";
  }

  useEffect(() => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const signal = controller.signal;
    const opts = { signal };
    // One parallel load per mount: summary + validation + latest records.
    // (documents_by_status already carries pipeline counts, so the
    // processing endpoint would only duplicate data — it is not fetched.)
    Promise.all([
      getDashboardSummary(opts),
      getDashboardValidation(opts),
      searchRecords({ page: 1, limit: 8 }, opts),
    ])
      .then(([summary, validation, records]) => {
        if (signal.aborted) return;
        setData({ summary, validation, records, syncedAt: new Date() });
      })
      .catch((err) => {
        if (isAbort(err) || signal.aborted) return;
        setError(friendlyMessage(err));
        setErrorRef(requestIdOf(err));
      });
    return () => controller.abort();
  }, [dirty]);

  if (error && !data) {
    return (
      <div>
        <PageHeader title="Dashboard" sub="Monitor document processing, cadastral validation, and officer review activity." />
        <div className="panel">
          <ErrorState title="Dashboard unavailable" message={error} requestId={errorRef || undefined} onRetry={() => { setError(""); setErrorRef(""); setData(null); setDirty((n) => n + 1); }} />
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div>
        <PageHeader title="Dashboard" sub="Monitor document processing, cadastral validation, and officer review activity." />
        <div className="stat-grid" aria-hidden="true">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="stat"><Skeleton lines={2} /></div>
          ))}
        </div>
        <div className="panel">
          <Skeleton lines={5} />
        </div>
      </div>
    );
  }

  const { summary, validation, records, syncedAt } = data;
  const recordsTotal = sumCounts(summary.records_by_status);
  const approved = summary.records_by_status.APPROVED || 0;
  const issuesTotal = sumCounts(validation.issues_by_severity);
  const avgConf = summary.average_confidence === null || summary.average_confidence === undefined
    ? "—"
    : `${Math.round(summary.average_confidence * 100)}%`;
  const processing = summary.documents_by_status.PROCESSING || 0;
  const uploaded = summary.documents_by_status.UPLOADED || 0;

  return (
    <div className="vstack">
      <PageHeader
        title="Dashboard"
        sub="What needs attention, and what the workspace has processed."
        meta={<span>Updated {timeAgo(syncedAt.toISOString())}</span>}
      />

      <div className="stat-grid">
        {/* Outstanding work leads, and each count links to the work itself. */}
        <StatCard
          label="Needs review"
          value={String(summary.open_reviews)}
          sub={summary.open_reviews === 1 ? "record waiting for an officer"
                                          : "records waiting for an officer"}
          tone={summary.open_reviews > 0 ? "review" : "neutral"}
          href="#/reviews"
          hint="Open the review queue"
        />
        <StatCard
          label="Flagged"
          value={String(validation.blocked_documents)}
          sub={`${issuesTotal} open ${issuesTotal === 1 ? "issue" : "issues"} to resolve`}
          tone={validation.blocked_documents > 0 ? "failed" : "neutral"}
          href="#/records?status=VALIDATION_FAILED"
          hint="Show flagged records"
        />
        <StatCard
          label="Approved"
          value={String(approved)}
          sub={`of ${recordsTotal} ${recordsTotal === 1 ? "record" : "records"}`}
          tone={approved > 0 ? "verified" : "neutral"}
        />
        <StatCard
          label="Documents"
          value={String(summary.documents_total)}
          sub={avgConf === "—" ? "processed so far" : `average confidence ${avgConf}`}
          href="#/records"
          hint="Browse all records"
        />
      </div>

      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Recent records</h2>
            <p className="panel-sub">Most recently updated{processing + uploaded > 0 ? ` — ${processing} processing, ${uploaded} awaiting processing` : ""}.</p>
          </div>
        </div>
        {records.items.length === 0 ? (
          <EmptyState title="No records yet">Upload a document to start the digitization pipeline.</EmptyState>
        ) : (
          <DataTable columns={["Holder", "Parcel", "Status", "Updated", ""]}>
            {records.items.map((r) => (
              <tr key={r.id} className="is-clickable">
                <td>
                  {r.owner_name
                    ? <span className="t-value">{r.owner_name}</span>
                    : <span className="t-absent">Not found</span>}
                </td>
                <td className="muted">
                  {[r.survey_number, r.village].filter(Boolean).join(" · ")
                    || <span className="t-absent">Not found</span>}
                </td>
                <td><StatusBadge tone={statusTone(r.status)}>{statusLabel(r.status)}</StatusBadge></td>
                <td className="muted">{timeAgo(r.updated_at || r.created_at)}</td>
                <td className="shrink">
                  <a href={`#/record/${r.id}`}>
                    Open<span className="sr-only"> {r.owner_name || r.survey_number || "record"}</span>
                  </a>
                </td>
              </tr>
            ))}
          </DataTable>
        )}
      </div>

      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Activity history</h2>
            <p className="panel-sub">Who did what, and when.</p>
          </div>
        </div>
        <EmptyState title="History is kept per record">
          Open any record and choose View audit to see every correction, review and
          approval recorded against it.
        </EmptyState>
      </div>
    </div>
  );
}
