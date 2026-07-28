import { ArrowUp, ArrowDown } from 'lucide-react';

export default function StatCard({ icon: Icon, label, value, change, className = '' }) {
  const isPositive = typeof change === 'number' && change >= 0;
  const hasChange = typeof change === 'number';

  return (
    <div className={`bg-[#111111] border border-[#1F2937] rounded-xl p-4 ${className}`}>
      <div className="flex items-center justify-between mb-2">
        {Icon && <Icon className="w-5 h-5 text-amber-500" />}
        {hasChange && (
          <span
            className={`flex items-center gap-0.5 text-xs font-medium ${
              isPositive ? 'text-emerald-400' : 'text-red-400'
            }`}
          >
            {isPositive ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
            {Math.abs(change)}%
          </span>
        )}
      </div>
      <p className="text-2xl font-semibold text-white leading-tight">{value}</p>
      <p className="text-xs text-gray-400 mt-1">{label}</p>
    </div>
  );
}
