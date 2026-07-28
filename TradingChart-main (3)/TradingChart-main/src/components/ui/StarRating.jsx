import { Star, StarHalf } from 'lucide-react';

const SIZES = {
  sm: 'w-3.5 h-3.5',
  md: 'w-5 h-5',
  lg: 'w-7 h-7',
};

export default function StarRating({
  rating = 0,
  size = 'md',
  showCount = false,
  count = 0,
  interactive = false,
  onChange = () => {},
}) {
  const sizeClass = SIZES[size] || SIZES.md;
  const stars = [1, 2, 3, 4, 5];

  return (
    <div className="flex items-center gap-1">
      <div className="flex items-center">
        {stars.map((n) => {
          const filled = rating >= n;
          const half = !filled && rating >= n - 0.5;
          return (
            <button
              key={n}
              type="button"
              disabled={!interactive}
              onClick={() => interactive && onChange(n)}
              className={interactive ? 'cursor-pointer' : 'cursor-default'}
              aria-label={`${n} star`}
            >
              {half ? (
                <StarHalf className={`${sizeClass} fill-amber-400 text-amber-400`} />
              ) : (
                <Star
                  className={`${sizeClass} ${
                    filled ? 'fill-amber-400 text-amber-400' : 'fill-transparent text-gray-600'
                  }`}
                />
              )}
            </button>
          );
        })}
      </div>
      {showCount && (
        <span className="text-xs text-gray-400 ml-1">
          {rating.toFixed(1)} {count > 0 && `(${count})`}
        </span>
      )}
    </div>
  );
}
