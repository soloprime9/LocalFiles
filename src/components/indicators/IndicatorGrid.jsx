import React from 'react';
import { IndicatorCard } from './IndicatorCard';
import { Spinner } from '../ui/Spinner';
import { RefreshCw, PackageX } from 'lucide-react';

export const IndicatorGrid = ({ 
  indicators, 
  isLoading,
  onClearFilters 
}) => {
  if (isLoading) {
    return (
      <div className="py-20 flex flex-col items-center justify-center space-y-4">
        <Spinner size="lg" />
        <p className="text-sm font-mono text-slate-500 animate-pulse">
          Hydrating Falcon analytical matrices...
        </p>
      </div>
    );
  }

  if (indicators.length === 0) {
    return (
      <div className="py-24 text-center border border-white/5 rounded-2xl bg-[#09090f]/60 p-8 glass-panel max-w-xl mx-auto flex flex-col items-center">
        <PackageX className="h-12 w-12 text-slate-600 mb-4 animate-bounce" />
        <h3 className="text-base font-semibold text-white">No Trading Tools Found</h3>
        <p className="text-xs text-slate-400 mt-2 max-w-md leading-relaxed">
          We couldn&apos;t find any indicators, EAs, or strategies matching your selected criteria. Try adjusting your timeframe, platform scope, or keyword parameters.
        </p>
        {onClearFilters && (
          <button
            onClick={onClearFilters}
            className="mt-6 flex items-center space-x-1.5 bg-amber-500 hover:bg-amber-400 text-black font-semibold text-xs px-4 py-2 rounded-lg transition-all"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Reset All Search Filters</span>
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {indicators.map((indicator) => (
        <IndicatorCard key={indicator._id} indicator={indicator} />
      ))}
    </div>
  );
};
