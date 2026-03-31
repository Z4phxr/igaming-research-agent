import { Fragment, useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import ArticleCard from '@/components/ArticleCard';
import { getReportById, getReports } from '@/services/api';
import type { Report } from '@/types';

export default function History() {
  const REPORTS_PER_PAGE = 10;
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [reports, setReports] = useState<Report[]>([]);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
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

  const totalPages = Math.max(1, Math.ceil(reports.length / REPORTS_PER_PAGE));
  const startIndex = (currentPage - 1) * REPORTS_PER_PAGE;
  const paginatedReports = reports.slice(startIndex, startIndex + REPORTS_PER_PAGE);

  const handleSelectReport = async (id: number) => {
    if (selectedReportId === id) {
      setSelectedReportId(null);
      setSelectedReport(null);
      return;
    }

    setSelectedReportId(id);
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
              {paginatedReports.map((report) => (
                <Fragment key={report.id}>
                  <tr
                    className="cursor-pointer border-b border-[#222222] bg-[#111111] transition-colors hover:bg-[#151515]"
                    onClick={() => void handleSelectReport(report.id)}
                  >
                    <td className="px-4 py-4 font-mono text-white">{report.report_date}</td>
                    <td className="px-4 py-4 text-[#888888]">
                      {report.total_articles_kept ?? 0} articles kept / {report.total_articles_found ?? 0} screened
                    </td>
                    <td className="px-4 py-4 text-right text-[#2563eb] hover:underline">
                      {selectedReportId === report.id ? 'Hide Report' : 'View Report'}
                    </td>
                  </tr>
                  {selectedReportId === report.id && (
                    <tr className="border-b border-[#222222] bg-[#0f0f0f]">
                      <td colSpan={3} className="px-4 py-4">
                        {detailLoading && (
                          <div className="loading-block">
                            <span className="spinner" />
                            <span>Loading report details...</span>
                          </div>
                        )}
                        {selectedReport && !detailLoading && selectedReport.id === report.id && (
                          <div className="space-y-3">
                            <h3 className="font-mono text-lg font-semibold text-white">Report {selectedReport.report_date}</h3>

                            <div className="space-y-2">
                              <p className="text-[11px] uppercase tracking-[0.1em] text-[#555555]">Intelligence Briefing</p>
                              <div className="rounded-lg border border-[#222222] bg-[#111111] p-4">
                                {selectedReport.briefing ? (
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
                                    {selectedReport.briefing}
                                  </ReactMarkdown>
                                ) : (
                                  <p className="text-sm text-[#555555]">Briefing not available for this report</p>
                                )}
                              </div>
                              <p className="text-[11px] text-[#555555]">
                                {selectedReport.briefing_generated_at
                                  ? `Generated ${new Date(selectedReport.briefing_generated_at).toLocaleString()}`
                                  : 'Briefing timestamp unavailable'}
                              </p>
                            </div>

                            <div className="grid gap-3 md:grid-cols-2">
                              {selectedReport.articles.map((article) => (
                                <ArticleCard key={article.id} article={article} rejected={!article.kept} />
                              ))}
                            </div>
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {!loading && !error && reports.length > REPORTS_PER_PAGE && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-[#555555]">
            Showing {startIndex + 1}-{Math.min(startIndex + REPORTS_PER_PAGE, reports.length)} of {reports.length}
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="rounded border border-[#333333] bg-[#111111] px-3 py-1 text-xs text-[#888888] hover:text-white disabled:opacity-50"
              disabled={currentPage === 1}
              onClick={() => {
                setCurrentPage((prev) => Math.max(1, prev - 1));
                setSelectedReportId(null);
                setSelectedReport(null);
              }}
            >
              Previous
            </button>
            <span className="text-xs text-[#888888]">Page {currentPage} / {totalPages}</span>
            <button
              type="button"
              className="rounded border border-[#333333] bg-[#111111] px-3 py-1 text-xs text-[#888888] hover:text-white disabled:opacity-50"
              disabled={currentPage === totalPages}
              onClick={() => {
                setCurrentPage((prev) => Math.min(totalPages, prev + 1));
                setSelectedReportId(null);
                setSelectedReport(null);
              }}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
