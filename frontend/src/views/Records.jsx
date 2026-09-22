import { useEffect, useRef, useState } from "react";
import EmptyState from "../components/EmptyState.jsx";
import ErrorState from "../components/ErrorState.jsx";
import Skeleton from "../components/Skeleton.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { friendlyMessage, requestIdOf } from "../components/errors.js";
import { isOperator } from "../components/roles.js";
import { exportRecord, getUser, searchRecords } from "../api/client";
import { statusLabel, statusTone } from "../api/types";
import { downloadJson, timeAgo } from "../components/format.js";
import "../styles/records.css";

const PAGE_SIZE = 20;
const STATUS_OPTIONS = [
  "DRAFT",
  "PROCESSING",
  "REVIEW_REQUIRED",
  "READY_FOR_APPROVAL",
  "APPROVED",
  "REJECTED",
];

const SEARCH_FIELDS = [
  { value: "owner", label: "Owner / Khatadar" },
  { value: "survey_number", label: "Survey / Gat" },
  { value: "khasra_number", label: "Khasra" },
  { value: "village", label: "Village" },
];

const EMPTY_FILTERS = {
  query: "",
  searchField: "owner",
  district: "",
  tehsil: "",
  status: "",
};

function isAbort(err) {
  return err instanceof DOMException && err.name === "AbortError";
}

function filterParams(filters) {
  const params = {
    limit: PAGE_SIZE,
    district: filters.district || undefined,
    tehsil: filters.tehsil || undefined,
    status: filters.status || undefined,
  };
  if (filters.query) params[filters.searchField] = filters.query;
  return params;
}

function recordReference(record) {
  return record.survey_number || record.khasra_number || record.khata_number || "Record";
}

function recordType(record) {
  if (record.land_classification) return record.land_classification;
  if (record.mutation_number) return `Mutation ${record.mutation_number}`;
  return "Cadastral record";
}

function joinLabel(value, fallback = "Not supplied") {
  return value || <span className="records-absent">{fallback}</span>;
}

function Chip({ children, onRemove, tone = "default" }) {
  return (
    <span className={`records-chip records-chip-${tone}`}>
      {children}
      {onRemove && (
        <button type="button" onClick={onRemove} aria-label={`Remove ${children} filter`}>
          ×
        </button>
      )}
    </span>
  );
}

function HeaderAction({ children, className = "", ...props }) {
  return <button type="button" className={`records-action ${className}`} {...props}>{children}</button>;
}

function RecordsTable({ records, selected, onToggleAll, onToggle, onExport }) {
  const allSelected = records.length > 0 && records.every((record) => selected.has(record.id));
  return (
    <div className="records-table-wrap">
      <table className="records-table">
        <thead>
          <tr>
            <th className="records-select-col">
              <input
                type="checkbox"
                aria-label="Select all visible records"
                checked={allSelected}
                onChange={(event) => onToggleAll(event.target.checked)}
              />
            </th>
            <th>Owner / Khatadar</th>
            <th>Survey / Gat / Khasra</th>
            <th>Village &amp; Taluka</th>
            <th>District</th>
            <th>Status</th>
            <th>Last updated</th>
            <th className="records-actions-col">Institutional actions</th>
          </tr>
        </thead>
        <tbody>
          {records.map((record) => (
            <tr key={record.id} className={selected.has(record.id) ? "is-selected" : ""}>
              <td className="records-select-col">
                <input
                  type="checkbox"
                  aria-label={`Select ${record.owner_name || recordReference(record)}`}
                  checked={selected.has(record.id)}
                  onChange={() => onToggle(record.id)}
                />
              </td>
              <td>
                <div className="records-primary">{joinLabel(record.owner_name)}</div>
                <div className="records-meta">
                  {record.khata_number ? `Khata No: ${record.khata_number}` : record.father_or_spouse_name || "Land record"}
                </div>
              </td>
              <td>
                <div className="records-reference">
                  <span>{joinLabel(recordReference(record))}</span>
                  <span className="records-type">{recordType(record)}</span>
                </div>
                {record.document_id && <div className="records-linkish">Document linked</div>}
              </td>
              <td>
                <div className="records-primary records-primary-small">{joinLabel(record.village)}</div>
                <div className="records-meta">{joinLabel(record.tehsil, "Taluka not supplied")}</div>
              </td>
              <td className="records-primary records-primary-small">{joinLabel(record.district)}</td>
              <td><StatusBadge tone={statusTone(record.status)}>{statusLabel(record.status)}</StatusBadge></td>
              <td className="records-meta records-updated">
                <div>{timeAgo(record.updated_at || record.created_at)}</div>
                <span>{record.approved_by ? "Approved by operator" : "Workflow record"}</span>
              </td>
              <td className="records-actions-col">
                <div className="records-row-actions">
                  <a className="records-row-button" href={`#/record/${record.id}`}>View dossier</a>
                  <a className="records-icon-button" href={`#/record/${record.id}/audit`} title="Inspect audit" aria-label={`Inspect audit for ${recordReference(record)}`}>✓</a>
                  <button className="records-icon-button" type="button" onClick={() => onExport(record)} title="Export record" aria-label={`Export ${recordReference(record)}`}>⇩</button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Records() {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [applied, setApplied] = useState(EMPTY_FILTERS);
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(() => new Set());
  const [error, setError] = useState("");
  const [errorRef, setErrorRef] = useState("");
  const [actionError, setActionError] = useState("");
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const abortRef = useRef(null);
  const operator = isOperator(getUser());

  async function search(nextPage, nextFilters) {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError("");
    setErrorRef("");
    try {
      const result = await searchRecords({ ...filterParams(nextFilters), page: nextPage }, { signal: controller.signal });
      if (controller.signal.aborted) return;
      setData(result);
      setApplied(nextFilters);
      setSelected(new Set());
    } catch (err) {
      if (isAbort(err)) return;
      setError(friendlyMessage(err));
      setErrorRef(requestIdOf(err));
    } finally {
      if (abortRef.current === controller) setLoading(false);
    }
  }

  useEffect(() => {
    search(1, EMPTY_FILTERS);
    return () => abortRef.current?.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function submit(event) {
    event.preventDefault();
    search(1, { ...filters, query: filters.query.trim(), district: filters.district.trim(), tehsil: filters.tehsil.trim() });
  }

  function retry() {
    search(data?.page || 1, applied);
  }

  function updateFilter(key, value) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function clearFilter(key) {
    const next = { ...applied, [key]: key === "searchField" ? "owner" : "" };
    const nextInput = { ...filters, [key]: key === "searchField" ? "owner" : "" };
    setFilters(nextInput);
    search(1, next);
  }

  function clearAll() {
    setFilters(EMPTY_FILTERS);
    search(1, EMPTY_FILTERS);
  }

  function toggleSelected(id) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll(checked) {
    setSelected(checked ? new Set((data?.items || []).map((record) => record.id)) : new Set());
  }

  async function exportOne(record) {
    setActionError("");
    setExporting(true);
    try {
      const result = await exportRecord(record.id);
      downloadJson(`land-record-${record.id}.json`, result);
    } catch (err) {
      setActionError(friendlyMessage(err));
    } finally {
      setExporting(false);
    }
  }

  async function exportSelected() {
    if (!selected.size) return;
    setActionError("");
    setExporting(true);
    try {
      const records = await Promise.all([...selected].map((id) => exportRecord(id)));
      downloadJson("bhoomi-intel-records.json", {
        format_version: "v1",
        exported_at: new Date().toISOString(),
        records,
      });
    } catch (err) {
      setActionError(friendlyMessage(err));
    } finally {
      setExporting(false);
    }
  }

  const visibleChips = [];
  if (applied.query) visibleChips.push({ key: "query", label: `${SEARCH_FIELDS.find((field) => field.value === applied.searchField)?.label || "Search"}: ${applied.query}` });
  if (applied.district) visibleChips.push({ key: "district", label: `District: ${applied.district}` });
  if (applied.tehsil) visibleChips.push({ key: "tehsil", label: `Taluka: ${applied.tehsil}` });
  if (applied.status) visibleChips.push({ key: "status", label: `Status: ${statusLabel(applied.status)}` });
  const hasFilters = visibleChips.length > 0;
  const items = data?.items || [];

  return (
    <div className="records-view">
      <section className="records-pagehead">
        <div>
          <nav className="records-breadcrumb" aria-label="Breadcrumb">
            <span>Console</span><span aria-hidden="true">›</span><span>Records management</span><span aria-hidden="true">›</span><strong>Master cadastral directory</strong>
          </nav>
          <div className="records-title-row">
            <h1>Institutional Cadastral Records Repository</h1>
            <span className="records-env">GAZETTED_DB</span>
          </div>
          <p>Search, filter, and inspect digitized land records across the jurisdictional registry.</p>
        </div>
        <div className="records-head-actions">
          <HeaderAction onClick={exportSelected} disabled={!selected.size || exporting} title={selected.size ? "Export selected records" : "Select records to export"}>
            <span aria-hidden="true">⇩</span> Export selected{selected.size ? ` (${selected.size})` : ""}
          </HeaderAction>
          {operator && <a className="records-action records-action-primary" href="#/upload"><span aria-hidden="true">⊕</span> Ingest new record</a>}
        </div>
      </section>

      <section className="records-filter-panel" aria-label="Record search and filters">
        <form onSubmit={submit}>
          <div className="records-search-row">
            <span className="records-search-icon" aria-hidden="true">⌕</span>
            <input
              value={filters.query}
              onChange={(event) => updateFilter("query", event.target.value)}
              placeholder="Search by owner, survey / Gat number, Khasra, village…"
              aria-label="Search cadastral records"
              disabled={loading}
            />
            {filters.query && <button type="button" className="records-clear-search" onClick={() => updateFilter("query", "")} aria-label="Clear search">×</button>}
            <select value={filters.searchField} onChange={(event) => updateFilter("searchField", event.target.value)} aria-label="Search field" disabled={loading}>
              {SEARCH_FIELDS.map((field) => <option key={field.value} value={field.value}>{field.label}</option>)}
            </select>
            <kbd>⌘K</kbd>
          </div>
          <div className="records-filter-grid">
            <label><span>District</span><input value={filters.district} onChange={(event) => updateFilter("district", event.target.value)} placeholder="All districts" disabled={loading} /></label>
            <label><span>Taluka / sub-district</span><input value={filters.tehsil} onChange={(event) => updateFilter("tehsil", event.target.value)} placeholder="All talukas" disabled={loading} /></label>
            <label><span>Record status</span><select value={filters.status} onChange={(event) => updateFilter("status", event.target.value)} disabled={loading}><option value="">All statuses</option>{STATUS_OPTIONS.map((status) => <option key={status} value={status}>{statusLabel(status)}</option>)}</select></label>
            <div className="records-supported-note"><span>Search scope</span><strong>Indexed cadastral records</strong><small>Only backend-supported fields are queried.</small></div>
          </div>
          <div className="records-active-row">
            <span className="records-eyebrow">Active filters</span>
            {visibleChips.length === 0 && <span className="records-muted">None</span>}
            {visibleChips.map((chip) => <Chip key={chip.key} onRemove={() => clearFilter(chip.key)}>{chip.label}</Chip>)}
            {hasFilters && <button type="button" className="records-clear-all" onClick={clearAll}>Clear all</button>}
            <button type="submit" className="records-search-submit" disabled={loading}>{loading ? "Searching…" : "Apply filters"}</button>
          </div>
        </form>
      </section>

      {actionError && <div className="records-action-error" role="alert">{actionError}</div>}
      {error && !data && <div className="records-state"><ErrorState title="Records unavailable" message={error} requestId={errorRef || undefined} onRetry={retry} /></div>}
      {loading && !data && <div className="records-state"><Skeleton lines={8} /></div>}
      {data && !loading && !error && data.items.length === 0 && (
        <section className="records-empty-panel">
          <div className="records-empty-mark" aria-hidden="true">⌕</div>
          <EmptyState title={hasFilters ? "No cadastral records found" : "No indexed records yet"}>
            {hasFilters ? "No records match the applied backend filters. Clear or broaden the search." : "Upload a document to start the digitization pipeline."}
          </EmptyState>
          {hasFilters && <button type="button" className="records-action records-action-primary" onClick={clearAll}>Reset filters</button>}
        </section>
      )}
      {data && data.items.length > 0 && (
        <section className="records-table-panel">
          {error && <ErrorState title="Refresh failed" message={error} requestId={errorRef || undefined} onRetry={retry} />}
          <RecordsTable records={items} selected={selected} onToggleAll={toggleAll} onToggle={toggleSelected} onExport={exportOne} />
          <footer className="records-pagination">
            <span>Displaying <strong>{(data.page - 1) * data.limit + 1}–{Math.min(data.page * data.limit, data.total)}</strong> of <strong>{data.total}</strong> records</span>
            <div className="records-pagination-controls">
              <span>Rows per page: <strong>{data.limit}</strong></span>
              <button type="button" onClick={() => search(data.page - 1, applied)} disabled={loading || data.page <= 1} aria-label="Previous page">‹</button>
              <span className="records-page-number">{data.page}</span>
              <button type="button" onClick={() => search(data.page + 1, applied)} disabled={loading || data.page * data.limit >= data.total} aria-label="Next page">›</button>
            </div>
          </footer>
        </section>
      )}

      <section className="records-context-grid" aria-label="Registry context">
        <div><span className="records-context-icon" aria-hidden="true">◈</span><div><h2>Source-grounded records</h2><p>Each indexed record remains linked to its uploaded source document and workflow history.</p></div></div>
        <div><span className="records-context-icon" aria-hidden="true">↔</span><div><h2>Backend search boundary</h2><p>Search and pagination are served by the authenticated records API.</p></div></div>
        <div><span className="records-context-icon" aria-hidden="true">◇</span><div><h2>Audit-preserved ledger</h2><p>Open a record dossier or audit trail for the authoritative workflow history.</p></div></div>
      </section>
    </div>
  );
}
