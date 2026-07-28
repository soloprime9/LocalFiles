'use client'
import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useAppContext } from '../context/AppContext';
import IndicatorCard from '../components/common/IndicatorCard';
import { SkeletonCard, EmptyState } from '../components/common/UI';
import { getByPlatform } from '../utils/api';
import { CpuChipIcon, ChevronRightIcon } from '@heroicons/react/24/outline';
import { getPlatformColor } from '../utils/helpers';
import clsx from 'clsx';

export function Platforms() {
  const { state } = useApp();
  const { platforms } = state;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="mb-8">
        <h1 className="section-title">Platforms</h1>
        <p className="section-subtitle">Browse tools by trading platform</p>
      </div>

      {platforms.length === 0 ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card p-5 animate-pulse h-24" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {platforms.map((p) => (
            <Link
              key={p.slug}
              to={`/platforms/${p.slug}`}
              className="card card-hover p-5 flex items-center justify-between group"
            >
              <div>
                <span
                  className={clsx(
                    'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border mb-2',
                    getPlatformColor(p.name)
                  )}
                >
                  {p.name}
                </span>
                {p.count !== undefined && (
                  <p className="text-gray-600 text-xs">{p.count} tools</p>
                )}
              </div>
              <ChevronRightIcon className="w-4 h-4 text-gray-700 group-hover:text-gray-400 transition-colors" />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function PlatformPage() {
  const { slug } = useParams();
  const { state } = useApp();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const platform = state.platforms.find((p) => p.slug === slug);

  useEffect(() => {
    getByPlatform(slug)
      .then((r) => setItems(r?.data || r || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [slug]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="flex items-center gap-2 text-xs text-gray-600 mb-6">
        <Link to="/" className="hover:text-gray-400">Home</Link>
        <ChevronRightIcon className="w-3 h-3" />
        <Link to="/platforms" className="hover:text-gray-400">Platforms</Link>
        <ChevronRightIcon className="w-3 h-3" />
        <span className="text-gray-400 capitalize">{slug}</span>
      </div>

      <div className="mb-8">
        <h1 className="section-title capitalize">
          {platform?.name || slug} Tools
        </h1>
        <p className="section-subtitle">
          {platform?.description || `Indicators and tools for ${platform?.name || slug}`}
        </p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : items.length === 0 ? (
        <EmptyState title="No tools for this platform yet" icon={CpuChipIcon} />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {items.map((ind) => (
            <IndicatorCard key={ind._id} indicator={ind} />
          ))}
        </div>
      )}
    </div>
  );
}
