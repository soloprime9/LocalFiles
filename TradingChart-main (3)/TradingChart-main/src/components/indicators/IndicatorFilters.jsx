'use client'
import { useState } from 'react';
import { ChevronDown, SlidersHorizontal, X } from 'lucide-react';
import SearchBar from '../ui/SearchBar';
import StarRating from '../ui/StarRating';
import { useAppContext } from '../../context/AppContext';

const LISTING_TYPES = ['All', 'Indicator', 'EA', 'Bot', 'Signal', 'Strategy', 'Screener', 'Script', 'CopyTrading', 'Course'];
const PLATFORMS = ['TradingView', 'MT4', 'MT5', 'cTrader', 'NinjaTrader', 'ThinkorSwim', '3Commas', 'Pionex', 'Cryptohopper'];
const ASSET_CLASSES = ['Crypto', 'Forex', 'Stocks', 'Indices', 'Gold', 'Silver', 'Oil', 'Futures', 'Options', 'ETFs'];
const STRATEGY_TYPES = ['Trend', 'Momentum', 'Scalping', 'Swing', 'Breakout', 'Smart Money', 'Price Action', 'Grid', 'DCA', 'Reversal', 'Volatility', 'Volume'];
const TIMEFRAMES = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1'];
const DIFFICULTIES = ['Beginner', 'Intermediate', 'Advanced', 'Expert'];
const SORT_OPTIONS = ['Trending', 'Newest', 'Top Rated', 'Most Reviewed', 'Price Low→High', 'Price High→Low', 'Trust Score'];
const STRATEGY_PREVIEW_COUNT = 8;

function FilterSection({ title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-b border-[#1F2937] pb-4 mb-4 last:border-b-0 last:pb-0 last:mb-0">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between mb-3 md:cursor-default"
      >
        <span className="text-sm font-semibold text-white">{title}</span>
        <ChevronDown
          className={`w-4 h-4 text-gray-500 md:hidden transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>
      <div className={`${open ? 'block' : 'hidden'} md:block`}>{children}</div>
    </div>
  );
}

function Chip({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
        active
          ? 'bg-amber-500 text-black border-amber-500'
          : 'bg-transparent text-gray-300 border-[#1F2937] hover:border-[#374151] hover:text-white'
      }`}
    >
      {children}
    </button>
  );
}

export default function IndicatorFilters() {
  const { filters, setFilter, toggleArrayFilter, resetFilters } = useAppContext();
  const [strategyExpanded, setStrategyExpanded] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const activeFilterCount =
    (filters.listingType !== 'All' ? 1 : 0) +
    filters.platforms.length +
    filters.assetClass.length +
    filters.strategyType.length +
    filters.timeframes.length +
    filters.difficulty.length +
    (filters.freeOnly ? 1 : 0) +
    (filters.minRating > 0 ? 1 : 0) +
    (filters.minWinRate > 0 ? 1 : 0);

  const visibleStrategyTypes = strategyExpanded
    ? STRATEGY_TYPES
    : STRATEGY_TYPES.slice(0, STRATEGY_PREVIEW_COUNT);

  const panelContent = (
    <div className="bg-[#111111] border border-[#1F2937] rounded-xl p-4">
      <FilterSection title="Search">
        <SearchBar />
      </FilterSection>

      <FilterSection title="Listing Type">
        <div className="flex flex-wrap gap-2">
          {LISTING_TYPES.map((type) => (
            <Chip
              key={type}
              active={filters.listingType === type}
              onClick={() => setFilter('listingType', type)}
            >
              {type}
            </Chip>
          ))}
        </div>
      </FilterSection>

      <FilterSection title="Platform">
        <div className="space-y-2">
          {PLATFORMS.map((p) => (
            <label key={p} className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer hover:text-white">
              <input
                type="checkbox"
                checked={filters.platforms.includes(p)}
                onChange={() => toggleArrayFilter('platforms', p)}
                className="w-4 h-4 rounded border-[#1F2937] bg-[#0A0A0A] text-amber-500 focus:ring-amber-500/50 focus:ring-offset-0"
              />
              {p}
            </label>
          ))}
        </div>
      </FilterSection>

      <FilterSection title="Asset Class">
        <div className="flex flex-wrap gap-2">
          {ASSET_CLASSES.map((a) => (
            <Chip key={a} active={filters.assetClass.includes(a)} onClick={() => toggleArrayFilter('assetClass', a)}>
              {a}
            </Chip>
          ))}
        </div>
      </FilterSection>

      <FilterSection title="Strategy Type">
        <div className="flex flex-wrap gap-2">
          {visibleStrategyTypes.map((s) => (
            <Chip
              key={s}
              active={filters.strategyType.includes(s)}
              onClick={() => toggleArrayFilter('strategyType', s)}
            >
              {s}
            </Chip>
          ))}
        </div>
        {STRATEGY_TYPES.length > STRATEGY_PREVIEW_COUNT && (
          <button
            type="button"
            onClick={() => setStrategyExpanded((e) => !e)}
            className="text-xs text-amber-400 hover:text-amber-300 mt-2"
          >
            {strategyExpanded ? 'Show less' : `+${STRATEGY_TYPES.length - STRATEGY_PREVIEW_COUNT} more`}
          </button>
        )}
      </FilterSection>

      <FilterSection title="Timeframe">
        <div className="flex flex-wrap gap-2">
          {TIMEFRAMES.map((t) => (
            <Chip key={t} active={filters.timeframes.includes(t)} onClick={() => toggleArrayFilter('timeframes', t)}>
              {t}
            </Chip>
          ))}
        </div>
      </FilterSection>

      <FilterSection title="Difficulty">
        <div className="flex flex-wrap gap-2">
          {DIFFICULTIES.map((d) => (
            <Chip key={d} active={filters.difficulty.includes(d)} onClick={() => toggleArrayFilter('difficulty', d)}>
              {d}
            </Chip>
          ))}
        </div>
      </FilterSection>

      <FilterSection title="Price">
        <label className="flex items-center justify-between cursor-pointer">
          <span className="text-sm text-gray-300">Free Only</span>
          <button
            type="button"
            onClick={() => setFilter('freeOnly', !filters.freeOnly)}
            className={`w-10 h-5.5 rounded-full relative transition-colors ${
              filters.freeOnly ? 'bg-amber-500' : 'bg-[#1F2937]'
            }`}
            style={{ height: '22px' }}
          >
            <span
              className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                filters.freeOnly ? 'translate-x-4' : ''
              }`}
            />
          </button>
        </label>
      </FilterSection>

      <FilterSection title="Min Rating">
        <StarRating
          rating={filters.minRating}
          interactive
          onChange={(n) => setFilter('minRating', n === filters.minRating ? 0 : n)}
        />
      </FilterSection>

      <FilterSection title="Min Win Rate">
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          value={filters.minWinRate}
          onChange={(e) => setFilter('minWinRate', Number(e.target.value))}
          className="w-full accent-amber-500"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>0%</span>
          <span className="text-amber-400 font-medium">{filters.minWinRate}%</span>
          <span>100%</span>
        </div>
      </FilterSection>

      <FilterSection title="Sort By">
        <select
          value={filters.sortBy}
          onChange={(e) => setFilter('sortBy', e.target.value)}
          className="w-full bg-[#0A0A0A] border border-[#1F2937] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-amber-500/50"
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </select>
      </FilterSection>

      <button
        type="button"
        onClick={resetFilters}
        className="w-full border border-amber-500/50 text-amber-400 hover:bg-amber-500/10 rounded-lg py-2 text-sm font-medium transition-colors"
      >
        Reset All Filters
      </button>
    </div>
  );

  return (
    <>
      <button
        type="button"
        onClick={() => setMobileOpen(true)}
        className="md:hidden w-full flex items-center justify-center gap-2 border border-[#1F2937] rounded-lg py-2.5 text-sm font-medium text-white mb-4"
      >
        <SlidersHorizontal className="w-4 h-4" />
        Filters {activeFilterCount > 0 && `(${activeFilterCount})`}
      </button>

      <div className="hidden md:block">{panelContent}</div>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="absolute inset-0 bg-black/70" onClick={() => setMobileOpen(false)} />
          <div className="absolute left-0 top-0 bottom-0 w-[85%] max-w-sm bg-[#0A0A0A] overflow-y-auto p-4">
            <div className="flex items-center justify-between mb-4">
              <span className="text-white font-semibold">Filters {activeFilterCount > 0 && `(${activeFilterCount})`}</span>
              <button type="button" onClick={() => setMobileOpen(false)} aria-label="Close filters">
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>
            {panelContent}
          </div>
        </div>
      )}
    </>
  );
}
