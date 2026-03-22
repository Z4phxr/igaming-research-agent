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
      <h2 className="text-2xl font-bold">Report History</h2>

      {loading && <p className="text-sm text-gray-600">Loading report history...</p>}
      {!loading && error && <p className="text-sm text-red-600">Failed to load report. Please try again.</p>}

      <div className="bg-white border rounded p-4 text-sm text-gray-600">
        {!loading && !error && reports.length === 0 ? (
          <p>No report history yet.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-gray-500">
                <th className="py-2">Report date</th>
                <th className="py-2">Kept</th>
                <th className="py-2">Screened</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((report) => (
                <tr
                  key={report.id}
                  className="cursor-pointer border-t hover:bg-gray-50"
                  onClick={() => void handleSelectReport(report.id)}
                >
                  <td className="py-2">{report.report_date}</td>
                  <td className="py-2">{report.total_articles_kept ?? 0}</td>
                  <td className="py-2">{report.total_articles_found ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {detailLoading && <p className="text-sm text-gray-600">Loading report details...</p>}

      {selectedReport && !detailLoading && (
        <div className="space-y-3">
          <h3 className="text-lg font-semibold">Report {selectedReport.report_date}</h3>
          <div className="grid gap-3 md:grid-cols-2">
            {selectedReport.articles.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
