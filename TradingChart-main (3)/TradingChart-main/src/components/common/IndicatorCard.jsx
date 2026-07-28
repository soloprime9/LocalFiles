import React from 'react';
import { Link } from 'react-router-dom';
import { StarIcon, HeartIcon, EyeIcon, ScaleIcon } from '@heroicons/react/24/outline';
import { StarIcon as StarSolid } from '@heroicons/react/24/solid';
import clsx from 'clsx';
import { formatPrice, formatNumber, getListingTypeIcon, getPlatformColor, truncate } from '../../utils/helpers';
import { useAppContext, value } from '../../context/AppContext';

export default function IndicatorCard({ indicator, showCompare = true }) {
  const { state, dispatch } = useApp();
  const inCompare = state.compareList.some((i) => i._id === indicator._id);

  const handleCompare = (e) => {
    e.preventDefault();
    if (inCompare) {
      dispatch({ type: ACTIONS.REMOVE_FROM_COMPARE, payload: indicator._id });
    } else if (state.compareList.length < 3) {
      dispatch({ type: ACTIONS.ADD_TO_COMPARE, payload: indicator });
    }
  };

  const rating = indicator.averageRating || indicator.rating || 0;
  const winRate = indicator.winRate || indicator.performance?.winRate;

  return (
    <Link to={`/indicators/${indicator.slug}`} className="block group">
      <div className="card card-hover h-full flex flex-col p-4 relative">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-2xl">{getListingTypeIcon(indicator.listingType)}</span>
            <div>
              <h3 className="text-white font-semibold text-sm leading-snug group-hover:text-amber-400 transition-colors">
                {truncate(indicator.name, 40)}
              </h3>
              {indicator.author && (
                <p className="text-gray-600 text-xs mt-0.5">by {indicator.author}</p>
              )}
            </div>
          </div>
          <div className="flex flex-col items-end gap-1 flex-shrink-0">
            {indicator.isFeatured && (
              <span className="badge-paid text-[10px] px-1.5 py-0.5">⭐ Featured</span>
            )}
            {indicator.isScam && (
              <span className="badge-scam text-[10px] px-1.5 py-0.5">⚠ Scam</span>
            )}
            {indicator.isVerified && !indicator.isScam && (
              <span className="badge-verified text-[10px] px-1.5 py-0.5">✓ Verified</span>
            )}
          </div>
        </div>

        {/* Description */}
        <p className="text-gray-500 text-xs leading-relaxed mb-3 flex-1">
          {truncate(indicator.shortDescription || indicator.description, 90)}
        </p>

        {/* Platform badges */}
        {indicator.platforms?.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {indicator.platforms.slice(0, 3).map((p) => (
              <span
                key={p}
                className={clsx(
                  'inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border',
                  getPlatformColor(p)
                )}
              >
                {p}
              </span>
            ))}
            {indicator.platforms.length > 3 && (
              <span className="text-gray-600 text-[10px]">+{indicator.platforms.length - 3}</span>
            )}
          </div>
        )}

        {/* Stats Row */}
        <div className="flex items-center justify-between pt-3 border-t border-[#1F2937]">
          <div className="flex items-center gap-3">
            {/* Rating */}
            <div className="flex items-center gap-1">
              <StarSolid className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-white text-xs font-semibold">{rating.toFixed(1)}</span>
              {indicator.reviewCount > 0 && (
                <span className="text-gray-600 text-xs">({formatNumber(indicator.reviewCount)})</span>
              )}
            </div>
            {/* Win Rate */}
            {winRate && (
              <div className="flex items-center gap-1">
                <span className="text-green-400 text-xs font-semibold">{winRate}%</span>
                <span className="text-gray-600 text-[10px]">WR</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Views */}
            <div className="flex items-center gap-1 text-gray-600">
              <EyeIcon className="w-3 h-3" />
              <span className="text-[10px]">{formatNumber(indicator.views || 0)}</span>
            </div>

            {/* Price */}
            <span
              className={clsx(
                'text-xs font-semibold',
                !indicator.price || indicator.pricingModel === 'free'
                  ? 'text-green-400'
                  : 'text-amber-400'
              )}
            >
              {formatPrice(indicator.price, indicator.pricingModel)}
            </span>
          </div>
        </div>

        {/* Compare button */}
        {showCompare && (
          <button
            onClick={handleCompare}
            className={clsx(
              'absolute top-3 right-3 w-6 h-6 rounded flex items-center justify-center transition-all',
              inCompare
                ? 'bg-amber-500/20 text-amber-400'
                : 'bg-transparent text-gray-700 hover:text-gray-400 opacity-0 group-hover:opacity-100'
            )}
            title={inCompare ? 'Remove from compare' : 'Add to compare'}
          >
            <ScaleIcon className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </Link>
  );
}
