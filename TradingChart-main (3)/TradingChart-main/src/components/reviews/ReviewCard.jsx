'use client'
import { useState } from 'react';
import { ThumbsUp, ThumbsDown, CheckCircle2 } from 'lucide-react';
import StarRating from '../ui/StarRating';
import { timeAgo, initials, colorFromString } from '../../utils/helpers';
import { markHelpful, markNotHelpful } from '../../utils/api';

const REVIEWER_TYPE_COLORS = {
  Beginner: 'bg-gray-500/15 text-gray-300',
  Intermediate: 'bg-blue-500/15 text-blue-400',
  Pro: 'bg-amber-500/15 text-amber-400',
  Institutional: 'bg-violet-500/15 text-violet-400',
};

export default function ReviewCard({ review }) {
  const [helpful, setHelpful] = useState(review.helpful || 0);
  const [notHelpful, setNotHelpful] = useState(review.notHelpful || 0);
  const [voted, setVoted] = useState(null);

  const {
    reviewerName,
    reviewerType,
    rating,
    title,
    body,
    tradingPeriod,
    assetTraded,
    timeframeUsed,
    profitableForReviewer,
    wouldRecommend,
    verified,
    createdAt,
    _id,
  } = review;

  const handleHelpful = async () => {
    if (voted) return;
    setHelpful((h) => h + 1);
    setVoted('helpful');
    try {
      await markHelpful(_id);
    } catch {
      // optimistic update stays even if request fails silently
    }
  };

  const handleNotHelpful = async () => {
    if (voted) return;
    setNotHelpful((n) => n + 1);
    setVoted('notHelpful');
    try {
      await markNotHelpful(_id);
    } catch {
      // optimistic update stays even if request fails silently
    }
  };

  return (
    <div className="bg-[#111111] border border-[#1F2937] rounded-xl p-5">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-3">
          <div
            className={`w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-semibold shrink-0 ${colorFromString(
              reviewerName
            )}`}
          >
            {initials(reviewerName)}
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-white font-medium text-sm">{reviewerName}</span>
              {verified && (
                <span className="flex items-center gap-0.5 text-emerald-400 text-xs">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Verified
                </span>
              )}
              {reviewerType && (
                <span
                  className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    REVIEWER_TYPE_COLORS[reviewerType] || 'bg-gray-500/15 text-gray-300'
                  }`}
                >
                  {reviewerType}
                </span>
              )}
            </div>
            <span className="text-xs text-gray-500">{timeAgo(createdAt)}</span>
          </div>
        </div>
        <StarRating rating={rating} size="sm" />
      </div>

      <h4 className="text-white font-semibold mb-1.5">{title}</h4>
      <p className="text-sm text-gray-400 leading-relaxed mb-3">{body}</p>

      <div className="flex flex-wrap gap-1.5 mb-3">
        {tradingPeriod && (
          <span className="px-2 py-0.5 rounded-full bg-[#1A1A1A] border border-[#1F2937] text-xs text-gray-400">
            {tradingPeriod}
          </span>
        )}
        {assetTraded && (
          <span className="px-2 py-0.5 rounded-full bg-[#1A1A1A] border border-[#1F2937] text-xs text-gray-400">
            {assetTraded}
          </span>
        )}
        {timeframeUsed && (
          <span className="px-2 py-0.5 rounded-full bg-[#1A1A1A] border border-[#1F2937] text-xs text-gray-400">
            {timeframeUsed}
          </span>
        )}
      </div>

      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <span
          className={`text-xs font-medium ${
            profitableForReviewer ? 'text-emerald-400' : 'text-red-400'
          }`}
        >
          {profitableForReviewer ? '✓ Profitable' : '✗ Not Profitable'}
        </span>
        <span className={`text-xs font-medium ${wouldRecommend ? 'text-emerald-400' : 'text-gray-500'}`}>
          {wouldRecommend ? 'Would Recommend' : "Wouldn't Recommend"}
        </span>
      </div>

      <div className="flex items-center gap-4 pt-3 border-t border-[#1F2937]">
        <span className="text-xs text-gray-500">Helpful?</span>
        <button
          type="button"
          onClick={handleHelpful}
          disabled={!!voted}
          className={`flex items-center gap-1 text-xs transition-colors ${
            voted === 'helpful' ? 'text-emerald-400' : 'text-gray-400 hover:text-white'
          }`}
        >
          <ThumbsUp className="w-3.5 h-3.5" /> {helpful}
        </button>
        <button
          type="button"
          onClick={handleNotHelpful}
          disabled={!!voted}
          className={`flex items-center gap-1 text-xs transition-colors ${
            voted === 'notHelpful' ? 'text-red-400' : 'text-gray-400 hover:text-white'
          }`}
        >
          <ThumbsDown className="w-3.5 h-3.5" /> {notHelpful}
        </button>
      </div>
    </div>
  );
}
