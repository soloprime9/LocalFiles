import { Inbox } from 'lucide-react';

export default function EmptyState({
  icon: Icon = Inbox,
  title = 'Nothing here yet',
  subtitle = '',
  ctaLabel,
  onCtaClick,
  className = '',
}) {
  return (
    <div className={`flex flex-col items-center justify-center text-center py-16 px-4 ${className}`}>
      <div className="w-14 h-14 rounded-full bg-[#111111] border border-[#1F2937] flex items-center justify-center mb-4">
        <Icon className="w-6 h-6 text-gray-500" />
      </div>
      <h3 className="text-white font-semibold text-lg">{title}</h3>
      {subtitle && <p className="text-gray-400 text-sm mt-1.5 max-w-sm">{subtitle}</p>}
      {ctaLabel && (
        <button
          type="button"
          onClick={onCtaClick}
          className="mt-5 px-4 py-2 rounded-lg bg-amber-500 text-black text-sm font-medium hover:bg-amber-400 transition-colors"
        >
          {ctaLabel}
        </button>
      )}
    </div>
  );
}
