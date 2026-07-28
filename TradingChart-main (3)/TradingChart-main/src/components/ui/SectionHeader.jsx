import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';

export default function SectionHeader({ title, subtitle, viewAllHref, className = '' }) {
  return (
    <div className={`flex items-end justify-between mb-6 ${className}`}>
      <div>
        <h2 className="text-xl sm:text-2xl font-semibold text-white">{title}</h2>
        {subtitle && <p className="text-sm text-gray-400 mt-1">{subtitle}</p>}
      </div>
      {viewAllHref && (
        <Link
          to={viewAllHref}
          className="flex items-center gap-1 text-sm font-medium text-amber-400 hover:text-amber-300 transition-colors whitespace-nowrap"
        >
          View All <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      )}
    </div>
  );
}
