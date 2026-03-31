import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import History from '@/pages/History';
import * as apiService from '@/services/api';


describe('History', () => {
  it('loads report list and fetches selected report details', async () => {
    vi.spyOn(apiService, 'getReports').mockResolvedValue([
      {
        id: 1,
        report_date: '2026-03-01',
        total_articles_found: 10,
        total_articles_kept: 5,
        generated_at: '2026-03-01T01:00:00Z',
        articles: [],
      },
      {
        id: 2,
        report_date: '2026-03-02',
        total_articles_found: 8,
        total_articles_kept: 3,
        generated_at: '2026-03-02T01:00:00Z',
        articles: [],
      },
    ] as any);
    vi.spyOn(apiService, 'getReportById').mockResolvedValue({
      id: 2,
      report_date: '2026-03-02',
      total_articles_found: 8,
      total_articles_kept: 3,
      briefing: '## Executive Summary\nStrong regulatory momentum this week.',
      briefing_generated_at: '2026-03-02T02:00:00Z',
      generated_at: '2026-03-02T01:00:00Z',
      articles: [
        {
          id: 22,
          title: 'Picked report article',
          url: 'https://example.com/picked',
          summary: 'Summary',
          score: 7,
          kept: true,
          rejection_reason: null,
          passed_relevance_filter: true,
          tags: 'regulation',
          source_domain: 'example.com',
          published_date: '2026-03-02T00:00:00Z',
          scraped_date: '2026-03-02T00:00:00Z',
        },
      ],
    } as any);

    render(<History />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText('2026-03-01')).toBeInTheDocument();
      expect(screen.getByText('2026-03-02')).toBeInTheDocument();
    });

    await user.click(screen.getByText('2026-03-02'));

    await waitFor(() => {
      expect(screen.getByText(/executive summary/i)).toBeInTheDocument();
      expect(screen.getByText(/strong regulatory momentum this week/i)).toBeInTheDocument();
      expect(screen.getByText(/picked report article/i)).toBeInTheDocument();
      expect(screen.getByText(/hide report/i)).toBeInTheDocument();
    });
  });

  it('paginates report history by 10 items per page', async () => {
    const reports = Array.from({ length: 12 }).map((_, index) => ({
      id: index + 1,
      report_date: `2026-03-${String(index + 1).padStart(2, '0')}`,
      total_articles_found: 10,
      total_articles_kept: 5,
      generated_at: '2026-03-01T01:00:00Z',
      articles: [],
    }));

    vi.spyOn(apiService, 'getReports').mockResolvedValue(reports as any);
    vi.spyOn(apiService, 'getReportById').mockResolvedValue({
      id: 12,
      report_date: '2026-03-12',
      total_articles_found: 10,
      total_articles_kept: 5,
      generated_at: '2026-03-12T01:00:00Z',
      articles: [],
    } as any);

    const user = userEvent.setup();
    render(<History />);

    await waitFor(() => {
      expect(screen.getByText('2026-03-01')).toBeInTheDocument();
      expect(screen.queryByText('2026-03-11')).not.toBeInTheDocument();
      expect(screen.getByText(/page 1 \/ 2/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /next/i }));

    await waitFor(() => {
      expect(screen.getByText('2026-03-11')).toBeInTheDocument();
      expect(screen.getByText('2026-03-12')).toBeInTheDocument();
      expect(screen.queryByText('2026-03-01')).not.toBeInTheDocument();
      expect(screen.getByText(/page 2 \/ 2/i)).toBeInTheDocument();
    });
  });
});
