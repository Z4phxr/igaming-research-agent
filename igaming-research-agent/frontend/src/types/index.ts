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
  article_type?: 'top_story' | 'release';
  tags: string;
  source_domain: string;
  /** Datetime string from backend (often ISO without `Z`); interpret as UTC when offset is missing. */
  published_date?: string | null;
  scraped_date: string;
  kept: boolean;
  rejection_reason: string | null;
  passed_relevance_filter: boolean;
  rejection_stage?: string | null;
  rejection_score?: number | null;
  rejection_detail?: string | null;
  rejection_llm_why?: string | null;
  matched_query_id?: number | null;
  matched_search_term?: string | null;
}

export interface ReleaseFailedSource {
  company_name: string;
  source_url: string;
  reason: string | null;
  checked_at: string | null;
}

export interface Report {
  id: number;
  report_date: string;
  generated_at: string;
  articles_pipeline_ran_at?: string | null;
  releases_pipeline_ran_at?: string | null;
  total_articles_found: number;
  total_articles_kept: number;
  briefing?: string | null;
  briefing_generated_at?: string | null;
  articles: Article[];
  release_articles?: Article[];
  release_recent_window_hours?: number;
  release_failed_sources?: ReleaseFailedSource[];
}

export interface ReleaseSource {
  id: number;
  company_name: string;
  category: string;
  source_url: string;
  notes?: string | null;
  source_tier?: number;
  preferred_method?: string;
  crawl_delay_seconds?: number;
  max_requests_per_hour?: number;
  consecutive_failures?: number;
  health_score?: number;
  quarantine_until?: string | null;
  last_failure_reason?: string | null;
  last_success_at?: string | null;
  last_listing_checked_at?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ReleaseSourceHealthCheckResult {
  source_id: number;
  company_name: string;
  source_url: string;
  passed: boolean;
  latest_article_url: string | null;
  latest_article_title: string | null;
  latest_article_published_at: string | null;
  latest_article_age_hours: number | null;
  error_log: string | null;
  checked_at: string;
}

export interface ReleaseSourceHealthCheckResponse {
  status: string;
  checked_at: string;
  total_sources: number;
  passed_sources: number;
  failed_sources: number;
  results: ReleaseSourceHealthCheckResult[];
}

export interface SingleReleaseSourceHealthCheckResponse {
  status: string;
  checked_at: string;
  result: ReleaseSourceHealthCheckResult;
}

export interface CreateReleaseSourceDto {
  company_name: string;
  category: string;
  source_url: string;
  notes?: string;
  is_active: boolean;
}

export interface UpdateReleaseSourceDto {
  company_name?: string;
  category?: string;
  source_url?: string;
  notes?: string;
  is_active?: boolean;
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

export interface PromptTemplateVersion {
  id: number;
  version: number;
  content: string;
  is_active: boolean;
  created_at: string;
}

export interface PromptTemplate {
  id: number;
  key: string;
  title: string;
  description: string | null;
  draft_content: string;
  active_content: string;
  active_version: number;
  created_at: string;
  updated_at: string;
}

export interface PromptTemplateDetail extends PromptTemplate {
  history: PromptTemplateVersion[];
}
