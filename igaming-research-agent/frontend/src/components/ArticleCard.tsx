import { useState } from 'react';
import ScoreCorrectionModal from '@/components/ScoreCorrectionModal';
import { submitArticleFeedback } from '@/services/api';
import type { Article } from '@/types';

interface Props {
  article: Article;
  rejected?: boolean;
  showAllInfo?: boolean;
  compactRelease?: boolean;
}

/** Short display date when we have a parseable ISO/string from Serper or pipeline. */
function formatShortPublishedDate(raw: string | null | undefined): string | null {
  const s = (raw || '').trim();
  if (!s) return null;
  const parsed = new Date(s);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  });
}

// TODO: Add score color scale and richer metadata chips.
export default function ArticleCard({
  article,
  rejected = false,
  showAllInfo = false,
  compactRelease = false,
}: Props) {
  const [feedbackMessage, setFeedbackMessage] = useState('');
  const [feedbackError, setFeedbackError] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [modalType, setModalType] = useState<'score_too_low' | 'score_too_high'>('score_too_low');

  const score = Number(article.score ?? 0);
  const tags = (article.tags || '')
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean);

  const reason = article.rejection_reason ?? '';
  const freshnessReasons = new Set([
    'Rejected: fail to check the date',
    'invalid_published_date',
    'missing_published_date',
    'stale_published_date',
    'future_published_date',
  ]);

  const rejectionLabel = reason === 'failed_relevance_filter'
    ? 'Rejected: failed relevance filter'
    : reason === 'score_below_threshold'
      ? `Rejected: low score (${score}/10)`
      : freshnessReasons.has(reason)
        ? 'Rejected: invalid_published_date'
        : reason
          ? `Rejected: ${reason}`
          : 'Rejected';

  const submitHelpful = async (): Promise<void> => {
    setFeedbackError('');
    try {
      const response = await submitArticleFeedback(article.id, 'helpful');
      setFeedbackMessage(response.message);
      setTimeout(() => setFeedbackMessage(''), 1200);
    } catch (error) {
      setFeedbackError(error instanceof Error ? error.message : 'Feedback failed');
    }
  };

  const openCorrection = (type: 'score_too_low' | 'score_too_high'): void => {
    setFeedbackError('');
    setFeedbackMessage('');
    setModalType(type);
    setModalOpen(true);
  };

  const submitCorrection = async (correctedScore: number): Promise<void> => {
    await submitArticleFeedback(article.id, modalType, correctedScore);
    setFeedbackMessage("Thanks! We'll learn from this.");
    setFeedbackError('');
    setTimeout(() => setFeedbackMessage(''), 1500);
  };

  if (compactRelease) {
    const rawDate = article.published_date || article.scraped_date;
    const formattedDate = rawDate
      ? new Date(rawDate).toLocaleString('en-US', {
          year: 'numeric',
          month: 'short',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
        })
      : 'Date unavailable';

    return (
      <article className="space-y-2.5 rounded-lg border border-[#222222] bg-[#111111] p-4 transition-all duration-150 ease-in-out hover:border-[#333333] hover:bg-[#151515]">
        <p className="font-mono text-xs text-[#888888]">{formattedDate}</p>
        <p className="text-xs uppercase tracking-[0.08em] text-[#2563eb]">
          {article.source_domain || 'unknown source'}
        </p>
        <a
          href={article.url}
          target="_blank"
          rel="noreferrer"
          className="text-base font-semibold text-white hover:text-[#2563eb]"
        >
          {article.title}
        </a>
      </article>
    );
  }

  const publishedDisplay = formatShortPublishedDate(article.published_date);

  return (
    <article
      className={`space-y-3 rounded-lg border bg-[#111111] p-4 transition-all duration-150 ease-in-out hover:border-[#333333] hover:bg-[#151515] ${
        rejected ? 'opacity-45 border-l-2 border-l-[#dc2626]' : ''
      } border-[#222222]`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className={`rounded px-2 py-1 font-mono text-xs ${
              rejected
                ? article.rejection_reason === 'failed_relevance_filter'
                  ? 'bg-[#1c0a0a] text-[#dc2626]'
                  : 'bg-[#1f2937] text-[#9ca3af]'
                : score >= 8
                  ? 'bg-[#14532d] text-[#16a34a]'
                  : 'bg-[#451a03] text-[#d97706]'
            }`}
          >
            {score.toFixed(1)}
          </span>

          <button
            type="button"
            className="flex h-8 w-8 items-center justify-center rounded-md bg-[#555555] text-white transition-colors hover:bg-[#2563eb]"
            aria-label="feedback-helpful"
            onClick={() => void submitHelpful()}
          >
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M7 11v10H4V11h3z" />
              <path d="M7 11l4-8h2a2 2 0 0 1 2 2v4h4a2 2 0 0 1 2 2l-1 8a2 2 0 0 1-2 2H7" />
            </svg>
          </button>
          <button
            type="button"
            className="flex h-8 w-8 items-center justify-center rounded-md bg-[#555555] text-white transition-colors hover:bg-[#2563eb]"
            aria-label="feedback-score-too-low"
            onClick={() => openCorrection('score_too_low')}
          >
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 19V5" />
              <path d="M6 11l6-6 6 6" />
            </svg>
          </button>
          <button
            type="button"
            className="flex h-8 w-8 items-center justify-center rounded-md bg-[#555555] text-white transition-colors hover:bg-[#2563eb]"
            aria-label="feedback-score-too-high"
            onClick={() => openCorrection('score_too_high')}
          >
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 5v14" />
              <path d="M18 13l-6 6-6-6" />
            </svg>
          </button>
        </div>
        <div className="text-right font-mono text-[11px] leading-tight text-[#888888]">
          {publishedDisplay ? (
            <span className="mb-0.5 block text-[#666666]">{publishedDisplay}</span>
          ) : null}
          <span className="block text-xs">{article.source_domain || 'unknown source'}</span>
        </div>
      </div>

      <div className="flex items-start justify-between gap-2">
        <a
          href={article.url}
          target="_blank"
          rel="noreferrer"
          className="text-base font-semibold text-white hover:text-[#2563eb]"
        >
          {article.title}
        </a>
      </div>

      {rejected && (
        <div className="space-y-1">
          <p className="text-[11px] text-[#dc2626]">{rejectionLabel}</p>
          {article.rejection_detail && (
            <p className="text-[11px] text-[#fca5a5]">{article.rejection_detail}</p>
          )}
          {article.rejection_score !== undefined && article.rejection_score !== null && (
            <p className="text-[11px] text-[#fca5a5]">Score received: {article.rejection_score}/10</p>
          )}
          {showAllInfo && article.rejection_llm_why && (
            <p className="text-[11px] text-[#fcd34d]">LLM why: {article.rejection_llm_why}</p>
          )}
        </div>
      )}

      <p className="mt-2 text-sm leading-6 text-[#888888]">{article.summary || 'No summary yet.'}</p>

      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {tags.map((tag) => (
            <span
              key={tag}
              className="rounded border border-[#222222] bg-[#1a1a1a] px-2 py-1 text-[11px] uppercase tracking-[0.05em] text-[#555555]"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {feedbackMessage && <p className="text-xs text-[#16a34a]">{feedbackMessage}</p>}
      {feedbackError && <p className="text-xs text-[#dc2626]">{feedbackError}</p>}

      <ScoreCorrectionModal
        open={modalOpen}
        currentScore={score}
        onClose={() => setModalOpen(false)}
        onSubmit={submitCorrection}
      />
    </article>
  );
}
