import React from 'react';
import { Star, StarHalf } from 'lucide-react';

export const StarRating = ({
  rating,
  maxStars = 5,
  size = 14,
  interactive = false,
  onRatingChange,
  showText = false
}) => {
  const [hoverRating, setHoverRating] = React.useState(null);

  const activeRating = hoverRating !== null ? hoverRating : rating;

  const handleStarClick = (idx) => {
    if (interactive && onRatingChange) {
      onRatingChange(idx);
    }
  };

  const renderStars = () => {
    const stars = [];
    for (let i = 1; i <= maxStars; i++) {
      const isFilled = i <= activeRating;
      const isHalf = !isFilled && (i - 0.5) <= activeRating;

      stars.push(
        <span
          key={i}
          className={`${interactive ? 'cursor-pointer hover:scale-110 transition-transform' : ''}`}
          onClick={() => handleStarClick(i)}
          onMouseEnter={() => interactive && setHoverRating(i)}
          onMouseLeave={() => interactive && setHoverRating(null)}
        >
          {isFilled ? (
            <Star 
              size={size} 
              className="text-amber-500 fill-amber-500 stroke-amber-500" 
            />
          ) : isHalf ? (
            <StarHalf 
              size={size} 
              className="text-amber-500 fill-amber-500 stroke-amber-500" 
            />
          ) : (
            <Star 
              size={size} 
              className="text-slate-600 hover:text-amber-500/50 stroke-slate-500" 
            />
          )}
        </span>
      );
    }
    return stars;
  };

  return (
    <div className="flex items-center space-x-1 font-mono text-xs">
      <div className="flex items-center space-x-0.5">{renderStars()}</div>
      {showText && (
        <span className="text-slate-400 font-medium ml-1">
          {rating.toFixed(1)} / {maxStars}
        </span>
      )}
    </div>
  );
};
