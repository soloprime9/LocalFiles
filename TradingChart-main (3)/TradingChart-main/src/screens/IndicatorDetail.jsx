'use client'
import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  StarIcon,
  EyeIcon,
  HeartIcon,
  FlagIcon,
  ScaleIcon,
  ArrowTopRightOnSquareIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';
import { StarIcon as StarSolid } from '@heroicons/react/24/solid';
import {
  getIndicator,
  getReviews,
  createReview,
  incrementView,
  toggleLike,
  flagScam,
  getSimilar,
} from '../utils/api';
import {
  formatPrice,
  formatNumber,
  timeAgo,
  getPlatformColor,
  getListingTypeIcon,
  getRatingColor,
  getTrustScoreColor,
} from '../utils/helpers';
import { LoadingSpinner, EmptyState } from '../components/common/UI';
import IndicatorCard from '../components/common/IndicatorCard';
import { useAppContext, value } from '../context/AppContext';
import toast from 'react-hot-toast';
import clsx from 'clsx';

function StarRating({ value, onChange }) {
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((s) => (
        <button key={s} onClick={() => onChange && onChange(s)} type="button">
          <StarSolid className={`w-5 h-5 ${s <= value ? 'text-amber-400' : 'text-gray-700'}`} />
        </button>
      ))}
    </div>
  );
}

export default function IndicatorDetail() {
  const { slug } = useParams();
  const { state, dispatch } = useApp();
  const [indicator, setIndicator] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [similar, setSimilar] = useState([]);
  const [loading, setLoading] = useState(true);
  const [reviewForm, setReviewForm] = useState({ rating: 5, title: '', body: '', author: '' });
  const [submitting, setSubmitting] = useState(false);

  const inCompare = state.compareList.some((i) => i._id === indicator?._id);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getIndicator(slug),
      getReviews(slug).catch(() => ({ data: [] })),
      getSimilar(slug).catch(() => ({ data: [] })),
    ])
      .then(([indRes, revRes, simRes]) => {
        const ind = indRes?.data || indRes;
        setIndicator(ind);
        setReviews(revRes?.data || revRes || []);
        setSimilar(simRes?.data || simRes || []);
        if (ind?._id) incrementView(ind._id).catch(() => {});
      })
      .catch(() => toast.error('Indicator not found'))
      .finally(() => setLoading(false));
  }, [slug]);

  const handleLike = async () => {
    if (!indicator) return;
    await toggleLike(indicator._id).catch(() => {});
  };

  const handleFlag = async () => {
    const reason = window.prompt('Reason for flagging as scam?');
    if (!reason) return;
    await flagScam(indicator._id, reason);
    toast.success('Flagged for review. Thank you.');
  };

  const handleCompare = () => {
    if (!indicator) return;
    if (inCompare) {
      dispatch({ type: ACTIONS.REMOVE_FROM_COMPARE, payload: indicator._id });
    } else {
      dispatch({ type: ACTIONS.ADD_TO_COMPARE, payload: indicator });
    }
  };

  const handleReviewSubmit = async (e) => {
    e.preventDefault();
    if (!reviewForm.body || !reviewForm.author) {
      toast.error('Please fill in all fields');
      return;
    }
    setSubmitting(true);
    try {
      await createReview({ ...reviewForm, indicator: indicator._id });
      toast.success('Review submitted!');
      setReviewForm({ rating: 5, title: '', body: '', author: '' });
      const revRes = await getReviews(slug);
      setReviews(revRes?.data || revRes || []);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <LoadingSpinner text="Loading indicator..." />;
  if (!indicator) return (
    <EmptyState title="Indicator not found" description="It may have been removed or the URL is incorrect." />
  );

  const rating = indicator.averageRating || indicator.rating || 0;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-gray-600 mb-6">
        <Link to="/" className="hover:text-gray-400">Home</Link>
        <ChevronRightIcon className="w-3 h-3" />
        <Link to="/indicators" className="hover:text-gray-400">Indicators</Link>
        <ChevronRightIcon className="w-3 h-3" />
        <span className="text-gray-400">{indicator.name}</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Header */}
          <div className="card p-6">
            <div className="flex items-start gap-4">
              <span className="text-4xl">{getListingTypeIcon(indicator.listingType)}</span>
              <div className="flex-1">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h1 className="text-2xl font-bold text-white">{indicator.name}</h1>
                    {indicator.author && (
                      <p className="text-gray-500 text-sm mt-1">by {indicator.author}</p>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2 justify-end">
                    {indicator.isVerified && (
                      <span className="badge-verified">✓ Verified</span>
                    )}
                    {indicator.isScam && (
                      <span className="badge-scam">⚠ Scam Alert</span>
                    )}
                    {indicator.isFeatured && (
                      <span className="badge-paid">⭐ Featured</span>
                    )}
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-4 mt-3">
                  <div className="flex items-center gap-1.5">
                    <StarRating value={Math.round(rating)} />
                    <span className={`font-bold ${getRatingColor(rating)}`}>{rating.toFixed(1)}</span>
                    <span className="text-gray-600 text-sm">({formatNumber(indicator.reviewCount || reviews.length)})</span>
                  </div>
                  <div className="flex items-center gap-1 text-gray-500 text-sm">
                    <EyeIcon className="w-4 h-4" />
                    {formatNumber(indicator.views || 0)} views
                  </div>
                  <div className="flex items-center gap-1 text-gray-500 text-sm">
                    <HeartIcon className="w-4 h-4" />
                    {formatNumber(indicator.likes || 0)}
                  </div>
                </div>

                {/* Platforms */}
                {indicator.platforms?.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-3">
                    {indicator.platforms.map((p) => (
                      <span
                        key={p}
                        className={clsx(
                          'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border',
                          getPlatformColor(p)
                        )}
                      >
                        {p}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex flex-wrap gap-3 mt-5 pt-5 border-t border-[#1F2937]">
              {indicator.externalUrl && (
                <a
                  href={indicator.externalUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-primary"
                >
                  <ArrowTopRightOnSquareIcon className="w-4 h-4" />
                  Get This Tool
                </a>
              )}
              <button onClick={handleLike} className="btn-secondary">
                <HeartIcon className="w-4 h-4" /> Like
              </button>
              <button
                onClick={handleCompare}
                className={clsx('btn-secondary', inCompare && 'border-amber-500 text-amber-400')}
              >
                <ScaleIcon className="w-4 h-4" />
                {inCompare ? 'In Compare' : 'Compare'}
              </button>
              <button onClick={handleFlag} className="btn-secondary text-red-400 border-red-900/50 hover:border-red-700">
                <FlagIcon className="w-4 h-4" /> Flag
              </button>
            </div>
          </div>

          {/* Description */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-white mb-3">About</h2>
            <p className="text-gray-400 text-sm leading-relaxed whitespace-pre-wrap">
              {indicator.description || indicator.shortDescription || 'No description provided.'}
            </p>
          </div>

          {/* Performance */}
          {(indicator.winRate || indicator.performance) && (
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-white mb-4">Performance</h2>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {indicator.winRate && (
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-400">{indicator.winRate}%</div>
                    <div className="text-gray-500 text-xs mt-1">Win Rate</div>
                  </div>
                )}
                {indicator.performance?.profitFactor && (
                  <div className="text-center">
                    <div className="text-2xl font-bold text-amber-400">{indicator.performance.profitFactor}</div>
                    <div className="text-gray-500 text-xs mt-1">Profit Factor</div>
                  </div>
                )}
                {indicator.performance?.maxDrawdown && (
                  <div className="text-center">
                    <div className="text-2xl font-bold text-red-400">{indicator.performance.maxDrawdown}%</div>
                    <div className="text-gray-500 text-xs mt-1">Max Drawdown</div>
                  </div>
                )}
                {indicator.performance?.sharpeRatio && (
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-400">{indicator.performance.sharpeRatio}</div>
                    <div className="text-gray-500 text-xs mt-1">Sharpe Ratio</div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Reviews */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-white mb-5">
              Reviews ({reviews.length})
            </h2>

            {reviews.length === 0 ? (
              <p className="text-gray-600 text-sm">No reviews yet. Be the first!</p>
            ) : (
              <div className="space-y-4 mb-8">
                {reviews.map((rev) => (
                  <div key={rev._id} className="border-b border-[#1F2937] pb-4">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-white text-sm font-medium">{rev.author || rev.userName || 'Anonymous'}</span>
                          <StarRating value={rev.rating} />
                        </div>
                        {rev.title && <p className="text-gray-300 text-sm font-medium mt-1">{rev.title}</p>}
                      </div>
                      <span className="text-gray-600 text-xs">{timeAgo(rev.createdAt)}</span>
                    </div>
                    <p className="text-gray-400 text-sm">{rev.body || rev.comment}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Write Review */}
            <div className="border-t border-[#1F2937] pt-6">
              <h3 className="text-white font-semibold mb-4">Write a Review</h3>
              <form onSubmit={handleReviewSubmit} className="space-y-3">
                <StarRating
                  value={reviewForm.rating}
                  onChange={(v) => setReviewForm((f) => ({ ...f, rating: v }))}
                />
                <input
                  type="text"
                  placeholder="Your name"
                  value={reviewForm.author}
                  onChange={(e) => setReviewForm((f) => ({ ...f, author: e.target.value }))}
                  className="input-field"
                />
                <input
                  type="text"
                  placeholder="Review title (optional)"
                  value={reviewForm.title}
                  onChange={(e) => setReviewForm((f) => ({ ...f, title: e.target.value }))}
                  className="input-field"
                />
                <textarea
                  rows={3}
                  placeholder="Share your experience..."
                  value={reviewForm.body}
                  onChange={(e) => setReviewForm((f) => ({ ...f, body: e.target.value }))}
                  className="input-field resize-none"
                />
                <button type="submit" disabled={submitting} className="btn-primary">
                  {submitting ? 'Submitting...' : 'Submit Review'}
                </button>
              </form>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-5">
          {/* Pricing */}
          <div className="card p-5">
            <div className="text-center mb-4">
              <div
                className={clsx(
                  'text-3xl font-extrabold',
                  !indicator.price || indicator.pricingModel === 'free'
                    ? 'text-green-400'
                    : 'text-amber-400'
                )}
              >
                {formatPrice(indicator.price, indicator.pricingModel)}
              </div>
              {indicator.pricingModel && (
                <p className="text-gray-600 text-xs mt-1 capitalize">{indicator.pricingModel}</p>
              )}
            </div>
            {indicator.externalUrl && (
              <a
                href={indicator.externalUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-primary w-full justify-center"
              >
                <ArrowTopRightOnSquareIcon className="w-4 h-4" />
                Get This Tool
              </a>
            )}
          </div>

          {/* Details */}
          <div className="card p-5">
            <h3 className="text-white font-semibold mb-3">Details</h3>
            <dl className="space-y-2.5">
              {[
                { label: 'Type', value: indicator.listingType },
                { label: 'Category', value: indicator.category?.name || indicator.category },
                { label: 'Timeframes', value: indicator.timeframes?.join(', ') },
                { label: 'Assets', value: indicator.assetClasses?.join(', ') },
                { label: 'Strategy', value: indicator.strategyTypes?.join(', ') },
                { label: 'Difficulty', value: indicator.difficulty },
                { label: 'Added', value: timeAgo(indicator.createdAt) },
              ]
                .filter((d) => d.value)
                .map((d) => (
                  <div key={d.label} className="flex items-start justify-between gap-2 text-sm">
                    <dt className="text-gray-600 flex-shrink-0">{d.label}</dt>
                    <dd className="text-gray-300 text-right capitalize">{d.value}</dd>
                  </div>
                ))}
            </dl>
          </div>

          {/* Trust Score */}
          {indicator.trustScore !== undefined && (
            <div className="card p-5">
              <h3 className="text-white font-semibold mb-3">Trust Score</h3>
              <div className="flex items-center gap-3">
                <div className="flex-1 bg-[#1A1A1A] rounded-full h-2">
                  <div
                    className={clsx(
                      'h-2 rounded-full transition-all',
                      indicator.trustScore >= 80
                        ? 'bg-green-500'
                        : indicator.trustScore >= 60
                        ? 'bg-amber-500'
                        : 'bg-red-500'
                    )}
                    style={{ width: `${indicator.trustScore}%` }}
                  />
                </div>
                <span className={clsx('font-bold text-sm', getTrustScoreColor(indicator.trustScore))}>
                  {indicator.trustScore}/100
                </span>
              </div>
            </div>
          )}

          {/* Similar */}
          {similar.length > 0 && (
            <div>
              <h3 className="text-white font-semibold mb-3">Similar Tools</h3>
              <div className="space-y-3">
                {similar.slice(0, 4).map((ind) => (
                  <IndicatorCard key={ind._id} indicator={ind} showCompare={false} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
