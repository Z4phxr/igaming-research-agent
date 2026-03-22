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
      generated_at: '2026-03-02T01:00:00Z',
      articles: [
        {
          id: 22,
          title: 'Picked report article',
          url: 'https://example.com/picked',
          summary: 'Summary',
          score: 7,
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
      expect(screen.getByText(/picked report article/i)).toBeInTheDocument();
    });
  });
});
