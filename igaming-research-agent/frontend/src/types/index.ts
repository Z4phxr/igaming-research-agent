// TODO: Keep these interfaces synced with backend response schemas.

export interface Query {
  id: number;
  search_term: string;
  stream_type: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Article {
  id: number;
  title: string;
  url: string;
  summary: string;
  score: number;
  raw_score?: number;
  tags: string;
  source_domain: string;
  published_date: string;
  scraped_date: string;
  kept: boolean;
  rejection_reason: string | null;
  passed_relevance_filter: boolean;
}

export interface Report {
  id: number;
  report_date: string;
  generated_at: string;
  total_articles_found: number;
  total_articles_kept: number;
  articles: Article[];
}

export interface CreateQueryDto {
  search_term: string;
  stream_type: string;
  description?: string;
  is_active: boolean;
}

export interface UpdateQueryDto {
  search_term?: string;
  stream_type?: string;
  description?: string;
  is_active?: boolean;
}

export type FeedbackType = 'helpful' | 'score_too_low' | 'score_too_high';

export interface ArticleFeedback {
  article_id: number;
  feedback_type: FeedbackType;
  user_corrected_score: number | null;
  created_at: string;
}
