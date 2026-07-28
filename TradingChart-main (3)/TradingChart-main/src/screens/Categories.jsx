'use client'
import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useAppContext } from '../context/AppContext';
import IndicatorCard from '../components/common/IndicatorCard';
import { LoadingSpinner, SkeletonCard, EmptyState } from '../components/common/UI';
import { getCategory, getIndicators } from '../utils/api';
import { TagIcon, ChevronRightIcon } from '@heroicons/react/24/outline';

export function Categories() {
  const { state } = useAppContext();
  const { categories } = state;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="mb-8">
        <h1 className="section-title">Categories</h1>
        <p className="section-subtitle">Browse indicators by category</p>
      </div>

      {categories.length === 0 ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="card p-5 animate-pulse">
              <div className="h-5 bg-[#1F2937] rounded w-3/4 mb-2" />
              <div className="h-3 bg-[#1A1A1A] rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {categories.map((cat) => (
            <Link
              key={cat.slug}
              to={`/categories/${cat.slug}`}
              className="card card-hover p-5 flex items-center justify-between group"
            >
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xl">{cat.emoji || '📊'}</span>
                  <span className="text-white font-medium text-sm">{cat.name}</span>
                </div>
                {cat.count !== undefined && (
                  <p className="text-gray-600 text-xs">{cat.count} tools</p>
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

export function CategoryPage() {
  const { slug } = useParams();
  const [category, setCategory] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getCategory(slug).catch(() => null),
      getIndicators({ category: slug }).catch(() => null),
    ])
      .then(([catRes, indRes]) => {
        setCategory(catRes?.data || catRes);
        setItems(indRes?.data || indRes?.indicators || []);
      })
      .finally(() => setLoading(false));
  }, [slug]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="flex items-center gap-2 text-xs text-gray-600 mb-6">
        <Link to="/" className="hover:text-gray-400">Home</Link>
        <ChevronRightIcon className="w-3 h-3" />
        <Link to="/categories" className="hover:text-gray-400">Categories</Link>
        <ChevronRightIcon className="w-3 h-3" />
        <span className="text-gray-400 capitalize">{slug}</span>
      </div>

      <div className="mb-8">
        <h1 className="section-title capitalize">
          {category?.emoji || '📊'} {category?.name || slug}
        </h1>
        {category?.description && (
          <p className="section-subtitle">{category.description}</p>
        )}
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : items.length === 0 ? (
        <EmptyState title="No tools in this category yet" icon={TagIcon} />
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
