import { Link } from 'react-router-dom';
import { Flame, CheckCircle2, AlertTriangle, Flag } from 'lucide-react';
import Badge from '../ui/Badge';
import StarRating from '../ui/StarRating';
import TrustScore from './TrustScore';
import { useAppContext } from '../../context/AppContext';
import { formatPrice } from '../../utils/helpers';

const ASSET_CLASS_COLORS = {
  Crypto: 'bg-orange-500/15 text-orange-400',
  Forex: 'bg-blue-500/15 text-blue-400',
  Stocks: 'bg-emerald-500/15 text-emerald-400',
  Indices: 'bg-violet-500/15 text-violet-400',
  Gold: 'bg-yellow-500/15 text-yellow-400',
  Silver: 'bg-gray-400/15 text-gray-300',
  Oil: 'bg-stone-500/15 text-stone-300',
  Commodities: 'bg-amber-600/15 text-amber-400',
  Futures: 'bg-pink-500/15 text-pink-400',
  Options: 'bg-cyan-500/15 text-cyan-400',
  ETFs: 'bg-teal-500/15 text-teal-400',
};

export default function IndicatorCard({ indicator, showCompare = true }) {
  const { addToCompare, isInCompare } = useAppContext();
  const inCompare = isInCompare(indicator._id);

  const {
    name,
    slug,
    author,
    listingType,
    platform,
    assetClass = [],
    strategyType = [],
    description,
    trustScore = 0,
    backtestData,
    rating = 0,
    totalReviews = 0,
    price = 0,
    pricingModel,
    imageUrl,
    trendingScore = 0,
    isVerified,
    isScamFlagged,
    affiliateUrl,
  } = indicator;

  const visibleAssets = assetClass.slice(0, 3);
  const extraAssets = assetClass.length - visibleAssets.length;
  const isFreeLabel = price === 0 || pricingModel === 'Free';

  return (
    <div className="bg-[#111111] border border-[#1F2937] rounded-xl hover:border-[#374151] hover:bg-[#141414] transition-all cursor-pointer overflow-hidden flex flex-col">
      <div className="relative h-40 w-full overflow-hidden">
        {imageUrl ? (
          <img src={imageUrl} alt={name} className="w-full h-full object-cover" loading="lazy" />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-[#1F2937] to-[#0A0A0A]">
            <span className="text-gray-400 font-semibold text-lg px-4 text-center">{name}</span>
          </div>
        )}

        <div className="absolute top-2 left-2 flex flex-col gap-1.5 items-start">
          <Badge variant="listingType" listingType={listingType} />
          {platform?.name && <Badge variant="platform">{platform.name}</Badge>}
        </div>

        <div className="absolute top-2 right-2 flex flex-col gap-1.5 items-end">
          {trendingScore > 80 && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium bg-orange-500/90 text-white">
              <Flame className="w-3 h-3" /> Trending
            </span>
          )}
          {isVerified && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium bg-emerald-500/90 text-white">
              <CheckCircle2 className="w-3 h-3" /> Verified
            </span>
          )}
          {backtestData?.auditStatus === 'Suspicious' && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium bg-red-600 text-white">
              <AlertTriangle className="w-3 h-3" /> SUSPICIOUS
            </span>
          )}
          {isScamFlagged && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium bg-red-600 text-white">
              <Flag className="w-3 h-3" /> FLAGGED
            </span>
          )}
        </div>
      </div>

      <div className="p-4 flex flex-col gap-2 flex-1">
        <div>
          <Link
            to={`/indicators/${slug}`}
            className="text-white font-semibold leading-snug line-clamp-2 hover:text-amber-400 transition-colors"
          >
            {name}
          </Link>
          {author && <p className="text-xs text-gray-500 mt-0.5">by {author}</p>}
        </div>

        {visibleAssets.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {visibleAssets.map((a) => (
              <span
                key={a}
                className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  ASSET_CLASS_COLORS[a] || 'bg-gray-500/15 text-gray-300'
                }`}
              >
                {a}
              </span>
            ))}
            {extraAssets > 0 && (
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-500/15 text-gray-400">
                +{extraAssets} more
              </span>
            )}
          </div>
        )}

        {strategyType.length > 0 && (
          <div className="flex flex-wrap gap-x-1.5 text-xs text-gray-500">
            {strategyType.slice(0, 3).map((s, i) => (
              <span key={s}>
                {s}
                {i < Math.min(strategyType.length, 3) - 1 && ' ·'}
              </span>
            ))}
          </div>
        )}

        {description && <p className="text-sm text-gray-400 line-clamp-2">{description}</p>}

        {trustScore > 0 && <TrustScore score={trustScore} size="sm" />}

        {backtestData && (
          <div className="flex items-center gap-3 text-xs pt-1">
            {typeof backtestData.winRate === 'number' && (
              <span className={backtestData.winRate > 60 ? 'text-emerald-400' : 'text-gray-400'}>
                Win {backtestData.winRate}%
              </span>
            )}
            {typeof backtestData.sharpeRatio === 'number' && (
              <span className={backtestData.sharpeRatio > 1 ? 'text-emerald-400' : 'text-gray-400'}>
                Sharpe {backtestData.sharpeRatio}
              </span>
            )}
            {typeof backtestData.maxDrawdown === 'number' && (
              <span className="text-red-400">DD {backtestData.maxDrawdown}%</span>
            )}
          </div>
        )}

        <StarRating rating={rating} size="sm" showCount count={totalReviews} />

        <div className="mt-auto pt-3 border-t border-[#1F2937] flex flex-col gap-2.5">
          <div className="flex items-center justify-between">
            <span className={`font-semibold ${isFreeLabel ? 'text-emerald-400' : 'text-amber-400'}`}>
              {formatPrice(price, pricingModel)}
            </span>
            {pricingModel && <span className="text-xs text-gray-500">{pricingModel}</span>}
          </div>

          <div className="flex gap-2">
            <Link
              to={`/indicators/${slug}`}
              className="flex-1 text-center text-sm font-medium border border-[#1F2937] text-gray-200 hover:text-white hover:border-[#374151] rounded-lg py-2 transition-colors"
            >
              View Details
            </Link>
            <a
              href={affiliateUrl || '#'}
              target="_blank"
              rel="noopener noreferrer sponsored"
              className="flex-1 text-center text-sm font-semibold bg-amber-500 text-black hover:bg-amber-400 rounded-lg py-2 transition-colors"
            >
              Get It →
            </a>
          </div>

          {showCompare && (
            <button
              type="button"
              onClick={() => addToCompare(indicator)}
              disabled={inCompare}
              className={`text-xs font-medium rounded-lg py-1.5 transition-colors ${
                inCompare
                  ? 'text-emerald-400 cursor-default'
                  : 'text-amber-400 hover:text-amber-300'
              }`}
            >
              {inCompare ? '✓ Added' : '+ Compare'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
