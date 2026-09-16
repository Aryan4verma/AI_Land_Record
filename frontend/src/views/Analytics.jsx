import { timeAgo } from "../components/format.js";
import { useEffect, useState } from "react";
import EmptyState from "../components/EmptyState.jsx";
import ErrorState from "../components/ErrorState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import Skeleton from "../components/Skeleton.jsx";
import StatCard from "../components/StatCard.jsx";
import { friendlyMessage, requestIdOf } from "../components/errors.js";
import {
  averageJobDuration,
  formatDuration,
  formatPercent,
  reviewShare,
  sumCounts,
  validationPassRate,
} from "../components/analytics.js";
import {
  getDashboardProcessing,
  getDashboardSummary,
  getDashboardValidation,
} from "../api/client";
import { statusLabel, statusTone } from "../api/types";

function severityTone(severity) {
  const s = (severity || "").toUpperCase();
  if (s === "ERROR" || s === "CRITICAL") return "failed";
  if (s === "WARNING") return "review";
  return "";
}

function Bars({ entries, toneOf }) {
  const max = Math.max(0, ...entries.map(([, n]) => n));
  if (entries.length === 0) {
    return <EmptyState title="No data yet">Distributions appear once documents are processed.</EmptyState>;
  }
  return (
    <div className="bars">
      {entries.map(([label, count]) => (
        <div key={label} className="bar-row">
          <span className="bar-label">{statusLabel(label)}</span>
          <span className="bar-track">
            <span
              className={`bar-fill${toneOf && toneOf(label) ? ` tone-${toneOf(label)}` : ""}`}
              style={{ width: `${max === 0 ? 0 : Math.round((count / max) * 100)}%` }}
            />
          </span>
          <span className="bar-value tnum">{count}</span>
        </div>
      ))}
    </div>
  );
}

/** Analytics (route #/analytics) — Stitch b1e028dd structure on live
 * backend aggregates only. Latency averages the recent jobs endpoint;
 * pass rate counts evaluated checks (NOT_CHECKED excluded); distributions
 * are zero-dependency CSS bars. Accuracy benchmarks, time series, and
 * per-stage latencies have no API source and are absent — including the
 * absence itself in the scope note below. No chart library is used
 * (the project has none), so nothing needs lazy-loading.
 */
export default function Analytics() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [errorRef, setErrorRef] = useState("");
  const [dirty, setDirty] = useState(0);

  function isAbort(err) {
    return err instanceof DOMException && err.name === "AbortError";
  }

  useEffect(() => {
    const controller = new AbortController();
    const signal = controller.signal;
    const opts = { signal };
    // One parallel load per mount; no filters exist backend-side, so none
    // are offered (filtering would only slice already-loaded aggregates).
    Promise.all([
      getDashboardSummary(opts),
      getDashboardProcessing(opts),
      getDashboardValidation(opts),
    ])
      .then(([summary, processing, validation]) => {
        if (signal.aborted) return;
        setData({ summary, processing, validation, syncedAt: new Date() });
        setError("");
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
        <PageHeader title="Analytics" sub="Operational monitoring of document processing, review and validation." />
        <div className="panel">
          <ErrorState title="Analytics unavailable" message={error} requestId={errorRef || undefined} onRetry={() => { setError(""); setErrorRef(""); setDirty((n) => n + 1); }} />
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div>
        <PageHeader title="Analytics" sub="Operational monitoring of document processing, review and validation." />
        <div className="stat-grid" aria-hidden="true">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="stat"><Skeleton lines={2} /></div>
          ))}
        </div>
        <div className="panel"><Skeleton lines={5} /></div>
      </div>
    );
  }

  const { summary, processing, validation, syncedAt } = data;
  const recordsTotal = sumCounts(summary.records_by_status);
  const duration = averageJobDuration(processing.recent_jobs);
  const share = reviewShare(summary.open_reviews, recordsTotal);
  const pass = validationPassRate(validation.issues_by_status);
  const evaluated = ["PASS", "WARNING", "FAIL", "REVIEW_REQUIRED"]
    .reduce((a, k) => a + (Number(validation.issues_by_status[k]) || 0), 0);

  const docEntries = Object.entries(summary.documents_by_status).sort((a, b) => b[1] - a[1]);
  const recEntries = Object.entries(summary.records_by_status).sort((a, b) => b[1] - a[1]);
  const sevEntries = Object.entries(validation.issues_by_severity).sort((a, b) => b[1] - a[1]);
  const jobEntries = Object.entries(processing.jobs_by_status).sort((a, b) => b[1] - a[1]);

  return (
    <div className="vstack">
      <PageHeader
        title="Analytics"
        sub="Operational monitoring of document processing, review and validation."
        meta={<span>Updated {timeAgo(syncedAt.toISOString())}</span>}
      />

      <div className="stat-grid">
        <StatCard label="Processed documents" value={String(summary.documents_total)} sub={`${recordsTotal} records extracted`} />
        <StatCard
          label="Average processing time"
          value={formatDuration(duration ? duration.seconds : null)}
          sub={duration ? `Across the last ${duration.count} ${duration.count === 1 ? "document" : "documents"}`
                            : "Nothing processed yet"}
        />
        <StatCard
          label="Awaiting review"
          value={formatPercent(share)}
          sub={share === null ? "No records yet" : `${summary.open_reviews} open review(s)`}
        />
        <StatCard
          label="Validation pass rate"
          value={formatPercent(pass)}
          sub={pass === null ? "Nothing checked yet"
                            : `${evaluated} ${evaluated === 1 ? "check" : "checks"} run`}
        />
      </div>

      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Documents by status</h2>
            <p className="panel-sub">Where each uploaded document currently sits.</p>
          </div>
        </div>
        <Bars entries={docEntries} toneOf={(s) => statusTone(s)} />
      </div>

      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Records by status</h2>
            <p className="panel-sub">Where each extracted record currently sits.</p>
          </div>
        </div>
        <Bars entries={recEntries} toneOf={(s) => statusTone(s)} />
      </div>

      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Validation issues by severity</h2>
            <p className="panel-sub">What the verification rules found, across every record.</p>
          </div>
        </div>
        <Bars entries={sevEntries} toneOf={severityTone} />
      </div>

      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Processing jobs by status</h2>
            <p className="panel-sub">Background pipeline executions.</p>
          </div>
        </div>
        <Bars entries={jobEntries} toneOf={(s) => statusTone(s)} />
      </div>

      <p className="muted">
        Scope note: AI accuracy benchmarks, confidence distributions, per-stage latencies, and
        time-series volume have no API source and are intentionally absent. Date/type filters
        are omitted for the same reason — no endpoint supports filtered aggregates.
      </p>
    </div>
  );
}
