import IndicatorCard from './IndicatorCard';
import SkeletonCard from '../ui/SkeletonCard';
import EmptyState from '../ui/EmptyState';
import { SearchX } from 'lucide-react';

export default function IndicatorGrid({ indicators = [], loading = false, emptyMessage = 'No results found. Try adjusting your filters.' }) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
        {Array.from({ length: 8 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (indicators.length === 0) {
    return <EmptyState icon={SearchX} title="No results" subtitle={emptyMessage} />;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
      {indicators.map((indicator) => (
        <IndicatorCard key={indicator._id} indicator={indicator} />
      ))}
    </div>
  );
}
