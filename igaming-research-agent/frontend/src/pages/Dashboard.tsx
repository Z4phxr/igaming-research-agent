import { useEffect, useState } from 'react';
import ArticleCard from '@/components/ArticleCard';
import { getReports } from '@/services/api';
import type { Report } from '@/types';

export default function Dashboard() {
  const [latestReport, setLatestReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(false);
      try {
        const reports = await getReports();
        setLatestReport(reports[0] ?? null);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, []);

  const articles = [...(latestReport?.articles ?? [])].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));

  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-bold">Today&apos;s Report</h2>

      {loading && <p className="text-sm text-gray-600">Loading today&apos;s report...</p>}
      {!loading && error && <p className="text-sm text-red-600">Failed to load report. Please try again.</p>}
      {!loading && !error && !latestReport && (
        <p className="text-sm text-gray-600">No reports yet. The pipeline runs daily at 7:00 AM UTC.</p>
      )}

      {!loading && !error && latestReport && (
        <div className="bg-white border rounded p-4 text-sm text-gray-700 space-y-1">
          <p>Report date: {latestReport.report_date}</p>
          <p>Generated at: {new Date(latestReport.generated_at).toLocaleString()}</p>
          <p>Total screened: {latestReport.total_articles_found ?? 0}</p>
          <p>Total kept: {latestReport.total_articles_kept ?? 0}</p>
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-2">
        {articles.map((article) => (
          <ArticleCard key={article.id} article={article} />
        ))}
      </div>
    </section>
  );
}
