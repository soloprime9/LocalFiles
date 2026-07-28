'use client'
import { useEffect, useState } from 'react';
import { 
  timeAgo, 
  formatPrice, 
  formatNumber, 
  getPlatformColor, 
  getAssetEmoji, 
  getTrustScoreColor 
} from '../../utils/helpers';

const HEIGHTS = { sm: 'h-1.5', md: 'h-2', lg: 'h-2.5' };
const TEXT_SIZES = { sm: 'text-xs', md: 'text-sm', lg: 'text-base' };

export default function TrustScore({ score = 0, size = 'md' }) {
  const [animatedWidth, setAnimatedWidth] = useState(0);
  const { text, bg } = trustScoreColor(score);

  useEffect(() => {
    const timer = setTimeout(() => setAnimatedWidth(score), 50);
    return () => clearTimeout(timer);
  }, [score]);

  return (
    <div className="group relative w-full">
      <div className="flex items-center justify-between mb-1">
        <span className={`${TEXT_SIZES[size]} text-gray-400`}>Trust Score</span>
        <span className={`${TEXT_SIZES[size]} font-semibold ${text}`}>{score}</span>
      </div>
      <div className={`w-full bg-[#1F2937] rounded-full overflow-hidden ${HEIGHTS[size]}`}>
        <div
          className={`${bg} ${HEIGHTS[size]} rounded-full transition-all duration-700 ease-out`}
          style={{ width: `${animatedWidth}%` }}
        />
      </div>
      <div className="absolute bottom-full left-0 mb-2 w-56 opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-10">
        <div className="bg-[#1A1A1A] border border-[#374151] rounded-lg px-3 py-2 text-xs text-gray-300 shadow-xl">
          Calculated from: rating, verified status, backtest audit, review count, scam reports
        </div>
      </div>
    </div>
  );
}
