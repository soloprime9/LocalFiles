import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { setSeo } from '../utils/seo';
import { useApp } from '../context/AppContext';
import { StarRating } from '../components/ui/StarRating';
import { Badge } from '../components/ui/Badge';
import { 
  ArrowLeftRight, 
  Trash2, 
  ArrowLeft, 
  CheckCircle, 
  AlertTriangle, 
  HelpCircle,
  PlusCircle
} from 'lucide-react';

export const Compare = () => {
  const { compareList, removeFromCompare, clearCompare } = useApp();

  useEffect(() => {
    setSeo({
  title: `${fetchedInd.name} — Review, Parameters, and Audits | FalconSpido`,
  description: fetchedInd.description || `${fetchedInd.name} reviews, parameters, and trust score on FalconSpido.`,
  path: `/indicators/${fetchedInd.slug}`
});
  }, []);

  if (compareList.length === 0) {
    return (
      <div className="max-w-xl mx-auto py-24 text-center space-y-6">
        <ArrowLeftRight className="h-16 w-16 text-slate-600 mx-auto animate-pulse" />
        <h2 className="text-xl font-bold text-white">Compare Sandbox is Empty</h2>
        <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
          Select target cards from our indicator and expert advisor list to review win-rates, maximum drawdowns, license prices, and platforms side-by-side.
        </p>
        <Link to="/indicators" className="bg-amber-500 hover:bg-amber-400 text-black font-extrabold text-xs px-5 py-2.5 rounded-lg inline-block shadow-lg shadow-amber-500/10">
          BROWSE INDICATORS TO AUDIT
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      
      {/* Return button */}
      <div className="flex items-center justify-between">
        <Link to="/indicators" className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-400 hover:text-white transition-all">
          <ArrowLeft className="h-4 w-4" />
          <span>Return to Browse Tools</span>
        </Link>
        <button 
          onClick={clearCompare}
          className="text-xs font-semibold text-rose-400 hover:text-rose-300 underline select-none"
        >
          Clear Comparisons Matrix
        </button>
      </div>

      {/* Header properties */}
      <div className="space-y-1">
        <span className="text-[10px] text-[#818cf8] uppercase tracking-widest font-extrabold flex items-center space-x-1">
          <ArrowLeftRight className="h-4.5 w-4.5 text-[#818cf8]" />
          <span>Comparative Quant Auditing Sandbox</span>
        </span>
        <h1 className="text-xl sm:text-3xl font-black text-white">Side-by-Side Comparison Matrix</h1>
        <p className="text-xs text-slate-400 max-w-xl leading-relaxed">
          Analyze up to 3 automated trading indicators or EA configurations. Keep risk variables aligned before finalizing licensing operations.
        </p>
      </div>

      {/* Main Sandbox Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 pt-4">
        
        {/* Metric Names description (Column 1) */}
        <div className="hidden md:flex flex-col space-y-4 pt-[180px] text-xs font-bold text-slate-500 uppercase tracking-wider font-mono">
          <div className="h-10 flex items-center">System Pricing</div>
          <div className="h-10 flex items-center border-t border-white/5">System Platform</div>
          <div className="h-10 flex items-center border-t border-white/5">Listing Type</div>
          <div className="h-10 flex items-center border-t border-white/5">Asset Volatility Class</div>
          <div className="h-10 flex items-center border-t border-white/5">Win Rate (%)</div>
          <div className="h-10 flex items-center border-t border-white/5">Max Drawdown (%)</div>
          <div className="h-10 flex items-center border-t border-white/5">Audit Status</div>
          <div className="h-10 flex items-center border-t border-white/5">Trust Score (Index)</div>
          <div className="h-10 flex items-center border-t border-white/5">Complexity Sizing</div>
        </div>

        {/* Indicators Comparisons maps (Columns 2-4) */}
        {compareList.map((item) => (
          <div key={item._id} className="bg-[#08080d] border border-white/5 rounded-2xl p-5 space-y-4 flex flex-col justify-between hover:border-amber-500/20 transition-all relative">
            
            {/* Delete/Remove absolute button */}
            <button 
              onClick={() => removeFromCompare(item._id)}
              className="absolute right-4 top-4 text-slate-500 hover:text-rose-400"
              title="Remove from Compare"
            >
              <Trash2 className="h-4 w-4" />
            </button>

            {/* Thumbnail name detail */}
            <div className="space-y-2 pb-4 border-b border-white/5 h-[160px] flex flex-col justify-between">
              <div className="space-y-1">
                <Badge variant="amber">{item.listingType}</Badge>
                <Link to={`/indicators/${item.slug}`} className="block">
                  <h3 className="text-sm font-bold text-white hover:text-amber-400 transition-colors line-clamp-2 leading-snug">
                    {item.name}
                  </h3>
                </Link>
                <div className="text-[10px] text-slate-500 font-mono">by {item.author}</div>
              </div>
              
              <div className="flex items-center space-x-1.5 text-xs text-slate-300">
                <span>Rating:</span>
                <StarRating rating={item.rating || 0} size={11} />
              </div>
            </div>

            {/* Parameters Matrix list */}
            <div className="space-y-4 font-mono text-xs text-slate-300">
              
              <div className="h-10 flex items-center justify-between md:justify-start border-t border-white/5 md:border-t-0 py-1.5 md:py-0">
                <span className="md:hidden text-slate-500 uppercase tracking-wider text-[10px] font-bold">Price</span>
                <span className="text-amber-500 font-black text-sm">{item.isFree ? 'FREE' : `$${item.price}`}</span>
              </div>

              <div className="h-10 flex items-center justify-between md:justify-start border-t border-white/5 py-1.5 md:py-0">
                <span className="md:hidden text-slate-500 uppercase tracking-wider text-[10px] font-bold">Platform</span>
                <span className="text-slate-100 font-semibold">{typeof item.platform === 'object' ? item.platform?.name : item.platform}</span>
              </div>

              <div className="h-10 flex items-center justify-between md:justify-start border-t border-white/5 py-1.5 md:py-0">
                <span className="md:hidden text-slate-500 uppercase tracking-wider text-[10px] font-bold">Type</span>
                <Badge variant="blue">{item.listingType}</Badge>
              </div>

              <div className="h-10 flex items-center justify-between md:justify-start border-t border-white/5 py-1.5 md:py-0">
                <span className="md:hidden text-slate-500 uppercase tracking-wider text-[10px] font-bold">Asset Class</span>
                <span className="text-slate-200 font-bold truncate max-w-[150px]">{item.assetClass?.slice(0, 2).join(', ') || 'Forex'}</span>
              </div>

              <div className="h-10 flex items-center justify-between md:justify-start border-t border-white/5 py-1.5 md:py-0">
                <span className="md:hidden text-slate-500 uppercase tracking-wider text-[10px] font-bold">Win Rate</span>
                <span className="font-extrabold text-emerald-400">{item.backtestData?.winRate || '--'}%</span>
              </div>

              <div className="h-10 flex items-center justify-between md:justify-start border-t border-white/5 py-1.5 md:py-0">
                <span className="md:hidden text-slate-500 uppercase tracking-wider text-[10px] font-bold">Max Drawdown</span>
                <span className="font-bold text-rose-400">{item.backtestData?.maxDrawdown || '--'}%</span>
              </div>

              <div className="h-10 flex items-center justify-between md:justify-start border-t border-white/5 py-1.5 md:py-0">
                <span className="md:hidden text-slate-500 uppercase tracking-wider text-[10px] font-bold">Audit Status</span>
                <span className={item.backtestData?.auditStatus === 'Verified' ? 'text-emerald-400' : 'text-slate-400'}>
                  {item.backtestData?.auditStatus || 'Unaudited'}
                </span>
              </div>

              <div className="h-10 flex items-center justify-between md:justify-start border-t border-white/5 py-1.5 md:py-0">
                <span className="md:hidden text-slate-500 uppercase tracking-wider text-[10px] font-bold">Trust Score</span>
                <span className="text-amber-500 font-extrabold">{item.trustScore}/100</span>
              </div>

              <div className="h-10 flex items-center justify-between md:justify-start border-t border-white/5 py-1.5 md:py-0">
                <span className="md:hidden text-slate-500 uppercase tracking-wider text-[10px] font-bold">Difficulty</span>
                <Badge variant="gray">{item.difficulty}</Badge>
              </div>

            </div>

            {/* Active Redirect Action */}
            <div className="pt-4 border-t border-white/5">
              <Link 
                to={`/indicators/${item.slug}`} 
                className="block text-center bg-amber-500 hover:bg-amber-400 text-black py-2 rounded-xl font-bold text-xs"
              >
                Launch specifications Audit
              </Link>
            </div>

          </div>
        ))}

        {/* Dummy/Add Col for side-by-side filling up to 3 */}
        {compareList.length < 3 && (
          <div className="border border-dashed border-white/10 rounded-2xl p-6 h-full flex flex-col justify-center items-center text-center text-slate-600 space-y-3 min-h-[350px]">
            <PlusCircle className="h-10 w-10 text-slate-700 hover:scale-105 transition-transform" />
            <div>
              <p className="text-xs font-bold text-slate-500 uppercase font-mono">Sandbox spot open</p>
              <p className="text-[10px] text-slate-500 max-w-[150px] mt-1">Select another system to compare side-by-side</p>
            </div>
            <Link to="/indicators" className="bg-white/5 border border-white/5 text-slate-400 hover:text-white px-3.5 py-1.5 rounded-lg text-[10px] font-bold transition-all">
              Add Tool
            </Link>
          </div>
        )}

      </div>

    </div>
  );
};
