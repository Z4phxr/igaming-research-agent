import { useEffect, useState } from 'react';
import {
  createReleaseSource,
  createQuery,
  deleteReleaseSource,
  deleteQuery,
  getReleaseSources,
  getQueries,
  runPipeline,
  updateReleaseSource,
  updateQuery,
} from '@/services/api';
import type { CreateQueryDto, Query, ReleaseSource } from '@/types';

export default function Settings() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [runningPipeline, setRunningPipeline] = useState(false);
  const [pipelineMessage, setPipelineMessage] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [streamType, setStreamType] = useState('legislative');
  const [description, setDescription] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [error, setError] = useState('');
  const [queries, setQueries] = useState<Query[]>([]);
  const [releaseSources, setReleaseSources] = useState<ReleaseSource[]>([]);
  const [companyName, setCompanyName] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');

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
    void loadQueries();
    void loadReleaseSources();
  }, []);

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
    if (type === 'legislative') return 'bg-[#1e3a5f] text-[#2563eb]';
    if (type === 'business') return 'bg-[#1e1b4b] text-[#6366f1]';
    return 'bg-[#14532d] text-[#16a34a]';
  };

  const handleRunPipeline = async () => {
    setRunningPipeline(true);
    setPipelineMessage('');
    setError('');
    try {
      const result = await runPipeline();
      setPipelineMessage(result.message);
      await loadQueries();
    } catch (pipelineError) {
      setError(pipelineError instanceof Error ? pipelineError.message : 'Unable to run pipeline');
    } finally {
      setRunningPipeline(false);
    }
  };

  const submitReleaseSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyName.trim() || !sourceUrl.trim()) {
      setError('Company name and source URL are required');
      return;
    }

    try {
      await createReleaseSource({
        company_name: companyName.trim(),
        source_url: sourceUrl.trim(),
        is_active: true,
      });
      setCompanyName('');
      setSourceUrl('');
      setError('');
      await loadReleaseSources();
    } catch {
      setError('Unable to save release source');
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

  return (
    <section className="space-y-5">
      <div className="flex items-center justify-center">
        <h2 className="text-3xl font-semibold text-white">Query Manager</h2>
      </div>

      {pipelineMessage && <p className="text-center text-sm text-[#16a34a]">{pipelineMessage}</p>}

      <form onSubmit={submit} className="mx-auto w-full max-w-3xl space-y-4 rounded-lg border border-[#222222] bg-[#111111] p-5">
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
                    <span className={`px-2 py-1 rounded text-xs ${badgeClass(query.stream_type)}`}>
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

      <div className="space-y-4">
        <div className="flex items-center justify-center">
          <h3 className="text-2xl font-semibold text-white">Release Source Manager</h3>
        </div>

        <form
          onSubmit={submitReleaseSource}
          className="mx-auto w-full max-w-3xl space-y-4 rounded-lg border border-[#222222] bg-[#111111] p-5"
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
                  <th className="px-4 py-3">Source URL</th>
                  <th className="px-4 py-3">Active</th>
                  <th className="px-4 py-3">Delete</th>
                </tr>
              </thead>
              <tbody>
                {releaseSources.map((source) => (
                  <tr key={source.id} className="border-b border-[#222222] bg-[#111111] transition-colors hover:bg-[#151515]">
                    <td className="px-4 py-3 text-white">{source.company_name}</td>
                    <td className="px-4 py-3 text-[#888888] break-all">{source.source_url}</td>
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

      <div className="flex flex-col items-center gap-2">
        <button
          type="button"
          onClick={() => void handleRunPipeline()}
          disabled={runningPipeline}
          className="rounded-md bg-[#2563eb] px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[#1d4ed8] disabled:opacity-50"
        >
          {runningPipeline ? 'Running pipeline...' : 'Run Pipeline'}
        </button>
      </div>
    </section>
  );
}
