import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import App from '@/App';
import * as apiService from '@/services/api';


describe('integration user flow', () => {
  it('adds query in settings, sees it in dashboard, and views history', async () => {
    const queries = [
      {
        id: 1,
        search_term: 'Baseline query',
        stream_type: 'business',
        description: null,
        is_active: true,
        created_at: '2026-03-22T00:00:00Z',
        updated_at: '2026-03-22T00:00:00Z',
      },
    ] as any[];

    const reports = [
      {
        id: 1,
        report_date: '2026-03-22',
        total_articles_found: 3,
        total_articles_kept: 1,
        generated_at: '2026-03-22T01:00:00Z',
        articles: [
          {
            id: 11,
            title: 'Daily summary article',
            url: 'https://example.com/daily',
            summary: 'summary',
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
      },
    ] as any[];

    vi.spyOn(apiService, 'getQueries').mockImplementation(async () => [...queries]);
    vi.spyOn(apiService, 'createQuery').mockImplementation(async (payload: any) => {
      const query = {
        id: queries.length + 1,
        search_term: payload.search_term,
        stream_type: payload.stream_type,
        description: payload.description ?? null,
        is_active: true,
        created_at: '2026-03-22T00:00:00Z',
        updated_at: '2026-03-22T00:00:00Z',
      };
      queries.push(query);
      return query as any;
    });
    vi.spyOn(apiService, 'updateQuery').mockResolvedValue({} as any);
    vi.spyOn(apiService, 'deleteQuery').mockResolvedValue();
    vi.spyOn(apiService, 'getPromptTemplates').mockResolvedValue([
      {
        id: 1,
        key: 'analyzer.relevance_system',
        title: 'Analyzer Relevance System Prompt',
        description: 'desc',
        draft_content: 'draft',
        active_content: 'active',
        active_version: 1,
        created_at: '2026-03-22T00:00:00Z',
        updated_at: '2026-03-22T00:00:00Z',
      },
    ] as any);
    vi.spyOn(apiService, 'getPromptTemplate').mockResolvedValue({
      id: 1,
      key: 'analyzer.relevance_system',
      title: 'Analyzer Relevance System Prompt',
      description: 'desc',
      draft_content: 'draft',
      active_content: 'active',
      active_version: 1,
      created_at: '2026-03-22T00:00:00Z',
      updated_at: '2026-03-22T00:00:00Z',
      history: [],
    } as any);
    vi.spyOn(apiService, 'getPromptHistory').mockResolvedValue([] as any);
    vi.spyOn(apiService, 'updatePromptDraft').mockResolvedValue({} as any);
    vi.spyOn(apiService, 'publishPrompt').mockResolvedValue({} as any);
    vi.spyOn(apiService, 'getReports').mockImplementation(async () => [...reports]);
    vi.spyOn(apiService, 'getLatestReport').mockImplementation(async () => reports[0] as any);
    vi.spyOn(apiService, 'getReportById').mockImplementation(async (id: number) => {
      return reports.find((report) => report.id === id) as any;
    });

    vi.spyOn(window, 'confirm').mockReturnValue(true);

    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('link', { name: /settings/i }));

    await user.type(screen.getByLabelText(/search query/i), ' Fresh legislative query');
    await user.click(screen.getByRole('button', { name: /add query/i }));

    await waitFor(() => {
      expect(screen.getByText(/fresh legislative query/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole('link', { name: /dashboard/i }));

    await waitFor(() => {
      expect(screen.getByText(/daily summary article/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole('link', { name: /history/i }));

    await waitFor(() => {
      expect(screen.getByText('2026-03-22')).toBeInTheDocument();
    });
  });
});
