import { render, screen } from '@testing-library/react';

import ArticleCard from '@/components/ArticleCard';


describe('ArticleCard', () => {
  it('renders article title, summary, score and source link', () => {
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
          published_date: '2026-03-22T00:00:00Z',
          scraped_date: new Date().toISOString(),
        }}
      />,
    );

    expect(screen.getByText('US iGaming market expands')).toBeInTheDocument();
    expect(screen.getByText('Regulatory momentum continues.')).toBeInTheDocument();
    expect(screen.getByText('8.0')).toBeInTheDocument();
    expect(screen.getByText('regulation')).toBeInTheDocument();
    expect(screen.getByText('licensing')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /read source/i })).toHaveAttribute(
      'href',
      'https://example.com/article',
    );
  });
});
