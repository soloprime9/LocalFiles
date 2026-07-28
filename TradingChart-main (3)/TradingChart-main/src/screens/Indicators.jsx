'use client'
import React, { useEffect, useCallback } from 'react';
import { useAppContext, jjj } from '../context/AppContext';
import IndicatorCard from '../components/common/IndicatorCard';
import FilterBar from '../components/common/FilterBar';
import { LoadingSpinner, SkeletonCard, EmptyState } from '../components/common/UI';
import { ChartBarIcon, ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline';
import { getIndicators } from '../utils/api';

export default function Indicators() {
  const { state, dispatch } = useApp();
  const { indicators, filters, totalResults, totalPages, loading } = state;

  const fetchIndicators = useCallback(async () => {
    dispatch({ type: ACTIONS.FETCH_START, payload: 'indicators' });
    try {
      const res = await getIndicators(filters);
      dispatch({ type: ACTIONS.FETCH_INDICATORS_SUCCESS, payload: res });
    } catch (err) {
      dispatch({ type: ACTIONS.FETCH_ERROR, payload: err.message });
    }
  }, [filters, dispatch]);

  useEffect(() => {
    fetchIndicators();
  }, [fetchIndicators]);

  const handlePage = (p) => {
    dispatch({ type: ACTIONS.SET_PAGE, payload: p });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="mb-8">
        <h1 className="section-title">Browse All Tools</h1>
        <p className="section-subtitle">
          {totalResults > 0 ? `${totalResults.toLocaleString()} listings found` : 'Discover trading indicators, EAs, bots & signals'}
        </p>
      </div>

      <FilterBar />

      {loading.indicators ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {[...Array(12)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : indicators.length === 0 ? (
        <EmptyState
          title="No results found"
          description="Try adjusting your filters or search terms."
          icon={ChartBarIcon}
        />
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {indicators.map((ind) => (
              <IndicatorCard key={ind._id} indicator={ind} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-10">
              <button
                onClick={() => handlePage(filters.page - 1)}
                disabled={filters.page <= 1}
                className="btn-secondary px-3 py-2 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <ChevronLeftIcon className="w-4 h-4" />
              </button>

              {[...Array(Math.min(totalPages, 7))].map((_, i) => {
                const page = i + 1;
                return (
                  <button
                    key={page}
                    onClick={() => handlePage(page)}
                    className={`w-9 h-9 rounded-md text-sm font-medium transition-colors ${
                      filters.page === page
                        ? 'bg-amber-500 text-black'
                        : 'btn-secondary'
                    }`}
                  >
                    {page}
                  </button>
                );
              })}

              <button
                onClick={() => handlePage(filters.page + 1)}
                disabled={filters.page >= totalPages}
                className="btn-secondary px-3 py-2 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <ChevronRightIcon className="w-4 h-4" />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
