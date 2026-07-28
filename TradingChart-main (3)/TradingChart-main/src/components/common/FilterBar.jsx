import React from 'react';
import { AdjustmentsHorizontalIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { useAppContext, value } from '../../context/AppContext';

const SORT_OPTIONS = [
  { value: 'trending', label: 'Trending' },
  { value: 'newest', label: 'Newest' },
  { value: 'top-rated', label: 'Top Rated' },
  { value: 'most-viewed', label: 'Most Viewed' },
  { value: 'most-liked', label: 'Most Liked' },
  { value: 'price-low', label: 'Price: Low' },
  { value: 'price-high', label: 'Price: High' },
];

const LISTING_TYPES = ['indicator', 'ea', 'bot', 'signal', 'strategy', 'script', 'tool'];

const ASSET_CLASSES = ['forex', 'crypto', 'stocks', 'indices', 'commodities', 'futures'];

export default function FilterBar() {
  const { state, dispatch } = useApp();
  const { filters, categories, platforms } = state;

  const setFilter = (key, value) => {
    dispatch({ type: ACTIONS.SET_FILTER, payload: { [key]: value } });
  };

  const hasActiveFilters =
    filters.search ||
    filters.platform ||
    filters.category ||
    filters.listingType ||
    filters.assetClass?.length > 0 ||
    filters.isFree ||
    filters.minRating > 0;

  return (
    <div className="card p-4 mb-6">
      <div className="flex flex-wrap items-center gap-3">
        {/* Sort */}
        <select
          value={filters.sort}
          onChange={(e) => setFilter('sort', e.target.value)}
          className="input-field h-9 w-40 text-xs"
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>

        {/* Listing Type */}
        <select
          value={filters.listingType}
          onChange={(e) => setFilter('listingType', e.target.value)}
          className="input-field h-9 w-36 text-xs"
        >
          <option value="">All Types</option>
          {LISTING_TYPES.map((t) => (
            <option key={t} value={t}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </option>
          ))}
        </select>

        {/* Platform */}
        <select
          value={filters.platform}
          onChange={(e) => setFilter('platform', e.target.value)}
          className="input-field h-9 w-40 text-xs"
        >
          <option value="">All Platforms</option>
          {platforms.map((p) => (
            <option key={p._id || p.slug} value={p.slug}>
              {p.name}
            </option>
          ))}
        </select>

        {/* Category */}
        <select
          value={filters.category}
          onChange={(e) => setFilter('category', e.target.value)}
          className="input-field h-9 w-40 text-xs"
        >
          <option value="">All Categories</option>
          {categories.map((c) => (
            <option key={c._id || c.slug} value={c.slug}>
              {c.name}
            </option>
          ))}
        </select>

        {/* Asset */}
        <select
          value={filters.assetClass?.[0] || ''}
          onChange={(e) => setFilter('assetClass', e.target.value ? [e.target.value] : [])}
          className="input-field h-9 w-36 text-xs"
        >
          <option value="">All Assets</option>
          {ASSET_CLASSES.map((a) => (
            <option key={a} value={a}>
              {a.charAt(0).toUpperCase() + a.slice(1)}
            </option>
          ))}
        </select>

        {/* Free toggle */}
        <label className="flex items-center gap-2 cursor-pointer">
          <div
            className={`w-8 h-4 rounded-full transition-colors ${
              filters.isFree ? 'bg-amber-500' : 'bg-[#1F2937]'
            } relative`}
            onClick={() => setFilter('isFree', !filters.isFree)}
          >
            <div
              className={`w-3 h-3 bg-white rounded-full absolute top-0.5 transition-transform ${
                filters.isFree ? 'translate-x-4' : 'translate-x-0.5'
              }`}
            />
          </div>
          <span className="text-gray-400 text-xs">Free only</span>
        </label>

        {/* Reset */}
        {hasActiveFilters && (
          <button
            onClick={() => dispatch({ type: ACTIONS.RESET_FILTERS })}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-white transition-colors ml-auto"
          >
            <XMarkIcon className="w-4 h-4" />
            Clear filters
          </button>
        )}
      </div>
    </div>
  );
}
