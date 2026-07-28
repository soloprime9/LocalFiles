'use client'
import { useNavigate } from 'react-router-dom';
import { X, GitCompareArrows } from 'lucide-react';
import { useAppContext } from '../../context/AppContext';

export default function CompareDrawer() {
  const { compareList, removeFromCompare, clearCompare } = useAppContext();
  const navigate = useNavigate();

  if (compareList.length === 0) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 border-t-2 border-transparent bg-[#111111]"
      style={{ borderImage: 'linear-gradient(90deg, #F59E0B, #FBBF24, #F59E0B) 1' }}
    >
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-3 sm:gap-4">
        <div className="hidden sm:flex items-center gap-2 flex-1 min-w-0 overflow-x-auto">
          {compareList.map((item) => (
            <span
              key={item._id}
              className="flex items-center gap-1.5 bg-[#1A1A1A] border border-[#1F2937] rounded-lg px-3 py-1.5 text-sm text-white whitespace-nowrap"
            >
              {item.name}
              <button
                type="button"
                onClick={() => removeFromCompare(item._id)}
                aria-label={`Remove ${item.name} from compare`}
                className="text-gray-500 hover:text-red-400 transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </span>
          ))}
        </div>

        <div className="flex sm:hidden items-center gap-2 flex-1">
          <GitCompareArrows className="w-4 h-4 text-amber-500" />
          <span className="text-sm text-white font-medium">{compareList.length} selected</span>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={clearCompare}
            className="text-sm text-gray-400 hover:text-white transition-colors px-2"
          >
            Clear All
          </button>
          <button
            type="button"
            onClick={() => navigate('/compare')}
            className="flex items-center gap-1.5 bg-amber-500 text-black text-sm font-semibold px-4 py-2 rounded-lg hover:bg-amber-400 transition-colors whitespace-nowrap"
          >
            Compare Now <span aria-hidden>→</span>
          </button>
        </div>
      </div>
    </div>
  );
}
