import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { apiService } from '../utils/api';
import { setSeo } from '../utils/seo';
import { useApp } from '../context/AppContext';
import { IndicatorGrid } from '../components/indicators/IndicatorGrid';
import { Badge } from '../components/ui/Badge';
import { 
  Search, 
  Sparkles, 
  ArrowUpDown, 
  RotateCcw, 
  Cpu, 
  Layers, 
  ArrowLeftRight, 
  Check, 
  X,
  Plus
} from 'lucide-react';

export const Indicators = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const { categories, platforms, compareList, removeFromCompare, clearCompare } = useApp();

  const [indicators, setIndicators] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [total, setTotal] = useState(0);

  // Parse state bounds from URL parameters
  const searchVal = searchParams.get('search') || '';
  const currentCategory = searchParams.get('category') || '';
  const currentPlatform = searchParams.get('platform') || '';
  const currentType = searchParams.get('type') || '';
  const currentPricing = searchParams.get('pricing') || 'All';
  const currentDifficulty = searchParams.get('difficulty') || '';
  const isPinned = searchParams.get('pinned') === 'true';
  const isFlagged = searchParams.get('flagged') === 'true';
  const sortBy = searchParams.get('sort') || 'trendingScore';

  useEffect(() => {
    // Elegant doc titles
    setSeo({
  title: `${fetchedInd.name} — Review, Parameters, and Audits | FalconSpido`,
  description: fetchedInd.description || `${fetchedInd.name} reviews, parameters, and trust score on FalconSpido.`,
  path: `/indicators/${fetchedInd.slug}`
});

    const fetchIndicatorsList = async () => {
      setIsLoading(true);
      try {
        const queryParams = {
          limit: 20
        };

        if (searchVal) queryParams.search = searchVal;
        if (currentCategory) queryParams.category = currentCategory;
        if (currentPlatform) queryParams.platform = currentPlatform;
        if (currentType) queryParams.listingType = currentType;
        if (currentDifficulty) queryParams.difficulty = currentDifficulty;
        if (isPinned) queryParams.isFeatured = true;
        if (isFlagged) queryParams.isScamFlagged = true;
        if (sortBy) queryParams.sort = sortBy;

        if (currentPricing === 'Free') {
          queryParams.isFree = true;
        } else if (currentPricing === 'Premium') {
          queryParams.isFree = false;
        }

        const res = await apiService.getIndicators(queryParams);
        if (res?.success) {
          setIndicators(res.data);
          setTotal(res.total || res.data.length);
        }
      } catch (err) {
        console.error('Failed to load indicators:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchIndicatorsList();
  }, [
    searchVal, currentCategory, currentPlatform, 
    currentType, currentPricing, currentDifficulty, 
    isPinned, isFlagged, sortBy
  ]);

  const updateParam = (key, value) => {
    const newParams = new URLSearchParams(searchParams);
    if (value) {
      newParams.set(key, value);
    } else {
      newParams.delete(key);
    }
    setSearchParams(newParams);
  };

  const handleClear = () => {
    setSearchParams(new URLSearchParams());
  };

  const listingTypes = [
    'Indicator', 'EA', 'Bot', 'Signal', 'Strategy', 
    'Screener', 'Script', 'Alert', 'CopyTrading', 'Template'
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 min-h-[750px]">
      
      {/* Title block */}
      <div className="space-y-1">
        <span className="text-[10px] text-amber-500 uppercase tracking-widest font-extrabold flex items-center space-x-1">
          <Sparkles className="h-4.5 w-4.5 text-amber-500" />
          <span>REAL-TIME AUDIT INTELLIGENCE</span>
        </span>
        <h1 className="text-xl sm:text-3xl font-black text-white">Algorithmic Technical Directory</h1>
        <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
          Filter, compare, and audit over {total || indicators.length}+ quantitative strategy codes, indicators, and systems listed by traders on FalconSpido.
        </p>
      </div>

      {/* Advanced Filter Control Box */}
      <div className="bg-[#0b0b12] border border-white/5 rounded-2xl p-5 space-y-4 shadow-xl">
        
        {/* Row 1: Search Inputs, Category, Platform */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          
          {/* Keyword Query Search */}
          <div className="relative">
            <input
              type="text"
              placeholder="Search by keywords, tags..."
              value={searchVal}
              onChange={(e) => updateParam('search', e.target.value)}
              className="w-full bg-[#11111b] border border-white/5 rounded-xl py-2 pl-9 pr-3 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 transition-all font-mono"
            />
            <Search className="absolute left-3 top-3 h-3.5 w-3.5 text-slate-500" />
          </div>

          {/* Select Category */}
          <div className="relative">
            <select
              value={currentCategory}
              onChange={(e) => updateParam('category', e.target.value)}
              className="w-full bg-[#11111b] border border-white/5 text-slate-300 text-xs rounded-xl py-2 px-3 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500/20"
            >
              <option value="">-- Select Category --</option>
              {categories.map((cat) => (
                <option key={cat._id} value={cat._id}>{cat.name}</option>
              ))}
            </select>
          </div>

          {/* Select Platform */}
          <div className="relative">
            <select
              value={currentPlatform}
              onChange={(e) => updateParam('platform', e.target.value)}
              className="w-full bg-[#11111b] border border-white/5 text-slate-300 text-xs rounded-xl py-2 px-3 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500/20"
            >
              <option value="">-- Select Platform --</option>
              {platforms.map((plat) => (
                <option key={plat._id} value={plat._id}>{plat.name}</option>
              ))}
            </select>
          </div>

          {/* Select Pricing */}
          <div className="relative">
            <select
              value={currentPricing}
              onChange={(e) => updateParam('pricing', e.target.value)}
              className="w-full bg-[#11111b] border border-white/5 text-slate-300 text-xs rounded-xl py-2 px-3 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500/20"
            >
              <option value="All">Pricing: All Models</option>
              <option value="Free">Free Tools Only</option>
              <option value="Premium">Premium License Only</option>
            </select>
          </div>

        </div>

        {/* Row 2: Sort, difficulty, listing types */}
        <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-white/5 text-xs text-slate-400">
          <div className="flex flex-wrap items-center gap-3">
            
            {/* Sorting order */}
            <div className="flex items-center space-x-1 bg-[#10101a] border border-white/5 px-2.5 py-1 rounded-lg">
              <ArrowUpDown className="h-3.5 w-3.5 text-amber-500" />
              <select
                value={sortBy}
                onChange={(e) => updateParam('sort', e.target.value)}
                className="bg-transparent border-none text-slate-300 text-[11px] focus:outline-none focus:ring-0 max-w-[130px]"
              >
                <option value="trendingScore">Sort: Popularity</option>
                <option value="rating">Sort: High Ratings</option>
                <option value="price">Sort: Price (Low - High)</option>
                <option value="-price">Sort: Price (High - Low)</option>
                <option value="backtestData.winRate">Sort: Best Win Rate</option>
              </select>
            </div>

            {/* Select difficulty */}
            <div className="flex items-center space-x-1 bg-[#10101a] border border-white/5 px-2.5 py-1 rounded-lg">
              <span className="text-[10px] uppercase font-bold text-slate-500">Tier:</span>
              <select
                value={currentDifficulty}
                onChange={(e) => updateParam('difficulty', e.target.value)}
                className="bg-transparent border-none text-slate-300 text-[11px] focus:outline-none focus:ring-0"
              >
                <option value="">All Tiers</option>
                <option value="Beginner">Beginner</option>
                <option value="Intermediate">Intermediate</option>
                <option value="Advanced">Advanced</option>
                <option value="Expert">Expert</option>
              </select>
            </div>

            {/* Quick Listing Type Filters */}
            <div className="flex flex-wrap items-center gap-1.5">
              <button
                onClick={() => updateParam('type', '')}
                className={`px-2.5 py-1 rounded-lg text-[10px] font-bold border transition-colors ${
                  !currentType 
                    ? 'bg-amber-500/10 border-amber-500/30 text-amber-400' 
                    : 'bg-[#10101a] border-white/5 text-slate-400 hover:text-white'
                }`}
              >
                All Types
              </button>
              {listingTypes.map((type) => (
                <button
                  key={type}
                  onClick={() => updateParam('type', type)}
                  className={`px-2.5 py-1 rounded-lg text-[10px] font-bold border transition-colors ${
                    currentType === type 
                      ? 'bg-amber-500/10 border-amber-500/30 text-amber-400' 
                      : 'bg-[#10101a] border-white/5 text-slate-400 hover:text-white'
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>

          </div>

          {/* Reset Filters button */}
          <button
            onClick={handleClear}
            className="flex items-center space-x-1 hover:text-white transition-colors bg-white/5 hover:bg-white/10 px-3 py-1 rounded-lg text-[11px] font-bold border border-white/5 text-slate-400"
          >
            <RotateCcw className="h-3.5 w-3.5 text-amber-500" />
            <span>Reset ALL Filters</span>
          </button>
        </div>
      </div>

      {/* Main listings Grid output */}
      <div className="space-y-4">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>Displaying {indicators.length} indicators out of {total} listings matching search patterns</span>
          {isFlagged && <Badge variant="red">Displaying scam-flagged listings only</Badge>}
        </div>

        <IndicatorGrid 
          indicators={indicators} 
          isLoading={isLoading} 
          onClearFilters={handleClear} 
        />
      </div>

      {/* Floating Side-by-Side compare drawer widget */}
      {compareList.length > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 w-full max-w-2xl px-4 animate-bounce-subtle">
          <div className="bg-[#0b0b14]/95 border border-amber-500/30 rounded-2xl p-4 shadow-2xl shadow-black/90 backdrop-blur-md flex items-center justify-between gap-6">
            <div className="flex items-center space-x-3">
              <div className="h-8 w-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
                <ArrowLeftRight className="h-4.5 w-4.5 text-amber-500" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-white flex items-center space-x-1">
                  <span>Compare Sandbox</span>
                  <span className="bg-amber-500 text-black px-1.5 rounded-full text-[9px] font-black">{compareList.length}/3</span>
                </h4>
                <p className="text-[10px] text-slate-400">Explore parameter differences side-by-side</p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              {compareList.map((item) => (
                <div key={item._id} className="relative bg-white/5 border border-white/5 rounded-lg px-2.5 py-1.5 text-[10px] text-slate-300 pr-7 flex items-center gap-1 font-semibold">
                  <span className="truncate max-w-[80px]">{item.name}</span>
                  <button 
                    onClick={() => removeFromCompare(item._id)}
                    className="absolute right-1 top-2.5 hover:text-white text-slate-500"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
              {compareList.length < 3 && (
                <div className="border border-dashed border-white/10 rounded-lg px-2.5 py-1.5 text-[10px] text-slate-600 flex items-center gap-1 select-none">
                  <Plus className="h-3 w-3" />
                  <span>Choose item</span>
                </div>
              )}
            </div>

            <div className="flex items-center space-x-2 flex-shrink-0">
              <button 
                onClick={clearCompare}
                className="text-[10px] text-slate-400 hover:text-slate-200 underline font-bold"
              >
                Clear
              </button>
              <Link 
                to="/compare" 
                className="bg-amber-500 hover:bg-amber-400 text-black font-extrabold text-xs px-4 py-2 rounded-xl shadow-lg shadow-amber-500/10 transition-all text-center leading-none"
              >
                LAUNCH SANDBOX
              </Link>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
