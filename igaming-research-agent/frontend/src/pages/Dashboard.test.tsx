import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import Dashboard from '@/pages/Dashboard';
import * as apiService from '@/services/api';


describe('Dashboard', () => {
  it('renders latest report from backend', async () => {
    vi.spyOn(apiService, 'getLatestReport').mockResolvedValue({
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
          kept: true,
          rejection_reason: null,
          passed_relevance_filter: true,
          tags: 'regulation',
          source_domain: 'example.com',
          published_date: '2026-03-22T00:00:00Z',
          scraped_date: '2026-03-22T00:00:00Z',
        },
      ],
      release_articles: [
        {
          id: 11,
          title: 'IGT Announces Q1 Release',
          url: 'https://example.com/release',
          summary: 'Press release summary',
          score: 0,
          kept: true,
          rejection_reason: null,
          passed_relevance_filter: true,
          tags: 'release',
          source_domain: 'example.com',
          article_type: 'release',
          published_date: '2026-03-22T01:00:00Z',
          scraped_date: '2026-03-22T01:00:00Z',
        },
      ],
    } as any);
    vi.spyOn(apiService, 'runPipeline').mockResolvedValue({ status: 'success', message: 'Pipeline completed' } as any);
    vi.spyOn(apiService, 'runArticlesPipeline').mockResolvedValue({ status: 'success', message: 'Articles pipeline completed' } as any);
    vi.spyOn(apiService, 'runReleasesPipeline').mockResolvedValue({ status: 'success', message: 'Releases pipeline completed' } as any);
    vi.spyOn(apiService, 'runReevaluateTopStories').mockResolvedValue({
      status: 'success',
      message: 'Top Stories re-evaluated using current published prompts',
      report_id: 1,
      processed_articles: 1,
      updated_articles: 1,
      kept_articles: 1,
    } as any);

    const user = userEvent.setup();
    render(<Dashboard />);

    expect(screen.getByRole('heading', { name: /daily intelligence report/i })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/articles screened/i)).toBeInTheDocument();
      expect(screen.getByText(/articles kept/i)).toBeInTheDocument();
      expect(screen.getByText(/pipeline actions/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /run all/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /run articles/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /run releases/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /re-evaluate/i })).toBeInTheDocument();
      expect(screen.getByText(/policy shift/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /new releases/i }));

    await waitFor(() => {
      expect(screen.getByText(/igt announces q1 release/i)).toBeInTheDocument();
      expect(screen.queryByText(/intelligence briefing/i)).not.toBeInTheDocument();
    });
  });
});
