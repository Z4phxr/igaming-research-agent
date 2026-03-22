import { render, screen, waitFor } from '@testing-library/react';

import Dashboard from '@/pages/Dashboard';
import * as apiService from '@/services/api';


describe('Dashboard', () => {
  it('renders latest report from backend', async () => {
    vi.spyOn(apiService, 'getReports').mockResolvedValue([
      {
        id: 1,
        report_date: '2026-03-22',
        total_articles_found: 2,
        total_articles_kept: 1,
        generated_at: '2026-03-22T00:00:00Z',
        articles: [
          {
            id: 10,
            title: 'Policy shift',
            url: 'https://example.com/policy',
            summary: 'Important summary',
            score: 8,
            tags: 'regulation',
            source_domain: 'example.com',
            published_date: '2026-03-22T00:00:00Z',
            scraped_date: '2026-03-22T00:00:00Z',
          },
        ],
      },
    ] as any);

    render(<Dashboard />);

    expect(screen.getByRole('heading', { name: /today's report/i })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/report date: 2026-03-22/i)).toBeInTheDocument();
      expect(screen.getByText(/total screened:/i)).toBeInTheDocument();
      expect(screen.getByText(/total kept:/i)).toBeInTheDocument();
      expect(screen.getByText(/policy shift/i)).toBeInTheDocument();
    });
  });
});
