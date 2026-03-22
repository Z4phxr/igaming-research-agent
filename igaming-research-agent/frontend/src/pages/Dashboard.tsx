import { useEffect, useState } from 'react';
import ArticleCard from '@/components/ArticleCard';
import { getLatestReport } from '@/services/api';
import type { Report } from '@/types';

export default function Dashboard() {
  const [latestReport, setLatestReport] = useState<Report | null>(null);
  const [showAllArticles, setShowAllArticles] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(false);
      try {
        const report = await getLatestReport(showAllArticles);
        setLatestReport(report);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [showAllArticles]);

  const articles = [...(latestReport?.articles ?? [])].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
  const keptCount = articles.filter((article) => article.kept).length;
  const totalScreened = latestReport?.total_articles_found ?? 0;
  const today = new Date();
  const subtitle = `${today.toLocaleDateString('en-US', { weekday: 'long' })}, ${today.toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
  })} ${today.getFullYear()}`;

  return (
    <section className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-3xl font-semibold text-white">Daily Intelligence Report</h2>
        <p className="font-mono text-sm text-[#888888]">{subtitle}</p>
      </div>

      {loading && (
        <div className="loading-block">
          <span className="spinner" />
          <span>Loading today&apos;s report...</span>
        </div>
      )}
      {!loading && error && <p className="text-sm text-[#dc2626]">Failed to load report. Please try again.</p>}
      {!loading && !error && !latestReport && (
        <div className="empty-state">
          <div className="empty-state-icon" />
          <p>No reports yet. The pipeline runs daily at 7:00 AM UTC.</p>
        </div>
      )}

      {!loading && !error && latestReport && (
        <div className="space-y-5">
          <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-lg border border-[#222222] bg-[#111111] p-4">
              <p className="text-xs uppercase tracking-[0.08em] text-[#555555]">Articles Screened</p>
              <p className="mt-2 font-mono text-2xl text-[#2563eb]">{latestReport.total_articles_found ?? 0}</p>
            </div>
            <div className="rounded-lg border border-[#222222] bg-[#111111] p-4">
              <p className="text-xs uppercase tracking-[0.08em] text-[#555555]">Articles Kept</p>
              <p className="mt-2 font-mono text-2xl text-[#2563eb]">{latestReport.total_articles_kept ?? 0}</p>
            </div>
            <div className="rounded-lg border border-[#222222] bg-[#111111] p-4">
              <p className="text-xs uppercase tracking-[0.08em] text-[#555555]">Pipeline Run</p>
              <p className="mt-2 font-mono text-2xl text-[#2563eb]">
                {new Date(latestReport.generated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-[#888888]">Showing {keptCount} kept / {totalScreened} total screened</p>
            <button
              type="button"
              className={`rounded-full border px-4 py-1.5 text-xs font-medium transition-colors ${
                showAllArticles
                  ? 'border-[#2563eb] bg-[#2563eb] text-white'
                  : 'border-[#333333] text-[#888888] hover:text-white'
              }`}
              onClick={() => setShowAllArticles((prev) => !prev)}
            >
              {showAllArticles ? 'Show kept only' : 'Show all articles'}
            </button>
          </div>

          <div>
            <p className="text-[11px] uppercase tracking-[0.1em] text-[#555555]">Top Stories</p>
          </div>
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        {articles.map((article) => (
          <ArticleCard key={article.id} article={article} rejected={!article.kept} />
        ))}
      </div>
    </section>
  );
}
