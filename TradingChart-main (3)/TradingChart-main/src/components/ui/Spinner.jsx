const SIZES = {
  sm: 'w-4 h-4 border-2',
  md: 'w-8 h-8 border-2',
  lg: 'w-12 h-12 border-[3px]',
};

export default function Spinner({ size = 'md', className = '' }) {
  const sizeClass = SIZES[size] || SIZES.md;
  return (
    <div
      role="status"
      aria-label="Loading"
      className={`${sizeClass} rounded-full border-amber-500 border-t-transparent animate-spin ${className}`}
    />
  );
}
