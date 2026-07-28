import React from 'react';

export function LoadingSpinner({ size = 'md', text = '' }) {
  const sizes = { sm: 'w-4 h-4', md: 'w-8 h-8', lg: 'w-12 h-12' };
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12">
      <div
        className={`${sizes[size]} border-2 border-[#1F2937] border-t-amber-400 rounded-full animate-spin`}
      />
      {text && <p className="text-gray-500 text-sm">{text}</p>}
    </div>
  );
}

export function EmptyState({ title = 'Nothing here yet', description = '', icon: Icon, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      {Icon && (
        <div className="w-16 h-16 rounded-full bg-[#1A1A1A] flex items-center justify-center mb-4">
          <Icon className="w-8 h-8 text-gray-600" />
        </div>
      )}
      <h3 className="text-white font-semibold text-lg mb-2">{title}</h3>
      {description && <p className="text-gray-500 text-sm max-w-sm mb-6">{description}</p>}
      {action}
    </div>
  );
}

export function SectionHeader({ title, subtitle, action, className = '' }) {
  return (
    <div className={`flex items-center justify-between mb-6 ${className}`}>
      <div>
        <h2 className="section-title">{title}</h2>
        {subtitle && <p className="section-subtitle">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="card p-4 animate-pulse">
      <div className="flex items-start gap-3 mb-3">
        <div className="w-8 h-8 bg-[#1F2937] rounded" />
        <div className="flex-1">
          <div className="h-4 bg-[#1F2937] rounded w-3/4 mb-1" />
          <div className="h-3 bg-[#1A1A1A] rounded w-1/2" />
        </div>
      </div>
      <div className="space-y-2 mb-3">
        <div className="h-3 bg-[#1A1A1A] rounded w-full" />
        <div className="h-3 bg-[#1A1A1A] rounded w-5/6" />
      </div>
      <div className="flex gap-2 mb-3">
        <div className="h-5 w-16 bg-[#1A1A1A] rounded" />
        <div className="h-5 w-16 bg-[#1A1A1A] rounded" />
      </div>
      <div className="flex justify-between pt-3 border-t border-[#1A1A1A]">
        <div className="h-4 w-16 bg-[#1A1A1A] rounded" />
        <div className="h-4 w-12 bg-[#1A1A1A] rounded" />
      </div>
    </div>
  );
}

export function StatBadge({ label, value, color = 'amber' }) {
  const colors = {
    amber: 'text-amber-400',
    green: 'text-green-400',
    blue: 'text-blue-400',
    red: 'text-red-400',
  };
  return (
    <div className="card px-4 py-3 text-center">
      <div className={`text-xl font-bold ${colors[color]}`}>{value}</div>
      <div className="text-gray-500 text-xs mt-0.5">{label}</div>
    </div>
  );
}
