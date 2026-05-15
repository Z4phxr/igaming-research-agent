import { render, screen } from '@testing-library/react';

import ArticleCard from '@/components/ArticleCard';


describe('ArticleCard', () => {
  it('renders article title, summary, score and tags', () => {
    render(
      <ArticleCard
        article={{
          id: 1,
          title: 'US iGaming market expands',
          url: 'https://example.com/article',
          summary: 'Regulatory momentum continues.',
          score: 8,
          kept: true,
          rejection_reason: null,
          passed_relevance_filter: true,
          tags: 'regulation, licensing',
          source_domain: 'example.com',
          published_date: '2026-03-22T00:00:00',
          scraped_date: new Date().toISOString(),
        }}
      />,
    );

    expect(screen.getByText('US iGaming market expands')).toBeInTheDocument();
    expect(screen.getByText('Regulatory momentum continues.')).toBeInTheDocument();
    expect(screen.getByText('8.0')).toBeInTheDocument();
    expect(screen.getByText('Mar 22, 2026')).toBeInTheDocument();
    expect(screen.getByText('regulation')).toBeInTheDocument();
    expect(screen.getByText('licensing')).toBeInTheDocument();
  });

  it('compact release row parses naive UTC datetime (no Z) without breaking', () => {
    render(
      <ArticleCard
        compactRelease
        article={{
          id: 3,
          title: 'Press note',
          url: 'https://example.com/pr',
          summary: '',
          score: 0,
          kept: true,
          rejection_reason: null,
          passed_relevance_filter: true,
          tags: '',
          source_domain: 'vendor.test',
          published_date: '2026-06-02T14:30:00',
          scraped_date: new Date().toISOString(),
        }}
      />,
    );

    expect(screen.getByText(/Jun 02, 2026,\s02:30 PM/)).toBeInTheDocument();
    expect(screen.getByText('Press note')).toBeInTheDocument();
  });

  it('renders freshness rejection label without low-score fallback', () => {
    render(
      <ArticleCard
        rejected
        article={{
          id: 2,
          title: 'Date parsing edge case',
          url: 'https://example.com/date-edge',
          summary: 'Summary',
          score: 0,
          kept: false,
          rejection_reason: 'invalid_published_date',
          passed_relevance_filter: false,
          tags: '',
          source_domain: 'example.com',
          published_date: '',
          scraped_date: new Date().toISOString(),
        }}
      />,
    );

    expect(screen.getByText('Rejected: invalid_published_date')).toBeInTheDocument();
    expect(screen.queryByText('Rejected: low score (0/10)')).not.toBeInTheDocument();
  });
});
