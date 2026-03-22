import type { Article } from '@/types';

interface Props {
  article: Article;
}

// TODO: Add score color scale and richer metadata chips.
export default function ArticleCard({ article }: Props) {
  const score = Number(article.score ?? 0);
  const scoreClass = score >= 8 ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700';
  const tags = (article.tags || '')
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean);

  return (
    <article className="bg-white rounded-lg border p-4 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <a
          href={article.url}
          target="_blank"
          rel="noreferrer"
          className="font-semibold text-sm text-blue-700 hover:underline"
        >
          {article.title}
        </a>
        <span className={`text-xs px-2 py-1 rounded ${scoreClass}`}>
          {score} / 10
        </span>
      </div>

      <p className="text-xs text-gray-500">
        {article.source_domain || 'unknown source'}
        {' · '}
        {article.published_date ? new Date(article.published_date).toLocaleDateString() : 'unknown date'}
      </p>

      <p className="text-sm text-gray-600">{article.summary || 'No summary yet.'}</p>

      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {tags.map((tag) => (
            <span key={tag} className="text-xs px-2 py-1 rounded bg-slate-100 text-slate-700">
              {tag}
            </span>
          ))}
        </div>
      )}

      <a
        href={article.url}
        target="_blank"
        rel="noreferrer"
        className="text-blue-600 text-xs hover:underline"
      >
        Read source
      </a>
    </article>
  );
}
