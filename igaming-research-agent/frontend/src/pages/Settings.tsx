import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import {
  createReleaseSource,
  createQuery,
  deleteReleaseSource,
  deleteQuery,
  getReleaseSources,
  getQueries,
  runArticlesPipeline,
  runReleaseSourceHealthCheck,
  runSingleReleaseSourceHealthCheck,
  runReleasesPipeline,
  updateReleaseSource,
  updateQuery,
} from '@/services/api';
import type {
  CreateQueryDto,
  Query,
  ReleaseSource,
  ReleaseSourceHealthCheckResponse,
  ReleaseSourceHealthCheckResult,
} from '@/types';

type SettingsView = 'queries' | 'sources' | 'health';

export default function Settings() {
  const [activeView, setActiveView] = useState<SettingsView>('queries');
  const [showAllInfo, setShowAllInfo] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [runningArticlesPipeline, setRunningArticlesPipeline] = useState(false);
  const [runningReleasesPipeline, setRunningReleasesPipeline] = useState(false);
  const [runningHealthCheck, setRunningHealthCheck] = useState(false);
  const [runningSingleHealthCheckId, setRunningSingleHealthCheckId] = useState<number | null>(null);
  const [articlesPipelineMessage, setArticlesPipelineMessage] = useState('');
  const [releasesPipelineMessage, setReleasesPipelineMessage] = useState('');
  const [healthError, setHealthError] = useState('');
  const [healthSummary, setHealthSummary] = useState<ReleaseSourceHealthCheckResponse | null>(null);
  const [healthResults, setHealthResults] = useState<ReleaseSourceHealthCheckResult[]>([]);

  const [searchTerm, setSearchTerm] = useState('');
  const [streamType, setStreamType] = useState('legislative');
  const [description, setDescription] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [error, setError] = useState('');
  const [queries, setQueries] = useState<Query[]>([]);

  const [releaseSources, setReleaseSources] = useState<ReleaseSource[]>([]);
  const [companyName, setCompanyName] = useState('');
  const [category, setCategory] = useState('Operator');
  const [sourceUrl, setSourceUrl] = useState('');
  const [notes, setNotes] = useState('');
  const [savingSourceId, setSavingSourceId] = useState<number | null>(null);

  const readShowAllInfoSetting = (): boolean => {
    if (typeof window === 'undefined') {
      return false;
    }

    const storageLike = window.localStorage as { getItem?: (key: string) => string | null } | undefined;
    if (!storageLike || typeof storageLike.getItem !== 'function') {
      return false;
    }

    return storageLike.getItem('show_all_info') === 'true';
  };

  const writeShowAllInfoSetting = (value: boolean): void => {
    if (typeof window === 'undefined') {
      return;
    }

    const storageLike = window.localStorage as { setItem?: (key: string, value: string) => void } | undefined;
    if (!storageLike || typeof storageLike.setItem !== 'function') {
      return;
    }

    storageLike.setItem('show_all_info', String(value));
  };

  const loadQueries = async () => {
    setLoading(true);
    try {
      const data = await getQueries();
      setQueries(data);
      setError('');
    } catch {
      setError('Unable to load queries');
    } finally {
      setLoading(false);
    }
  };

  const loadReleaseSources = async () => {
    try {
      const data = await getReleaseSources();
      setReleaseSources(data);
      setError('');
    } catch {
      setError('Unable to load release sources');
    }
  };

  useEffect(() => {
    setShowAllInfo(readShowAllInfoSetting());

    void loadQueries();
    void loadReleaseSources();
  }, []);

  const handleToggleShowAllInfo = (checked: boolean): void => {
    setShowAllInfo(checked);
    writeShowAllInfoSetting(checked);
  };

  const resetForm = (): void => {
    setSearchTerm('');
    setStreamType('legislative');
    setDescription('');
    setIsActive(true);
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchTerm.trim()) {
      setError('Search term is required');
      return;
    }

    setSaving(true);
    try {
      const payload: CreateQueryDto = {
        search_term: searchTerm.trim(),
        stream_type: streamType,
        description: description.trim() || undefined,
        is_active: isActive,
      };

      await createQuery(payload);
      setError('');
      resetForm();
      await loadQueries();
    } catch {
      setError('Unable to save query');
    } finally {
      setSaving(false);
    }
  };

  const remove = async (queryId: number) => {
    if (!window.confirm('Delete this query?')) {
      return;
    }

    try {
      await deleteQuery(queryId);
      setError('');
      await loadQueries();
    } catch {
      setError('Unable to delete query');
    }
  };

  const toggleActive = async (query: Query, checked: boolean) => {
    try {
      await updateQuery(query.id, { is_active: checked });
      setQueries((current) =>
        current.map((item) => (item.id === query.id ? { ...item, is_active: checked } : item)),
      );
    } catch {
      setError('Unable to update query status');
    }
  };

  const badgeClass = (type: string): string => {
    if (type === 'legislative') return 'bg-[#1e3a5f] text-[#60a5fa]';
    if (type === 'business') return 'bg-[#1e1b4b] text-[#818cf8]';
    return 'bg-[#14532d] text-[#4ade80]';
  };

  const handleRunArticlesPipeline = async () => {
    setRunningArticlesPipeline(true);
    setArticlesPipelineMessage('');
    setError('');
    try {
      const result = await runArticlesPipeline();
      setArticlesPipelineMessage(result.message);
      await loadQueries();
    } catch (pipelineError) {
      setError(pipelineError instanceof Error ? pipelineError.message : 'Unable to run pipeline');
    } finally {
      setRunningArticlesPipeline(false);
    }
  };

  const handleRunReleasesPipeline = async () => {
    setRunningReleasesPipeline(true);
    setReleasesPipelineMessage('');
    setError('');
    try {
      const result = await runReleasesPipeline();
      setReleasesPipelineMessage(result.message);
      await loadReleaseSources();
    } catch (pipelineError) {
      setError(pipelineError instanceof Error ? pipelineError.message : 'Unable to run release pipeline');
    } finally {
      setRunningReleasesPipeline(false);
    }
  };

  const handleRunHealthCheck = async () => {
    setRunningHealthCheck(true);
    setHealthError('');
    try {
      const result = await runReleaseSourceHealthCheck();
      setHealthSummary(result);
      setHealthResults(result.results || []);
    } catch (runError) {
      setHealthError(runError instanceof Error ? runError.message : 'Unable to run release source health check');
    } finally {
      setRunningHealthCheck(false);
    }
  };

  const handleRunSingleHealthCheck = async (source: ReleaseSource) => {
    setRunningSingleHealthCheckId(source.id);
    setHealthError('');
    try {
      const response = await runSingleReleaseSourceHealthCheck(source.id);
      setHealthResults((current) => {
        const next = [...current];
        const index = next.findIndex((item) => item.source_id === source.id);
        if (index >= 0) {
          next[index] = response.result;
        } else {
          next.push(response.result);
        }
        return next;
      });
    } catch (runError) {
      setHealthError(runError instanceof Error ? runError.message : 'Unable to run company health check');
    } finally {
      setRunningSingleHealthCheckId(null);
    }
  };

  const submitReleaseSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyName.trim() || !category.trim() || !sourceUrl.trim()) {
      setError('Company name, category and source URL are required');
      return;
    }

    try {
      await createReleaseSource({
        company_name: companyName.trim(),
        category: category.trim(),
        source_url: sourceUrl.trim(),
        notes: notes.trim() || undefined,
        is_active: true,
      });
      setCompanyName('');
      setCategory('Operator');
      setSourceUrl('');
      setNotes('');
      setError('');
      await loadReleaseSources();
    } catch {
      setError('Unable to save release source');
    }
  };

  const updateReleaseSourceField = (sourceId: number, field: keyof ReleaseSource, value: string | boolean) => {
    setReleaseSources((current) =>
      current.map((item) => (item.id === sourceId ? { ...item, [field]: value } : item)),
    );
  };

  const saveReleaseSource = async (source: ReleaseSource) => {
    if (!source.company_name.trim() || !source.category.trim() || !source.source_url.trim()) {
      setError('Company name, category and source URL are required');
      return;
    }

    setSavingSourceId(source.id);
    try {
      await updateReleaseSource(source.id, {
        company_name: source.company_name.trim(),
        category: source.category.trim(),
        source_url: source.source_url.trim(),
        notes: source.notes?.trim() || '',
        is_active: source.is_active,
      });
      setError('');
      await loadReleaseSources();
    } catch {
      setError('Unable to save release source changes');
    } finally {
      setSavingSourceId(null);
    }
  };

  const toggleReleaseSourceActive = async (source: ReleaseSource, checked: boolean) => {
    try {
      await updateReleaseSource(source.id, { is_active: checked });
      setReleaseSources((current) =>
        current.map((item) => (item.id === source.id ? { ...item, is_active: checked } : item)),
      );
    } catch {
      setError('Unable to update release source status');
    }
  };

  const removeReleaseSource = async (sourceId: number) => {
    if (!window.confirm('Delete this release source?')) {
      return;
    }

    try {
      await deleteReleaseSource(sourceId);
      setError('');
      await loadReleaseSources();
    } catch {
      setError('Unable to delete release source');
    }
  };

  const healthCards = useMemo(() => {
    const resultMap = new Map<number, ReleaseSourceHealthCheckResult>();
    for (const result of healthResults) {
      resultMap.set(result.source_id, result);
    }

    const activeSources = releaseSources.filter((source) => source.is_active);
    return activeSources.map((source) => {
      const item = resultMap.get(source.id);
      const hasResult = Boolean(item);
      const passed = item?.passed ?? false;

      const cardClass = !hasResult
        ? 'border-[#374151] bg-[#121212]'
        : passed
          ? 'border-[#15803d] bg-[#0f2518]'
          : 'border-[#991b1b] bg-[#2a1111]';

      return (
        <article key={source.id} className={`rounded-lg border p-4 ${cardClass}`}>
          <div className="mb-3 flex items-center justify-between gap-3">
            <h4 className="text-base font-semibold text-white">{source.company_name}</h4>
            <span
              className={`rounded px-2 py-1 text-xs font-semibold ${
                !hasResult
                  ? 'bg-[#1f2937] text-[#e5e7eb]'
                  : passed
                    ? 'bg-[#166534] text-[#bbf7d0]'
                    : 'bg-[#7f1d1d] text-[#fecaca]'
              }`}
            >
              {!hasResult ? 'NOT RUN' : passed ? 'PASS' : 'FAIL'}
            </span>
          </div>

          <p className="text-xs text-[#b3b3b3]">Source: {source.source_url}</p>

          <div className="mt-3">
            <button
              type="button"
              onClick={() => void handleRunSingleHealthCheck(source)}
              disabled={runningSingleHealthCheckId === source.id}
              className="rounded-md bg-[#1d4ed8] px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-[#1e40af] disabled:opacity-50"
            >
              {runningSingleHealthCheckId === source.id ? 'Checking...' : 'Run Health Check'}
            </button>
          </div>

          {!hasResult ? (
            <div className="mt-3 rounded border border-[#4b5563] bg-[#0f172a] p-2">
              <p className="text-sm text-[#d1d5db]">No result yet for this company.</p>
            </div>
          ) : passed ? (
            <div className="mt-3 space-y-1 text-sm text-[#d7f9e0]">
              <p>Latest article: {item?.latest_article_title || '-'}</p>
              {item?.latest_article_url ? (
                <a
                  href={item.latest_article_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-block text-[#7dd3fc] underline decoration-[#1d4ed8] underline-offset-2 hover:text-[#bae6fd]"
                >
                  Open latest article
                </a>
              ) : (
                <p className="text-[#fef08a]">Article link not available</p>
              )}
              <p className="text-[#a7f3d0]">Age: {formatAge(item?.latest_article_age_hours ?? null)}</p>
            </div>
          ) : (
            <div className="mt-3 rounded border border-[#7f1d1d] bg-[#180b0b] p-2">
              <p className="text-xs uppercase tracking-[0.08em] text-[#fca5a5]">Error Log</p>
              <p className="mt-1 text-sm text-[#fecaca]">{item?.error_log || 'Unknown error'}</p>
            </div>
          )}
        </article>
      );
    });
  }, [healthResults, releaseSources, runningSingleHealthCheckId]);

  const activeHealthSourcesCount = useMemo(
    () => releaseSources.filter((source) => source.is_active).length,
    [releaseSources],
  );

  const renderQueriesView = () => (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h3 className="text-2xl font-semibold text-white">Query Manager</h3>
        <button
          type="button"
          onClick={() => void handleRunArticlesPipeline()}
          disabled={runningArticlesPipeline}
          className="rounded-md bg-[#2563eb] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#1d4ed8] disabled:opacity-50"
        >
          {runningArticlesPipeline ? 'Running articles...' : 'Run Articles Pipeline'}
        </button>
      </div>

      {articlesPipelineMessage && <p className="text-sm text-[#16a34a]">{articlesPipelineMessage}</p>}

      <form onSubmit={submit} className="w-full max-w-3xl space-y-4 rounded-lg border border-[#222222] bg-[#111111] p-5">
        <div>
          <label htmlFor="searchTerm" className="mb-1 block text-[12px] uppercase tracking-[0.05em] text-[#888888]">Search query</label>
          <input
            id="searchTerm"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            required
            className="w-full rounded-md border border-[#333333] bg-[#0a0a0a] px-3.5 py-2.5 text-sm text-white outline-none transition-colors focus:border-[#2563eb]"
          />
        </div>

        <div>
          <label htmlFor="streamType" className="mb-1 block text-[12px] uppercase tracking-[0.05em] text-[#888888]">Stream type</label>
          <select
            id="streamType"
            value={streamType}
            onChange={(e) => setStreamType(e.target.value)}
            className="w-full rounded-md border border-[#333333] bg-[#0a0a0a] px-3.5 py-2.5 text-sm text-white outline-none transition-colors focus:border-[#2563eb]"
          >
            <option value="legislative">Legislative</option>
            <option value="business">Business</option>
            <option value="whitelist">Whitelist</option>
          </select>
        </div>

        <div>
          <label htmlFor="description" className="mb-1 block text-[12px] uppercase tracking-[0.05em] text-[#888888]">Description</label>
          <input
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full rounded-md border border-[#333333] bg-[#0a0a0a] px-3.5 py-2.5 text-sm text-white outline-none transition-colors focus:border-[#2563eb]"
          />
        </div>

        <label className="flex items-center gap-2 text-sm text-[#888888]">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
          />
          Active
        </label>

        {error && <p className="text-sm text-[#dc2626]">{error}</p>}

        <button
          className="rounded-md bg-[#2563eb] px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[#1d4ed8] disabled:opacity-50"
          type="submit"
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Add Query'}
        </button>
      </form>

      <div className="overflow-hidden rounded-lg border border-[#222222] bg-[#111111]">
        {loading ? (
          <div className="loading-block">
            <span className="spinner" />
            <span>Loading queries...</span>
          </div>
        ) : queries.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon" />
            <p>No queries yet. Add your first search query above.</p>
          </div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="bg-[#1a1a1a] text-[11px] uppercase tracking-[0.08em] text-[#555555]">
                <th className="px-4 py-3">Search term</th>
                <th className="px-4 py-3">Stream type</th>
                <th className="px-4 py-3">Description</th>
                <th className="px-4 py-3">Active</th>
                <th className="px-4 py-3">Delete</th>
              </tr>
            </thead>
            <tbody>
              {queries.map((query) => (
                <tr key={query.id} className="border-b border-[#222222] bg-[#111111] transition-colors hover:bg-[#151515]">
                  <td className="px-4 py-3 text-white">{query.search_term}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded px-2 py-1 text-xs ${badgeClass(query.stream_type)}`}>
                      {query.stream_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-[#888888]">{query.description || '-'}</td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      aria-label={`toggle-${query.id}`}
                      onClick={() => void toggleActive(query, !query.is_active)}
                      className={`h-6 w-11 rounded-full border border-[#333333] p-0.5 transition-colors ${
                        query.is_active ? 'bg-[#2563eb]' : 'bg-[#1a1a1a]'
                      }`}
                    >
                      <span
                        className={`block h-4 w-4 rounded-full bg-white transition-transform ${
                          query.is_active ? 'translate-x-5' : 'translate-x-0'
                        }`}
                      />
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      className="text-[#555555] transition-colors hover:text-[#dc2626]"
                      onClick={() => void remove(query.id)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );

  const renderSourcesView = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-2xl font-semibold text-white">Release Source Manager</h3>
        <button
          type="button"
          onClick={() => void handleRunReleasesPipeline()}
          disabled={runningReleasesPipeline}
          className="rounded-md bg-[#16a34a] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#15803d] disabled:opacity-50"
        >
          {runningReleasesPipeline ? 'Running releases...' : 'Run Releases Pipeline'}
        </button>
      </div>

      {releasesPipelineMessage && <p className="text-sm text-[#16a34a]">{releasesPipelineMessage}</p>}

      <form
        onSubmit={submitReleaseSource}
        className="w-full max-w-3xl space-y-4 rounded-lg border border-[#222222] bg-[#111111] p-5"
      >
        <div>
          <label htmlFor="companyName" className="mb-1 block text-[12px] uppercase tracking-[0.05em] text-[#888888]">
            Company name
          </label>
          <input
            id="companyName"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            required
            className="w-full rounded-md border border-[#333333] bg-[#0a0a0a] px-3.5 py-2.5 text-sm text-white outline-none transition-colors focus:border-[#2563eb]"
          />
        </div>

        <div>
          <label htmlFor="category" className="mb-1 block text-[12px] uppercase tracking-[0.05em] text-[#888888]">
            Category
          </label>
          <input
            id="category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            required
            className="w-full rounded-md border border-[#333333] bg-[#0a0a0a] px-3.5 py-2.5 text-sm text-white outline-none transition-colors focus:border-[#2563eb]"
          />
        </div>

        <div>
          <label htmlFor="sourceUrl" className="mb-1 block text-[12px] uppercase tracking-[0.05em] text-[#888888]">
            Source URL
          </label>
          <input
            id="sourceUrl"
            value={sourceUrl}
            onChange={(e) => setSourceUrl(e.target.value)}
            required
            placeholder="https://www.igt.com/explore-igt/news/news"
            className="w-full rounded-md border border-[#333333] bg-[#0a0a0a] px-3.5 py-2.5 text-sm text-white outline-none transition-colors focus:border-[#2563eb]"
          />
        </div>

        <div>
          <label htmlFor="notes" className="mb-1 block text-[12px] uppercase tracking-[0.05em] text-[#888888]">Notes</label>
          <textarea
            id="notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            className="w-full rounded-md border border-[#333333] bg-[#0a0a0a] px-3.5 py-2.5 text-sm text-white outline-none transition-colors focus:border-[#2563eb]"
          />
        </div>

        {error && <p className="text-sm text-[#dc2626]">{error}</p>}

        <button
          className="rounded-md bg-[#2563eb] px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[#1d4ed8]"
          type="submit"
        >
          Add Release Source
        </button>
      </form>

      <div className="overflow-hidden rounded-lg border border-[#222222] bg-[#111111]">
        {releaseSources.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon" />
            <p>No release sources yet. Add company newsroom pages above.</p>
          </div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="bg-[#1a1a1a] text-[11px] uppercase tracking-[0.08em] text-[#555555]">
                <th className="px-4 py-3">Company</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Source URL</th>
                <th className="px-4 py-3">Notes</th>
                <th className="px-4 py-3">Active</th>
                <th className="px-4 py-3">Save</th>
                <th className="px-4 py-3">Delete</th>
              </tr>
            </thead>
            <tbody>
              {releaseSources.map((source) => (
                <tr key={source.id} className="border-b border-[#222222] bg-[#111111] transition-colors hover:bg-[#151515]">
                  <td className="px-4 py-3">
                    <input
                      value={source.company_name}
                      onChange={(e) => updateReleaseSourceField(source.id, 'company_name', e.target.value)}
                      className="w-full rounded-md border border-[#333333] bg-[#0a0a0a] px-2.5 py-1.5 text-sm text-white outline-none transition-colors focus:border-[#2563eb]"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <input
                      value={source.category}
                      onChange={(e) => updateReleaseSourceField(source.id, 'category', e.target.value)}
                      className="w-full rounded-md border border-[#333333] bg-[#0a0a0a] px-2.5 py-1.5 text-sm text-white outline-none transition-colors focus:border-[#2563eb]"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <input
                      value={source.source_url}
                      onChange={(e) => updateReleaseSourceField(source.id, 'source_url', e.target.value)}
                      className="w-full rounded-md border border-[#333333] bg-[#0a0a0a] px-2.5 py-1.5 text-sm text-white outline-none transition-colors focus:border-[#2563eb]"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <textarea
                      value={source.notes || ''}
                      onChange={(e) => updateReleaseSourceField(source.id, 'notes', e.target.value)}
                      rows={2}
                      className="w-full rounded-md border border-[#333333] bg-[#0a0a0a] px-2.5 py-1.5 text-sm text-white outline-none transition-colors focus:border-[#2563eb]"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      aria-label={`toggle-release-source-${source.id}`}
                      onClick={() => void toggleReleaseSourceActive(source, !source.is_active)}
                      className={`h-6 w-11 rounded-full border border-[#333333] p-0.5 transition-colors ${
                        source.is_active ? 'bg-[#2563eb]' : 'bg-[#1a1a1a]'
                      }`}
                    >
                      <span
                        className={`block h-4 w-4 rounded-full bg-white transition-transform ${
                          source.is_active ? 'translate-x-5' : 'translate-x-0'
                        }`}
                      />
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      className="text-[#2563eb] transition-colors hover:text-white disabled:opacity-50"
                      disabled={savingSourceId === source.id}
                      onClick={() => void saveReleaseSource(source)}
                    >
                      {savingSourceId === source.id ? 'Saving...' : 'Save'}
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      className="text-[#555555] transition-colors hover:text-[#dc2626]"
                      onClick={() => void removeReleaseSource(source.id)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );

  const renderHealthView = () => (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h3 className="text-2xl font-semibold text-white">Release Source Health Check</h3>
        <button
          type="button"
          onClick={() => void handleRunHealthCheck()}
          disabled={runningHealthCheck}
          className="rounded-md bg-[#0ea5e9] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#0284c7] disabled:opacity-50"
        >
          {runningHealthCheck ? 'Running health check...' : 'Run Health Check'}
        </button>
      </div>

      {healthSummary && (
        <div className="rounded-lg border border-[#1f2937] bg-[#10141f] p-4 text-sm text-[#cbd5e1]">
          <p>
            Checked: <span className="text-white">{new Date(healthSummary.checked_at).toLocaleString()}</span>
          </p>
          <p>
            Passed: <span className="text-[#86efac]">{healthSummary.passed_sources}</span> / {healthSummary.total_sources}
          </p>
          <p>
            Failed: <span className="text-[#fca5a5]">{healthSummary.failed_sources}</span>
          </p>
        </div>
      )}

      {healthError && <p className="text-sm text-[#dc2626]">{healthError}</p>}

      {activeHealthSourcesCount === 0 ? (
        <div className="rounded-lg border border-dashed border-[#333333] bg-[#0f0f0f] p-6 text-sm text-[#8b8b8b]">
          No active release sources available for health checks.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">{healthCards}</div>
      )}
    </div>
  );

  return (
    <section className="space-y-5">
      <div className="rounded-lg border border-[#4b3a0b] bg-[#17130a] p-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-[#fcd34d]">SHOW ALL INFO</p>
            <p className="mt-1 text-xs text-[#fef3c7]">
              When enabled, dashboard rejected cards request extra LLM "why failed" details. This increases API cost.
            </p>
          </div>
          <button
            type="button"
            aria-label="toggle-show-all-info"
            onClick={() => handleToggleShowAllInfo(!showAllInfo)}
            className={`h-6 w-11 rounded-full border p-0.5 transition-colors ${
              showAllInfo ? 'border-[#f59e0b] bg-[#f59e0b]' : 'border-[#333333] bg-[#1a1a1a]'
            }`}
          >
            <span
              className={`block h-4 w-4 rounded-full bg-white transition-transform ${
                showAllInfo ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 rounded-lg border border-[#222222] bg-[#0f0f0f] p-2">
        <TabButton active={activeView === 'queries'} onClick={() => setActiveView('queries')}>
          Query Manager
        </TabButton>
        <TabButton active={activeView === 'sources'} onClick={() => setActiveView('sources')}>
          Release Source Manager
        </TabButton>
        <TabButton active={activeView === 'health'} onClick={() => setActiveView('health')}>
          Release Source Health Check
        </TabButton>
      </div>

      {activeView === 'queries' && renderQueriesView()}
      {activeView === 'sources' && renderSourcesView()}
      {activeView === 'health' && renderHealthView()}
    </section>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
        active
          ? 'bg-[#2563eb] text-white'
          : 'bg-[#191919] text-[#b3b3b3] hover:bg-[#262626] hover:text-white'
      }`}
    >
      {children}
    </button>
  );
}

function formatAge(ageHours: number | null): string {
  if (ageHours === null || Number.isNaN(ageHours)) {
    return 'Unknown';
  }
  if (ageHours < 24) {
    return `${ageHours.toFixed(1)} hours ago`;
  }
  const days = ageHours / 24;
  return `${days.toFixed(1)} days ago`;
}
