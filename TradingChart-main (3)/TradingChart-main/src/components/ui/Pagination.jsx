import { ChevronLeft, ChevronRight } from 'lucide-react';

function getPageList(current, total) {
  const pages = [];
  const window = 1;
  const start = Math.max(1, current - window);
  const end = Math.min(total, current + window);

  if (start > 1) pages.push(1);
  if (start > 2) pages.push('…');
  for (let p = start; p <= end; p++) pages.push(p);
  if (end < total - 1) pages.push('…');
  if (end < total) pages.push(total);

  return pages;
}

export default function Pagination({ currentPage = 1, totalPages = 1, onPageChange = () => {} }) {
  if (totalPages <= 1) return null;
  const pages = getPageList(currentPage, totalPages);

  return (
    <nav className="flex items-center justify-center gap-1.5" aria-label="Pagination">
      <button
        type="button"
        disabled={currentPage === 1}
        onClick={() => onPageChange(currentPage - 1)}
        className="p-2 rounded-lg border border-[#1F2937] text-gray-400 hover:text-white hover:border-[#374151] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        aria-label="Previous page"
      >
        <ChevronLeft className="w-4 h-4" />
      </button>

      {pages.map((p, idx) =>
        p === '…' ? (
          <span key={`ellipsis-${idx}`} className="px-2 text-gray-500 text-sm">
            …
          </span>
        ) : (
          <button
            key={p}
            type="button"
            onClick={() => onPageChange(p)}
            className={`min-w-[36px] h-9 rounded-lg text-sm font-medium transition-colors ${
              p === currentPage
                ? 'bg-amber-500 text-black'
                : 'border border-[#1F2937] text-gray-300 hover:text-white hover:border-[#374151]'
            }`}
          >
            {p}
          </button>
        )
      )}

      <button
        type="button"
        disabled={currentPage === totalPages}
        onClick={() => onPageChange(currentPage + 1)}
        className="p-2 rounded-lg border border-[#1F2937] text-gray-400 hover:text-white hover:border-[#374151] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        aria-label="Next page"
      >
        <ChevronRight className="w-4 h-4" />
      </button>
    </nav>
  );
}
