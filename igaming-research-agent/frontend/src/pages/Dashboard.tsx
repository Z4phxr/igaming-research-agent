import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import ArticleCard from '@/components/ArticleCard';
import {
  getLatestReport,
  runArticlesPipeline,
  runPipeline,
  runReevaluateTopStories,
  runReleasesPipeline,
} from '@/services/api';
import type { Report } from '@/types';

type DashboardView = 'top_stories' | 'new_releases';

export default function Dashboard() {
  const [latestReport, setLatestReport] = useState<Report | null>(null);
  const [view, setView] = useState<DashboardView>('top_stories');
  const [showAllArticles, setShowAllArticles] = useState(false);
  const [showAllInfo, setShowAllInfo] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [runningAction, setRunningAction] = useState<'all' | 'articles' | 'releases' | 'reevaluate' | null>(null);
  const [actionMessage, setActionMessage] = useState('');
  const [actionError, setActionError] = useState('');

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

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const readSetting = (): void => {
      setShowAllInfo(readShowAllInfoSetting());
    };

    readSetting();
    window.addEventListener('storage', readSetting);
    return () => window.removeEventListener('storage', readSetting);
  }, []);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(false);
      try {
        const report = await getLatestReport(showAllArticles, showAllInfo);
        setLatestReport(report);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [showAllArticles, showAllInfo]);

  const refreshLatestReport = async () => {
    const report = await getLatestReport(showAllArticles, showAllInfo);
    setLatestReport(report);
  };

  const handleRunPipelineAction = async (action: 'all' | 'articles' | 'releases' | 'reevaluate') => {
    setRunningAction(action);
    setActionError('');
    setActionMessage('');
    try {
      let message = '';
      if (action === 'all') {
        const result = await runPipeline();
        message = result.message;
      } else if (action === 'articles') {
        const result = await runArticlesPipeline();
        message = result.message;
      } else if (action === 'releases') {
        const result = await runReleasesPipeline();
        message = result.message;
      } else {
        const result = await runReevaluateTopStories();
        message = result.message;
      }

      setActionMessage(message);
      await refreshLatestReport();
    } catch (runError) {
      setActionError(runError instanceof Error ? runError.message : 'Unable to run selected pipeline action.');
    } finally {
      setRunningAction(null);
    }
  };

  const articles = [...(latestReport?.articles ?? [])].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
  const releaseArticles = [...(latestReport?.release_articles ?? [])].sort(
    (a, b) => new Date(b.published_date || b.scraped_date).getTime() - new Date(a.published_date || a.scraped_date).getTime(),
  );
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
            <div className="rounded-lg border border-[#222222] bg-[#111111] p-4 text-center">
              <p className="text-xs uppercase tracking-[0.08em] text-[#555555]">Articles Screened</p>
              <p className="mt-2 font-mono text-2xl text-[#2563eb]">{latestReport.total_articles_found ?? 0}</p>
            </div>
            <div className="rounded-lg border border-[#222222] bg-[#111111] p-4 text-center">
              <p className="text-xs uppercase tracking-[0.08em] text-[#555555]">Articles Kept</p>
              <p className="mt-2 font-mono text-2xl text-[#2563eb]">{latestReport.total_articles_kept ?? 0}</p>
            </div>
            <div className="rounded-lg border border-[#222222] bg-[#111111] p-4 text-center">
              <p className="text-xs uppercase tracking-[0.08em] text-[#555555]">Pipeline Actions</p>
              <div className="mt-2 grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => void handleRunPipelineAction('all')}
                  disabled={runningAction !== null}
                  className="rounded border border-[#333333] bg-[#0f0f0f] px-2 py-1.5 text-xs font-medium text-[#2563eb] hover:bg-[#1a1a1a] disabled:opacity-50"
                >
                  {runningAction === 'all' ? 'Running...' : 'Run All'}
                </button>
                <button
                  type="button"
                  onClick={() => void handleRunPipelineAction('articles')}
                  disabled={runningAction !== null}
                  className="rounded border border-[#333333] bg-[#0f0f0f] px-2 py-1.5 text-xs font-medium text-[#2563eb] hover:bg-[#1a1a1a] disabled:opacity-50"
                >
                  {runningAction === 'articles' ? 'Running...' : 'Run Articles'}
                </button>
                <button
                  type="button"
                  onClick={() => void handleRunPipelineAction('releases')}
                  disabled={runningAction !== null}
                  className="rounded border border-[#333333] bg-[#0f0f0f] px-2 py-1.5 text-xs font-medium text-[#2563eb] hover:bg-[#1a1a1a] disabled:opacity-50"
                >
                  {runningAction === 'releases' ? 'Running...' : 'Run Releases'}
                </button>
                <button
                  type="button"
                  onClick={() => void handleRunPipelineAction('reevaluate')}
                  disabled={runningAction !== null}
                  className="rounded border border-[#333333] bg-[#0f0f0f] px-2 py-1.5 text-xs font-medium text-[#2563eb] hover:bg-[#1a1a1a] disabled:opacity-50"
                >
                  {runningAction === 'reevaluate' ? 'Running...' : 'Re-evaluate'}
                </button>
              </div>
            </div>
          </div>

          {actionMessage && <p className="text-sm text-[#16a34a]">{actionMessage}</p>}
          {actionError && <p className="text-sm text-[#dc2626]">{actionError}</p>}

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="inline-flex items-center rounded-full border border-[#333333] bg-[#0f0f0f] p-1">
              <button
                type="button"
                className={`rounded-full px-4 py-1.5 text-xs font-medium transition-colors ${
                  view === 'top_stories'
                    ? 'bg-[#2563eb] text-white'
                    : 'text-[#888888] hover:text-white'
                }`}
                onClick={() => setView('top_stories')}
              >
                Top Stories
              </button>
              <button
                type="button"
                className={`rounded-full px-4 py-1.5 text-xs font-medium transition-colors ${
                  view === 'new_releases'
                    ? 'bg-[#2563eb] text-white'
                    : 'text-[#888888] hover:text-white'
                }`}
                onClick={() => setView('new_releases')}
              >
                New Releases
              </button>
            </div>

            {view === 'top_stories' && (
              <div className="flex items-center gap-2">
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
                {showAllInfo && (
                  <span className="rounded-full border border-[#f59e0b] bg-[#3f2f04] px-3 py-1 text-[11px] font-medium text-[#fcd34d]">
                    SHOW ALL INFO on
                  </span>
                )}
              </div>
            )}
          </div>

          {view === 'top_stories' && (
            <>
              <p className="text-sm text-[#888888]">Showing {keptCount} kept / {totalScreened} total screened</p>
              <div className="space-y-2">
                <p className="text-[11px] uppercase tracking-[0.1em] text-[#555555]">Intelligence Briefing</p>
                <div className="rounded-lg border border-[#222222] bg-[#111111] p-4">
                  {latestReport.briefing ? (
                    <ReactMarkdown
                      components={{
                        h2: ({ children }) => (
                          <h2 className="mb-3 border-b border-[#222222] pb-2 text-base font-semibold text-white">{children}</h2>
                        ),
                        p: ({ children }) => <p className="mb-3 leading-7 text-[#888888] last:mb-0">{children}</p>,
                        strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
                        ul: ({ children }) => <ul className="mb-2 list-disc space-y-1 pl-5 text-[#888888]">{children}</ul>,
                        li: ({ children }) => <li className="marker:text-[#2563eb]">{children}</li>,
                      }}
                    >
                      {latestReport.briefing}
                    </ReactMarkdown>
                  ) : (
                    <p className="text-sm text-[#555555]">Briefing not available for this report</p>
                  )}
                </div>
                <p className="text-[11px] text-[#555555]">
                  {latestReport.briefing_generated_at
                    ? `Generated ${new Date(latestReport.briefing_generated_at).toLocaleString()}`
                    : 'Briefing timestamp unavailable'}
                </p>
              </div>

              <div>
                <p className="text-[11px] uppercase tracking-[0.1em] text-[#555555]">Top Stories</p>
              </div>
            </>
          )}

          {view === 'new_releases' && (
            <div>
              <p className="text-sm text-[#888888]">Latest company releases discovered in the last 24 hours</p>
            </div>
          )}
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        {view === 'top_stories' &&
          articles.map((article) => (
            <ArticleCard key={article.id} article={article} rejected={!article.kept} showAllInfo={showAllInfo} />
          ))}

        {view === 'new_releases' &&
          releaseArticles.map((article) => (
            <ArticleCard key={article.id} article={article} rejected={false} compactRelease />
          ))}
      </div>

      {!loading && !error && view === 'new_releases' && releaseArticles.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon" />
          <p>No fresh releases found in the last 24h. Add more source pages in Settings.</p>
        </div>
      )}
    </section>
  );
}
