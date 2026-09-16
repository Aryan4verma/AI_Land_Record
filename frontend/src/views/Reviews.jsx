import Alert from "../components/Alert.jsx";
import { useEffect, useMemo, useRef, useState } from "react";
import Button from "../components/Button.jsx";
import DataTable from "../components/DataTable.jsx";
import EmptyState from "../components/EmptyState.jsx";
import ErrorState from "../components/ErrorState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import Select from "../components/Select.jsx";
import Skeleton from "../components/Skeleton.jsx";
import StatCard from "../components/StatCard.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import TextInput from "../components/TextInput.jsx";
import { timeAgo } from "../components/format.js";
import { friendlyMessage, requestIdOf } from "../components/errors.js";
import { averageAgeHours, filterQueue, sortQueue } from "../components/queue.js";
import { getUser, listReviews } from "../api/client";
import { statusLabel, statusTone } from "../api/types";
import { isOperator } from "../components/roles.js";

/** Review queue (route #/reviews) — Stitch 99a50253 structure on real task
 * rows. Columns, filters, and sorts cover only task fields the backend
 * exposes (status/priority/reason/created_at/assigned_to): per-task
 * confidence, issue-type taxonomy, and reviewer names do not exist
 * backend-side and are omitted rather than invented. Listing requires
 * operator+; read-only users honestly receive the backend 403 as an error state.
 */
export default function Reviews() {
  const readOnly = !isOperator(getUser());
  const [tasks, setTasks] = useState(null);
  const [error, setError] = useState("");
  const [errorRef, setErrorRef] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [assignee, setAssignee] = useState("");
  const [sort, setSort] = useState("PRIORITY");
  const [dirty, setDirty] = useState(0);
  const abortRef = useRef(null);
  const me = getUser();

  function isAbort(err) {
    return err instanceof DOMException && err.name === "AbortError";
  }

  useEffect(() => {
    // Read-only users cannot list tasks (backend 403 by design): do not
    // fire a request that is guaranteed to fail.
    if (readOnly) return undefined;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const signal = controller.signal;
    const opts = { signal };
    // Two list calls (the API filters one status per call); queue rows are
    // the union. Refresh is explicit — no polling on this screen.
    Promise.all([listReviews("PENDING", opts), listReviews("IN_REVIEW", opts)])
      .then(([pending, inReview]) => {
        if (signal.aborted) return;
        setTasks([...pending, ...inReview]);
        setError("");
      })
      .catch((err) => {
        if (isAbort(err) || signal.aborted) return;
        setError(friendlyMessage(err));
        setErrorRef(requestIdOf(err));
      });
    return () => controller.abort();
  }, [dirty, readOnly]);

  const filtered = useMemo(
    () => sortQueue(
      filterQueue(tasks || [], { query, status, priority, assignee, me: me && me.id }),
      sort,
    ),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [tasks, query, status, priority, assignee, sort],
  );

  const hasFilters = Boolean(query.trim() || status || priority || assignee);
  const pending = (tasks || []).filter((t) => t.status === "PENDING");
  const high = (tasks || []).filter((t) => t.priority === "HIGH" || t.priority === "URGENT");
  const avgAge = tasks ? averageAgeHours(tasks) : null;

  function assigneeLabel(t) {
    if (!t.assigned_to) return "Unassigned";
    if (me && t.assigned_to === me.id) return "You";
    return `${t.assigned_to.slice(0, 8)}…`;
  }

  if (readOnly) {
    return (
      <div>
        <PageHeader title="Review queue" sub="Documents requiring human attention." />
        <div className="panel">
          <Alert tone="info" title="Operator access required">
            Your account has read-only access. The review queue, corrections and
            approvals need an operator account. You can still search, open and
            export records.
          </Alert>
        </div>
      </div>
    );
  }

  if (error && !tasks) {
    return (
      <div>
        <PageHeader title="Review queue" sub="Documents requiring human attention." />
        <div className="panel">
          <ErrorState title="Queue unavailable" message={error} requestId={errorRef || undefined} onRetry={() => { setError(""); setErrorRef(""); setDirty((n) => n + 1); }} />
        </div>
      </div>
    );
  }

  if (!tasks) {
    return (
      <div>
        <PageHeader title="Review queue" sub="Documents requiring human attention." />
        <div className="stat-grid" aria-hidden="true">
          {[0, 1, 2].map((i) => (
            <div key={i} className="stat"><Skeleton lines={2} /></div>
          ))}
        </div>
        <div className="panel"><Skeleton lines={5} /></div>
      </div>
    );
  }

  return (
    <div className="vstack">
      <PageHeader
        title="Review queue"
        sub="Documents requiring human attention."
      />

      <div className="stat-grid">
        <StatCard
          label="Pending reviews"
          value={String(pending.length)}
          sub={`${tasks.filter((t) => !t.assigned_to).length} unassigned • ${tasks.length - pending.length} in progress`}
        />
        <StatCard label="High-priority reviews" value={String(high.length)} sub="High or urgent priority" />
        <StatCard
          label="Average review age"
          value={avgAge === null ? "—" : `${avgAge.toFixed(1)} h`}
          sub="Mean wait since task creation"
        />
      </div>

      <div className="panel">
        <form className="filterbar" onSubmit={(e) => e.preventDefault()}>
          <TextInput
            label="Issue contains"
            id="queue-query"
            placeholder="Reason or record ID…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <Select label="Status" id="queue-status" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            <option value="PENDING">Pending verification</option>
            <option value="IN_REVIEW">In review</option>
          </Select>
          <Select label="Priority" id="queue-priority" value={priority} onChange={(e) => setPriority(e.target.value)}>
            <option value="">All priorities</option>
            <option value="HIGH_PLUS">High &amp; urgent</option>
            <option value="URGENT">Urgent</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </Select>
          <Select label="Reviewer" id="queue-assignee" value={assignee} onChange={(e) => setAssignee(e.target.value)}>
            <option value="">All reviewers</option>
            <option value="MINE">Assigned to me</option>
            <option value="UNASSIGNED">Unassigned queue</option>
          </Select>
          <Select label="Sort" id="queue-sort" value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="PRIORITY">Statutory priority</option>
            <option value="OLDEST">Oldest submitted</option>
            <option value="NEWEST">Newest submitted</option>
          </Select>
          <Button type="button" variant="secondary" onClick={() => setDirty((n) => n + 1)}>Refresh</Button>
        </form>

        {error && <ErrorState title="Refresh failed" message={error} requestId={errorRef || undefined} onRetry={() => { setError(""); setErrorRef(""); setDirty((n) => n + 1); }} />}

        {filtered.length === 0 ? (
          <EmptyState title={hasFilters ? "No matching reviews" : "Your review queue is clear."}>
            {hasFilters
              ? "No open tasks match these filters."
              : "No documents currently require human attention."}
          </EmptyState>
        ) : (
          <DataTable columns={["Priority", "Document", "Issue", "Status", "Submitted", "Assignee", "Action"]}>
            {filtered.map((t) => (
              <tr key={t.id}>
                <td>
                  <StatusBadge tone={t.priority === "URGENT" || t.priority === "HIGH" ? "review" : "neutral"}>
                    {statusLabel(t.priority)}
                  </StatusBadge>
                </td>
                <td><code className="tnum">{t.land_record_id.slice(0, 8)}…</code></td>
                <td>{t.reason || "—"}</td>
                <td><StatusBadge tone={statusTone(t.status)}>{statusLabel(t.status)}</StatusBadge></td>
                <td className="muted">{timeAgo(t.created_at)}</td>
                <td>{assigneeLabel(t)}</td>
                <td><a href={`#/record/${t.land_record_id}`}>Review</a></td>
              </tr>
            ))}
          </DataTable>
        )}
      </div>
    </div>
  );
}
