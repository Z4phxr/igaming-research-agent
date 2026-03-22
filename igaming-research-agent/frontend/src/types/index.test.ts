import type { Query, Report } from '@/types';


describe('types', () => {
  it('Query interface matches backend-style payload shape', () => {
    const query: Query = {
      id: 1,
      search_term: 'US iGaming',
      stream_type: 'business',
      description: null,
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    };

    expect(query.stream_type).toBe('business');
  });

  it('Report interface supports nested article arrays', () => {
    const report: Report = {
      id: 1,
      report_date: '2026-03-22',
      total_articles_found: 2,
      total_articles_kept: 1,
      generated_at: '2026-03-22T01:00:00Z',
      articles: [
        {
          id: 10,
          title: 'Story',
          url: 'https://example.com/story',
          summary: 'Summary',
          score: 7,
          tags: 'regulation',
          source_domain: 'example.com',
          published_date: '2026-03-22T00:00:00Z',
          scraped_date: '2026-03-22T01:00:00Z',
        },
      ],
    };

    expect(report.articles[0].url).toBe('https://example.com/story');
  });
});
