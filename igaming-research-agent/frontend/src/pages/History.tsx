import { useEffect, useState } from 'react';
import ArticleCard from '@/components/ArticleCard';
import { getReportById, getReports } from '@/services/api';
import type { Report } from '@/types';

export default function History() {
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [reports, setReports] = useState<Report[]>([]);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(false);
      try {
        const data = await getReports();
        setReports(data);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, []);

  const handleSelectReport = async (id: number) => {
    setDetailLoading(true);
    try {
      const report = await getReportById(id);
      setSelectedReport(report);
    } catch {
      setError(true);
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <section className="space-y-4">
      <h2 className="text-3xl font-semibold text-white">Report History</h2>

      {loading && (
        <div className="loading-block">
          <span className="spinner" />
          <span>Loading report history...</span>
        </div>
      )}
      {!loading && error && <p className="text-sm text-[#dc2626]">Failed to load report. Please try again.</p>}

      <div className="overflow-hidden rounded-lg border border-[#222222] bg-[#111111]">
        {!loading && !error && reports.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon" />
            <p>No report history yet.</p>
          </div>
        ) : (
          <table className="w-full text-left text-sm">
            <tbody>
              {reports.map((report) => (
                <tr
                  key={report.id}
                  className="cursor-pointer border-b border-[#222222] bg-[#111111] transition-colors hover:bg-[#151515]"
                  onClick={() => void handleSelectReport(report.id)}
                >
                  <td className="px-4 py-4 font-mono text-white">{report.report_date}</td>
                  <td className="px-4 py-4 text-[#888888]">
                    {report.total_articles_kept ?? 0} articles kept / {report.total_articles_found ?? 0} screened
                  </td>
                  <td className="px-4 py-4 text-right text-[#2563eb] hover:underline">View Report</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {detailLoading && (
        <div className="loading-block">
          <span className="spinner" />
          <span>Loading report details...</span>
        </div>
      )}

      {selectedReport && !detailLoading && (
        <div className="space-y-3">
          <button
            type="button"
            className="text-sm text-[#888888] transition-colors hover:text-white"
            onClick={() => setSelectedReport(null)}
          >
            ← Back to history
          </button>
          <h3 className="font-mono text-lg font-semibold text-white">Report {selectedReport.report_date}</h3>
          <div className="grid gap-3 md:grid-cols-2">
            {selectedReport.articles.map((article) => (
              <ArticleCard key={article.id} article={article} rejected={!article.kept} />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
