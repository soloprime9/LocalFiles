'use client'
import React, { useEffect, useState } from 'react';
import IndicatorCard from '../components/common/IndicatorCard';
import { SectionHeader, SkeletonCard, EmptyState } from '../components/common/UI';
import { getTrending, getNewest, getTopRated, getFreeTools } from '../utils/api';
import { FireIcon, SparklesIcon, StarIcon, GiftIcon } from '@heroicons/react/24/outline';

function ListPage({ title, subtitle, icon: Icon, fetcher }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetcher()
      .then((r) => setItems(r?.data || r || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center">
          <Icon className="w-5 h-5 text-amber-400" />
        </div>
        <div>
          <h1 className="section-title">{title}</h1>
          <p className="section-subtitle">{subtitle}</p>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(12)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : items.length === 0 ? (
        <EmptyState title="Nothing here yet" icon={Icon} />
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

export function Trending() {
  return <ListPage title="🔥 Trending" subtitle="Most viewed in the last 7 days" icon={FireIcon} fetcher={getTrending} />;
}

export function NewArrivals() {
  return <ListPage title="✨ New Arrivals" subtitle="Recently added to the directory" icon={SparklesIcon} fetcher={getNewest} />;
}

export function TopRated() {
  return <ListPage title="🏆 Top Rated" subtitle="Highest community-rated tools" icon={StarIcon} fetcher={getTopRated} />;
}

export function FreeTools() {
  return <ListPage title="🎁 Free Tools" subtitle="Quality tools available at no cost" icon={GiftIcon} fetcher={getFreeTools} />;
}
