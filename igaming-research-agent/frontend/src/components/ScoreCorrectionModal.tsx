import { useEffect, useState } from 'react';

interface ScoreCorrectionModalProps {
  open: boolean;
  currentScore: number;
  onSubmit: (score: number) => Promise<void>;
  onClose: () => void;
}

export default function ScoreCorrectionModal({
  open,
  currentScore,
  onSubmit,
  onClose,
}: ScoreCorrectionModalProps) {
  const [selectedScore, setSelectedScore] = useState<number>(Math.min(10, Math.max(1, Math.round(currentScore || 6))));
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (open) {
      setSelectedScore(Math.min(10, Math.max(1, Math.round(currentScore || 6))));
      setMessage('');
      setError('');
      setLoading(false);
    }
  }, [open, currentScore]);

  if (!open) {
    return null;
  }

  const handleSubmit = async () => {
    setLoading(true);
    setError('');
    try {
      await onSubmit(selectedScore);
      setMessage("Thanks! We'll learn from this.");
      setTimeout(() => {
        onClose();
      }, 1000);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Failed to submit feedback');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-md rounded-lg border border-[#222222] bg-[#111111] p-5">
        <h3 className="text-lg font-semibold text-white">What should the score be?</h3>
        <p className="mt-2 text-sm text-[#888888]">
          Current: <span className="font-mono">{currentScore}/10</span> {' -> '} Your suggestion:{' '}
          <span className="font-mono text-[#2563eb]">{selectedScore}/10</span>
        </p>

        <div className="mt-4">
          <input
            type="range"
            min={1}
            max={10}
            value={selectedScore}
            onChange={(e) => setSelectedScore(Number(e.target.value))}
            className="w-full accent-[#2563eb]"
          />
        </div>

        {message && <p className="mt-3 text-sm text-[#16a34a]">{message}</p>}
        {error && <p className="mt-3 text-sm text-[#dc2626]">{error}</p>}

        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-[#333333] px-3 py-2 text-sm text-[#888888] hover:text-white"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void handleSubmit()}
            className="rounded-md bg-[#2563eb] px-4 py-2 text-sm font-medium text-white hover:bg-[#1d4ed8] disabled:opacity-50"
            disabled={loading}
          >
            {loading ? 'Submitting...' : 'Submit'}
          </button>
        </div>
      </div>
    </div>
  );
}
