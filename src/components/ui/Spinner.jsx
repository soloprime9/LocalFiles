import React from 'react';

export const Spinner = ({
  size = 'md',
  color = 'border-amber-500'
}) => {
  const sizeClasses = {
    sm: 'h-6 w-6 border-2',
    md: 'h-10 w-10 border-3',
    lg: 'h-16 w-16 border-4'
  };

  return (
    <div className="flex items-center justify-center p-4">
      <div className={`animate-spin rounded-full border-t-transparent ${color} ${sizeClasses[size]}`}></div>
    </div>
  );
};
