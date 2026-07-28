import React, { useState, useEffect } from 'react';
import { apiService } from '../utils/api';
import { Spinner } from '../components/ui/Spinner';
import { Badge } from '../components/ui/Badge';
import { 
  Award, 
  TrendingUp, 
  ShieldCheck, 
  ExternalLink,
  DollarSign,
  HelpCircle,
  Clock
} from 'lucide-react';

export const Brokers = () => {
  const [brokers, setBrokers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setSeo({
  title: `${fetchedInd.name} — Review, Parameters, and Audits | FalconSpido`,
  description: fetchedInd.description || `${fetchedInd.name} reviews, parameters, and trust score on FalconSpido.`,
  path: `/indicators/${fetchedInd.slug}`
});

    const fetchBrokersData = async () => {
      setIsLoading(true);
      try {
        const res = await apiService.getBrokers();
        if (res?.success) {
          setBrokers(res.data);
        }
      } catch (err) {
        console.error('Failed to get brokers listing catalogues:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchBrokersData();
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      
      {/* Title */}
      <div className="space-y-1">
        <span className="text-[10px] text-amber-500 uppercase tracking-widest font-extrabold flex items-center space-x-1">
          <ShieldCheck className="h-4.5 w-4.5 text-amber-500" />
          <span>REGULATORY FEEDS COMPLIANCE</span>
        </span>
        <h1 className="text-xl sm:text-3xl font-black text-white">Regulated Trading Broker Partners</h1>
        <p className="text-xs text-slate-400 max-w-xl">
          Execute Expert Advisors and automated signal alerts on highly regulated retail brokerage accounts. Avoid offshore bucket-shops to keep trading parameter slippages protected.
        </p>
      </div>

      {isLoading && brokers.length === 0 ? (
        <div className="py-20 flex flex-col items-center">
          <Spinner size="lg" />
          <p className="text-xs text-slate-500 font-mono">Comparing broker configurations...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {brokers.map((broker) => (
            <div key={broker._id} className="bg-[#08080d] border border-white/5 rounded-2xl p-5 hover:border-amber-500/20 transition-all flex flex-col justify-between h-full relative group">
              
              {/* Featured overlays */}
              {broker.isRecommended && (
                <span className="absolute top-4 right-4 bg-amber-500 text-black text-[8px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full">
                  FALCON RECOMMENDED
                </span>
              )}

              <div className="space-y-4">
                <div className="space-y-1">
                  <h3 className="text-base font-extrabold text-white group-hover:text-amber-500 transition-colors">{broker.name}</h3>
                  <div className="flex flex-wrap gap-1">
                    {broker.regulatedBy?.map((reg) => (
                      <span key={reg} className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[9px] font-bold px-1.5 rounded uppercase font-mono">
                        {reg} Verified
                      </span>
                    ))}
                  </div>
                </div>

                <p className="text-xs text-slate-400 leading-relaxed">
                  {broker.description || `Highly rated execution environments designed to run complex algorithmic systems and MQL scripts flawlessly.`}
                </p>

                {/* Properties grids */}
                <div className="grid grid-cols-2 gap-3 bg-[#11111a]/60 border border-white/5 rounded-xl p-3 font-mono text-[11px] text-slate-400">
                  <div>
                    <span className="text-[9px] text-slate-500 block uppercase">Min Deposit</span>
                    <span className="font-bold text-slate-200">${broker.minDeposit || 10}</span>
                  </div>
                  <div>
                    <span className="text-[9px] text-slate-500 block uppercase">Spread Type</span>
                    <span className="font-bold text-slate-200">{broker.spreadType} Spreads</span>
                  </div>
                  <div className="col-span-2 border-t border-white/5 pt-1.5 mt-1">
                    <span className="text-[9px] text-slate-500 block uppercase mb-0.5">Asset Coverage</span>
                    <span className="text-slate-300 font-semibold text-[10px] truncate block" title={broker.assetsCovered?.join(', ')}>
                      {broker.assetsCovered?.slice(0, 3).join(', ') || 'Forex, CFDs, Metals'}
                    </span>
                  </div>
                </div>

                {/* Platforms chipsets */}
                {broker.platforms && broker.platforms.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1">
                    <span className="text-[9px] font-bold text-slate-500">Tech:</span>
                    {broker.platforms.map((plat) => (
                      <Badge key={plat} variant="blue">{plat}</Badge>
                    ))}
                  </div>
                )}
              </div>

              <div className="pt-6 border-t border-white/5 mt-6 flex items-center justify-between">
                <div>
                  <span className="text-[9px] text-slate-500 font-mono uppercase block">Falcon trust</span>
                  <span className="text-amber-500 font-black font-mono text-sm">{broker.trustScore || '96'}/100</span>
                </div>

                <a
                  href={broker.affiliateUrl || broker.signupUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="bg-amber-500 hover:bg-amber-400 text-black text-xs font-black px-4.5 py-2.5 rounded-xl flex items-center space-x-1 shadow-md shadow-amber-500/5 transition-all"
                >
                  <span>Open raw Account</span>
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>

            </div>
          ))}
        </div>
      )}

      {/* Dynamic guidance callout */}
      <div className="bg-[#10101b] border border-white/10 p-5 rounded-2xl flex items-start space-x-3 text-xs leading-relaxed text-slate-400">
        <Clock className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
        <div>
          <span className="font-bold text-white block mb-0.5">Note on Algorithmic Latency loops:</span>
          <p>
            When utilizing MT4/MT5 expert advisor files, running them directly on VPS nodes colocated inside your raw spread brokers Liquidity Centre (typically NY4 in London/New Jersey) helps eliminate dynamic execution latencies, bringing execution parameter slippage to near zero intervals!
          </p>
        </div>
      </div>

    </div>
  );
};
