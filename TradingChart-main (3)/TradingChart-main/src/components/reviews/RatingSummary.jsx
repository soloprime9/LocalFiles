import StarRating from '../ui/StarRating';

export default function RatingSummary({ ratingBreakdown = { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 }, avgRating = 0, total = 0 }) {
  const stars = [5, 4, 3, 2, 1];

  return (
    <div className="bg-[#111111] border border-[#1F2937] rounded-xl p-5">
      <div className="flex flex-col sm:flex-row gap-6">
        <div className="flex flex-col items-center justify-center sm:border-r sm:border-[#1F2937] sm:pr-6 shrink-0">
          <span className="text-4xl font-bold text-white">{avgRating.toFixed(1)}</span>
          <StarRating rating={avgRating} size="md" />
          <span className="text-xs text-gray-500 mt-1">{total} review{total !== 1 ? 's' : ''}</span>
        </div>

        <div className="flex-1 space-y-2">
          {stars.map((star) => {
            const count = ratingBreakdown[star] || 0;
            const pct = total > 0 ? Math.round((count / total) * 100) : 0;
            return (
              <div key={star} className="flex items-center gap-3">
                <span className="text-xs text-gray-400 w-10 shrink-0">{star} star</span>
                <div className="flex-1 h-2 bg-[#1F2937] rounded-full overflow-hidden">
                  <div
                    className="h-2 bg-amber-500 rounded-full transition-all duration-500"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="text-xs text-gray-500 w-10 text-right shrink-0">{pct}%</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
