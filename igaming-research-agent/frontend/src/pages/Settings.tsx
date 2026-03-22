import { useEffect, useState } from 'react';
import {
  createQuery,
  deleteQuery,
  getQueries,
  updateQuery,
} from '@/services/api';
import type { CreateQueryDto, Query } from '@/types';

export default function Settings() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [streamType, setStreamType] = useState('legislative');
  const [description, setDescription] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [error, setError] = useState('');
  const [queries, setQueries] = useState<Query[]>([]);

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

  useEffect(() => {
    void loadQueries();
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
    if (type === 'legislative') return 'bg-blue-100 text-blue-700';
    if (type === 'business') return 'bg-emerald-100 text-emerald-700';
    return 'bg-amber-100 text-amber-700';
  };

  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-bold">Settings / Query Manager</h2>

      <form onSubmit={submit} className="bg-white border rounded p-4 space-y-3 max-w-2xl">
        <div>
          <label htmlFor="searchTerm" className="block text-sm mb-1">Search query</label>
          <input
            id="searchTerm"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            required
            className="w-full border rounded px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label htmlFor="streamType" className="block text-sm mb-1">Stream type</label>
          <select
            id="streamType"
            value={streamType}
            onChange={(e) => setStreamType(e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm"
          >
            <option value="legislative">Legislative</option>
            <option value="business">Business</option>
            <option value="whitelist">Whitelist</option>
          </select>
        </div>

        <div>
          <label htmlFor="description" className="block text-sm mb-1">Description</label>
          <input
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm"
          />
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
          />
          Active
        </label>

        {error && <p className="text-red-600 text-sm">{error}</p>}

        <button className="bg-blue-600 text-white text-sm px-4 py-2 rounded disabled:opacity-50" type="submit" disabled={saving}>
          {saving ? 'Saving...' : 'Add Query'}
        </button>
      </form>

      <div className="bg-white border rounded p-4 text-sm text-gray-600">
        {loading ? (
          <p>Loading queries...</p>
        ) : queries.length === 0 ? (
          <p>No queries yet. Add your first search query above.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-gray-500">
                <th className="py-2">Search term</th>
                <th className="py-2">Stream type</th>
                <th className="py-2">Description</th>
                <th className="py-2">Active</th>
                <th className="py-2">Delete</th>
              </tr>
            </thead>
            <tbody>
              {queries.map((query) => (
                <tr key={query.id} className="border-t">
                  <td className="py-2 pr-2">{query.search_term}</td>
                  <td className="py-2 pr-2">
                    <span className={`px-2 py-1 rounded text-xs ${badgeClass(query.stream_type)}`}>
                      {query.stream_type}
                    </span>
                  </td>
                  <td className="py-2 pr-2">{query.description || '-'}</td>
                  <td className="py-2 pr-2">
                    <input
                      aria-label={`toggle-${query.id}`}
                      type="checkbox"
                      checked={query.is_active}
                      onChange={(e) => void toggleActive(query, e.target.checked)}
                    />
                  </td>
                  <td className="py-2">
                    <button type="button" className="text-red-700" onClick={() => void remove(query.id)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
