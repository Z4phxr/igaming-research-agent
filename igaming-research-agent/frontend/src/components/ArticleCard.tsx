import { useState } from 'react';
import ScoreCorrectionModal from '@/components/ScoreCorrectionModal';
import { submitArticleFeedback } from '@/services/api';
import type { Article } from '@/types';

interface Props {
  article: Article;
  rejected?: boolean;
}

// TODO: Add score color scale and richer metadata chips.
export default function ArticleCard({ article, rejected = false }: Props) {
  const [feedbackMessage, setFeedbackMessage] = useState('');
  const [feedbackError, setFeedbackError] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [modalType, setModalType] = useState<'score_too_low' | 'score_too_high'>('score_too_low');

  const score = Number(article.score ?? 0);
  const tags = (article.tags || '')
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean);

  const rejectionLabel = article.rejection_reason === 'failed_relevance_filter'
    ? 'Rejected: failed relevance filter'
    : `Rejected: low score (${score}/10)`;

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

  return (
    <article
      className={`space-y-3 rounded-lg border bg-[#111111] p-4 transition-all duration-150 ease-in-out hover:border-[#333333] hover:bg-[#151515] ${
        rejected ? 'opacity-45 border-l-2 border-l-[#dc2626]' : ''
      } border-[#222222]`}
    >
      <div className="flex items-center justify-between gap-2">
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
        <span className="font-mono text-xs text-[#888888]">
          {article.source_domain || 'unknown source'}
          {' · '}
          {article.published_date ? new Date(article.published_date).toLocaleDateString() : 'unknown date'}
        </span>
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
        <p className="text-[11px] text-[#dc2626]">{rejectionLabel}</p>
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

      <a
        href={article.url}
        target="_blank"
        rel="noreferrer"
        className="text-xs text-[#2563eb] hover:underline"
      >
        Read source
      </a>

      <div className="flex items-center gap-2 pt-1">
        <button
          type="button"
          className="h-8 w-8 rounded-md bg-[#555555] text-white transition-colors hover:bg-[#2563eb]"
          aria-label="feedback-helpful"
          onClick={() => void submitHelpful()}
        >
          👍
        </button>
        <button
          type="button"
          className="h-8 w-8 rounded-md bg-[#555555] text-white transition-colors hover:bg-[#2563eb]"
          aria-label="feedback-score-too-low"
          onClick={() => openCorrection('score_too_low')}
        >
          ⬆️
        </button>
        <button
          type="button"
          className="h-8 w-8 rounded-md bg-[#555555] text-white transition-colors hover:bg-[#2563eb]"
          aria-label="feedback-score-too-high"
          onClick={() => openCorrection('score_too_high')}
        >
          ⬇️
        </button>
      </div>

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
