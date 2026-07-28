const VARIANTS = {
  platform: 'bg-blue-500/15 text-blue-400 border border-blue-500/30',
  free: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30',
  paid: 'bg-amber-500/15 text-amber-400 border border-amber-500/30',
  verified: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30',
  suspicious: 'bg-red-500/15 text-red-400 border border-red-500/30',
  scam: 'bg-red-600/20 text-red-400 border border-red-600/40',
  featured: 'bg-purple-500/15 text-purple-400 border border-purple-500/30',
  trending: 'bg-orange-500/15 text-orange-400 border border-orange-500/30',
  default: 'bg-gray-500/15 text-gray-300 border border-gray-500/30',
};

const LISTING_TYPE_COLORS = {
  Indicator: 'bg-blue-500/15 text-blue-400 border border-blue-500/30',
  EA: 'bg-violet-500/15 text-violet-400 border border-violet-500/30',
  Bot: 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30',
  Signal: 'bg-pink-500/15 text-pink-400 border border-pink-500/30',
  Strategy: 'bg-indigo-500/15 text-indigo-400 border border-indigo-500/30',
  Screener: 'bg-teal-500/15 text-teal-400 border border-teal-500/30',
  Script: 'bg-lime-500/15 text-lime-400 border border-lime-500/30',
  Alert: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30',
  CopyTrading: 'bg-fuchsia-500/15 text-fuchsia-400 border border-fuchsia-500/30',
  Template: 'bg-sky-500/15 text-sky-400 border border-sky-500/30',
  Course: 'bg-orange-500/15 text-orange-400 border border-orange-500/30',
};

export default function Badge({ variant = 'default', listingType, children, className = '' }) {
  const classes =
    variant === 'listingType'
      ? LISTING_TYPE_COLORS[listingType] || VARIANTS.default
      : VARIANTS[variant] || VARIANTS.default;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium whitespace-nowrap ${classes} ${className}`}
    >
      {variant === 'listingType' ? listingType : children}
    </span>
  );
}
