import React from 'react';
import { Link } from 'react-router-dom';
import { useApp } from '../../context/AppContext';
import { StarRating } from '../ui/StarRating';
import { Badge } from '../ui/Badge';
import { 
  BarChart2, 
  CheckCircle, 
  ShieldAlert, 
  AlertTriangle, 
  TrendingUp, 
  Plus, 
  Check, 
  ExternalLink 
} from 'lucide-react';

export const IndicatorCard = ({ indicator }) => {
  const { addToCompare, compareList, removeFromCompare } = useApp();
  
  const isCompared = compareList.some(item => item._id === indicator._id);

  const handleCompareClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (isCompared) {
      removeFromCompare(indicator._id);
    } else {
      addToCompare(indicator);
    }
  };

  // Safe color formatting for TrustScore (0-100)
  const getTrustScoreColor = (score) => {
    if (score >= 80) return 'from-emerald-500 to-teal-500';
    if (score >= 50) return 'from-amber-500 to-yellow-500';
    return 'from-rose-500 to-red-500';
  };

  const formattedPrice = indicator.isFree || indicator.price === 0 
    ? 'FREE' 
    : `$${indicator.price}`;

  return (
    <div className="group relative rounded-xl border border-white/5 bg-[#0a0a0f]/80 p-4 transition-all duration-300 hover:border-amber-500/20 hover:bg-[#0c0c16] hover:translate-y-[-2px] flex flex-col justify-between neon-border-amber h-full">
      
      {/* Top Media Thumbnail / Logo */}
      <Link to={`/indicators/${indicator.slug}`} className="block">
        <div className="relative aspect-video w-full rounded-lg overflow-hidden bg-slate-900 border border-white/5 flex items-center justify-center">
          {indicator.imageUrl ? (
            <img 
              src={indicator.imageUrl} 
              alt={indicator.name} 
              className="object-cover w-full h-full group-hover:scale-105 transition-transform duration-300"
              referrerPolicy="no-referrer"
            />
          ) : (
            <div className="w-full h-full bg-gradient-to-br from-[#12121e] to-[#080812] flex flex-col items-center justify-center p-3 text-center">
              <BarChart2 className="h-8 w-8 text-amber-500/30 mb-2" />
              <span className="font-semibold text-xs text-slate-400 group-hover:text-white transition-colors duration-200">
                {indicator.name}
              </span>
            </div>
          )}

          {/* Type tag overlays */}
          <div className="absolute top-2 left-2 flex flex-col gap-1.5">
            <Badge variant="blue">{indicator.listingType}</Badge>
            {indicator.isVerified && (
              <span className="flex items-center space-x-0.5 bg-emerald-500/80 text-[8px] text-white px-2 py-0.5 rounded-full font-bold uppercase tracking-wider select-none">
                <CheckCircle className="h-2 w-2 stroke-[3]" />
                <span>Verified</span>
              </span>
            )}
            {indicator.isScamFlagged && (
              <span className="flex items-center space-x-0.5 bg-rose-500 text-[8px] text-white px-2 py-0.5 rounded-full font-bold uppercase tracking-wider select-none">
                <AlertTriangle className="h-2.5 w-2.5" />
                <span>Flagged</span>
              </span>
            )}
          </div>

          <div className="absolute top-2 right-2">
            <Badge variant="gray">{indicator.difficulty}</Badge>
          </div>
        </div>
      </Link>

      {/* Main Core Description */}
      <div className="mt-4 flex-grow flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between text-[11px] text-slate-500 font-mono">
            <span>By {indicator.author}</span>
            <span>{typeof indicator.platform === 'object' ? indicator.platform?.name : indicator.platform}</span>
          </div>

          <Link to={`/indicators/${indicator.slug}`} className="block mt-1">
            <h3 className="text-sm font-semibold text-white group-hover:text-amber-400 transition-colors duration-200 line-clamp-1">
              {indicator.name}
            </h3>
          </Link>

          <p className="mt-1.5 text-[11px] text-slate-400 line-clamp-2 h-8 leading-relaxed">
            {indicator.description}
          </p>

          {/* Grid target indicators parameters */}
          {indicator.assetClass && indicator.assetClass.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2.5">
              {indicator.assetClass.slice(0, 3).map((asset, i) => (
                <span key={i} className="text-[9px] bg-white/5 border border-white/5 rounded-md px-1.5 py-0.5 text-slate-300 font-medium">
                  {asset}
                </span>
              ))}
            </div>
          )}

          {/* Audit parameters */}
          {indicator.backtestData && (
            <div className="grid grid-cols-3 gap-1 bg-white/5 border border-white/5 rounded-lg p-2 mt-3.5 text-center text-[10px] font-mono select-none">
              <div className="border-r border-white/5">
                <div className="text-slate-500 uppercase tracking-widest text-[8px]">Win Rate</div>
                <div className={`font-bold mt-0.5 text-xs ${indicator.backtestData.winRate >= 65 ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {indicator.backtestData.winRate}%
                </div>
              </div>
              <div className="border-r border-white/5">
                <div className="text-slate-500 uppercase tracking-widest text-[8px]">Drawdown</div>
                <div className="font-bold text-rose-400 mt-0.5 text-xs">
                  {indicator.backtestData.maxDrawdown}%
                </div>
              </div>
              <div>
                <div className="text-slate-500 uppercase tracking-widest text-[8px]">Audit</div>
                <div className={`mt-0.5 font-semibold ${
                  indicator.backtestData.auditStatus === 'Verified' ? 'text-emerald-400' : 
                  indicator.backtestData.auditStatus === 'Suspicious' ? 'text-rose-400' : 'text-slate-400'
                }`}>
                  {indicator.backtestData.auditStatus}
                </div>
              </div>
            </div>
          )}

          {/* Trust Score block */}
          {indicator.trustScore > 0 && (
            <div className="mt-3 space-y-1">
              <div className="flex justify-between text-[9px] text-slate-500">
                <span className="uppercase tracking-wider">Falcon trust score</span>
                <span className="font-bold text-slate-300">{indicator.trustScore}/100</span>
              </div>
              <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                <div 
                  className={`h-full bg-gradient-to-r rounded-full ${getTrustScoreColor(indicator.trustScore)}`}
                  style={{ width: `${indicator.trustScore}%` }}
                ></div>
              </div>
            </div>
          )}
        </div>

        {/* Dynamic Card actions */}
        <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between">
          <div className="flex flex-col">
            <span className="text-xs font-mono font-medium text-amber-500">{formattedPrice}</span>
            <span className="text-[9px] text-slate-500 uppercase tracking-wider">{indicator.pricingModel}</span>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handleCompareClick}
              className={`p-1.5 rounded-lg border text-xs flex items-center justify-center transition-all ${
                isCompared 
                  ? 'bg-amber-500/10 border-amber-500/30 text-amber-400' 
                  : 'border-white/5 bg-[#12121a]/50 text-slate-400 hover:text-white hover:border-white/20'
              }`}
              title={isCompared ? "Remove from comparison Sandbox" : "Add to comparison Sandbox"}
            >
              {isCompared ? <Check className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
            </button>

            <Link 
              to={`/indicators/${indicator.slug}`} 
              className="flex items-center space-x-1 bg-amber-500 hover:bg-amber-400 text-black font-semibold text-xs px-3 py-1.5 rounded-lg transition-all"
            >
              <span>Explore</span>
              <ExternalLink className="h-3 w-3 inline" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
