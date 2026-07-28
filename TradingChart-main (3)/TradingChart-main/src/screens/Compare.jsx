'use client'
import React from 'react';
import { Link } from 'react-router-dom';
import { useAppContext, value } from '../context/AppContext';
import { XMarkIcon, StarIcon as StarSolid } from '@heroicons/react/24/solid';
import { ScaleIcon, ArrowTopRightOnSquareIcon } from '@heroicons/react/24/outline';
import { formatPrice, formatNumber, getRatingColor, getTrustScoreColor, getPlatformColor } from '../utils/helpers';
import clsx from 'clsx';

const COMPARE_FIELDS = [
  { label: 'Type', key: 'listingType' },
  { label: 'Price', render: (i) => formatPrice(i.price, i.pricingModel) },
  { label: 'Rating', render: (i) => i.averageRating?.toFixed(1) || i.rating?.toFixed(1) || 'N/A' },
  { label: 'Win Rate', render: (i) => i.winRate ? `${i.winRate}%` : 'N/A' },
  { label: 'Reviews', render: (i) => formatNumber(i.reviewCount || 0) },
  { label: 'Views', render: (i) => formatNumber(i.views || 0) },
  { label: 'Trust Score', render: (i) => i.trustScore !== undefined ? `${i.trustScore}/100` : 'N/A' },
  { label: 'Platforms', render: (i) => i.platforms?.join(', ') || 'N/A' },
  { label: 'Assets', render: (i) => i.assetClasses?.join(', ') || 'N/A' },
  { label: 'Timeframes', render: (i) => i.timeframes?.join(', ') || 'N/A' },
  { label: 'Difficulty', key: 'difficulty' },
  { label: 'Verified', render: (i) => i.isVerified ? '✅ Yes' : '❌ No' },
];

export default function Compare() {
  const { state, dispatch } = useApp();
  const { compareList } = state;

  const remove = (id) => dispatch({ type: ACTIONS.REMOVE_FROM_COMPARE, payload: id });
  const clear = () => dispatch({ type: ACTIONS.CLEAR_COMPARE });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="section-title">Compare Tools</h1>
          <p className="section-subtitle">Side-by-side comparison (up to 3 tools)</p>
        </div>
        {compareList.length > 0 && (
          <button onClick={clear} className="btn-secondary text-xs">
            Clear all
          </button>
        )}
      </div>

      {compareList.length === 0 ? (
        <div className="text-center py-24">
          <ScaleIcon className="w-16 h-16 text-gray-700 mx-auto mb-4" />
          <h3 className="text-white font-semibold text-lg mb-2">No tools to compare</h3>
          <p className="text-gray-500 text-sm mb-6">
            Add tools to compare from the browse page by clicking the compare icon on any card.
          </p>
          <Link to="/indicators" className="btn-primary">Browse Tools</Link>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <th className="w-40 text-left p-3 text-gray-600 text-xs font-medium border-b border-[#1F2937]">
                  Field
                </th>
                {compareList.map((ind) => (
                  <th key={ind._id} className="p-3 border-b border-[#1F2937] min-w-48">
                    <div className="card p-3 relative">
                      <button
                        onClick={() => remove(ind._id)}
                        className="absolute top-2 right-2 text-gray-600 hover:text-red-400"
                      >
                        <XMarkIcon className="w-4 h-4" />
                      </button>
                      <Link
                        to={`/indicators/${ind.slug}`}
                        className="text-white font-medium text-sm hover:text-amber-400 transition-colors block pr-5"
                      >
                        {ind.name}
                      </Link>
                      <div className="flex items-center gap-1 mt-1">
                        <StarSolid className="w-3.5 h-3.5 text-amber-400" />
                        <span className={`text-xs font-semibold ${getRatingColor(ind.averageRating || ind.rating || 0)}`}>
                          {(ind.averageRating || ind.rating || 0).toFixed(1)}
                        </span>
                      </div>
                      {ind.externalUrl && (
                        <a
                          href={ind.externalUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-2 text-amber-400 text-xs flex items-center gap-1 hover:underline"
                        >
                          View <ArrowTopRightOnSquareIcon className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  </th>
                ))}
                {/* Placeholder slots */}
                {[...Array(3 - compareList.length)].map((_, i) => (
                  <th key={`empty-${i}`} className="p-3 border-b border-[#1F2937] min-w-48">
                    <Link
                      to="/indicators"
                      className="card p-3 flex flex-col items-center justify-center h-24 text-gray-700 hover:text-gray-500 hover:border-[#374151] transition-all"
                    >
                      <span className="text-2xl mb-1">+</span>
                      <span className="text-xs">Add tool</span>
                    </Link>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {COMPARE_FIELDS.map(({ label, key, render }) => (
                <tr key={label} className="border-b border-[#111111] hover:bg-[#0F0F0F]">
                  <td className="p-3 text-gray-500 text-xs font-medium">{label}</td>
                  {compareList.map((ind) => {
                    const val = render ? render(ind) : ind[key];
                    return (
                      <td key={ind._id} className="p-3 text-center text-sm text-gray-300">
                        {val || <span className="text-gray-700">—</span>}
                      </td>
                    );
                  })}
                  {[...Array(3 - compareList.length)].map((_, i) => (
                    <td key={i} className="p-3" />
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
