import { useEffect, useRef, useState } from "react";
import Button from "../components/Button.jsx";
import DataTable from "../components/DataTable.jsx";
import EmptyState from "../components/EmptyState.jsx";
import ErrorState from "../components/ErrorState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import Pagination from "../components/Pagination.jsx";
import Select from "../components/Select.jsx";
import Skeleton from "../components/Skeleton.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import TextInput from "../components/TextInput.jsx";
import { friendlyMessage, requestIdOf } from "../components/errors.js";
import { timeAgo } from "../components/format.js";
import { searchRecords } from "../api/client";
import { statusLabel, statusTone } from "../api/types";

const PAGE_SIZE = 20;
const STATUS_OPTIONS = ["", "REVIEW_REQUIRED", "READY_FOR_APPROVAL", "APPROVED", "REJECTED"];

/** Documents repository (route #/records) — searchable, server-filtered and
 * server-paginated via GET /api/v1/records. Columns and filters cover only
 * fields the search API actually supports (holder, survey, status):
 * document-type / date / confidence filtering and a document-ID lookup do
 * not exist backend-side and are omitted rather than invented.
 */
export default function Records() {
  const [holder, setHolder] = useState("");
  const [survey, setSurvey] = useState("");
  const [status, setStatus] = useState("");
  const [applied, setApplied] = useState(null);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [errorRef, setErrorRef] = useState("");
  const [loading, setLoading] = useState(false);
  const abortRef = useRef(null);

  function isAbort(err) {
    return err instanceof DOMException && err.name === "AbortError";
  }

  async function search(nextPage, filters) {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    try {
      // GET /api/v1/records — one request per explicit search/page/refresh.
      // Typing never fires requests (submit-driven only, no debounce needed).
      const result = await searchRecords({
        page: nextPage,
        limit: PAGE_SIZE,
        ...(filters.holder ? { owner: filters.holder } : {}),
        ...(filters.survey ? { survey_number: filters.survey } : {}),
        ...(filters.status ? { status: filters.status } : {}),
      }, { signal: controller.signal });
      if (controller.signal.aborted) return;
      setData(result);
      setApplied(filters);
      setError("");
      setErrorRef("");
    } catch (err) {
      if (isAbort(err)) return;
      setError(friendlyMessage(err));
      setErrorRef(requestIdOf(err));
    } finally {
      if (abortRef.current === controller) setLoading(false);
    }
  }

  function retry() {
    setError("");
    setErrorRef("");
    search(data ? data.page : 1, applied || { holder: "", survey: "", status: "" });
  }

  useEffect(() => {
    search(1, { holder: "", survey: "", status: "" });
    return () => abortRef.current?.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function submit(e) {
    e.preventDefault();
    search(1, { holder: holder.trim(), survey: survey.trim(), status });
  }

  const filtered = applied && (applied.holder || applied.survey || applied.status);

  return (
    <div>
      <PageHeader
        title="Documents"
        sub="Searchable repository of digitized land records."
      />
      <div className="panel">
        <form className="filterbar" onSubmit={submit}>
          <TextInput
            label="Holder name"
            id="doc-holder"
            placeholder="Holder contains…"
            value={holder}
            disabled={loading}
            onChange={(e) => setHolder(e.target.value)}
          />
          <TextInput
            label="Survey number"
            id="doc-survey"
            placeholder="Survey contains…"
            value={survey}
            disabled={loading}
            onChange={(e) => setSurvey(e.target.value)}
          />
          <Select label="Status" id="doc-status" value={status} disabled={loading} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            {STATUS_OPTIONS.filter(Boolean).map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </Select>
          <Button type="submit" variant="primary" disabled={loading}>Search</Button>
        </form>

        {error && !data && <ErrorState title="Documents unavailable" message={error} requestId={errorRef || undefined} onRetry={retry} />}
        {loading && !data && <Skeleton lines={6} />}
        {data && data.items.length === 0 && !loading && !error && (
          <EmptyState title={filtered ? "No matching records" : "No records yet"}>
            {filtered
              ? "No records match these filters. Clear or broaden the search."
              : "Upload a document to start the digitization pipeline."}
          </EmptyState>
        )}
        {data && data.items.length > 0 && (
          <>
            {error && <ErrorState title="Refresh failed" message={error} requestId={errorRef || undefined} onRetry={retry} />}
            <DataTable columns={["Holder", "Survey no.", "Village", "Status", "Updated", ""]}>
              {data.items.map((r) => (
                <tr key={r.id} className="is-clickable">
                  <td>
                    {r.owner_name
                      ? <span className="t-value">{r.owner_name}</span>
                      : <span className="t-absent">Not found</span>}
                  </td>
                  <td>{r.survey_number || <span className="t-absent">Not found</span>}</td>
                  <td>{r.village || <span className="t-absent">Not found</span>}</td>
                  <td><StatusBadge tone={statusTone(r.status)}>{statusLabel(r.status)}</StatusBadge></td>
                  <td className="muted">{timeAgo(r.updated_at || r.created_at)}</td>
                  <td className="shrink">
                    {/* The row itself is the affordance; this stays for keyboard
                        and assistive navigation and names the record it opens. */}
                    <a href={`#/record/${r.id}`}>
                      Open<span className="sr-only"> {r.owner_name || r.survey_number || "record"}</span>
                    </a>
                  </td>
                </tr>
              ))}
            </DataTable>
            <Pagination
              page={data.page}
              limit={data.limit}
              total={data.total}
              disabled={loading}
              onPrev={() => search(data.page - 1, applied)}
              onNext={() => search(data.page + 1, applied)}
            />
          </>
        )}
      </div>
    </div>
  );
}
