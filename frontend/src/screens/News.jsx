import React, { useState, useEffect } from 'react';
import { apiService } from '../utils/api';
import { setSeo } from '../utils/seo';
import { Spinner } from '../components/ui/Spinner';
import { Badge } from '../components/ui/Badge';
import { 
  FileText, 
  RotateCw, 
  Search, 
  AlertTriangle, 
  CheckCircle2, 
  ShieldAlert,
  SlidersHorizontal
} from 'lucide-react';

export const News = () => {
  const [news, setNews] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [sentimentFilter, setSentimentFilter] = useState('All');
  const [searchVal, setSearchVal] = useState('');

  useEffect(() => {
    setSeo({
  title: `${fetchedInd.name} — Review, Parameters, and Audits | FalconSpido`,
  description: fetchedInd.description || `${fetchedInd.name} reviews, parameters, and trust score on FalconSpido.`,
  path: `/indicators/${fetchedInd.slug}`
});

    const fetchNewsArticles = async () => {
      setIsLoading(true);
      try {
        const queryParams = {};
        if (sentimentFilter !== 'All') queryParams.sentiment = sentimentFilter;
        if (searchVal) queryParams.search = searchVal;

        const res = await apiService.getMarketNews(queryParams);
        if (res?.success) {
          setNews(res.data);
        }
      } catch (err) {
        console.error('Failed to get market flash news articles:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchNewsArticles();
  }, [sentimentFilter, searchVal]);

  const getSentimentBadge = (sent) => {
    switch (sent) {
      case 'Bullish':
        return <Badge variant="green">Bullish Sentiment</Badge>;
      case 'Bearish':
        return <Badge variant="red">Bearish Sentiment</Badge>;
      default:
        return <Badge variant="gray">Neutral Sweep</Badge>;
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      
      {/* Title */}
      <div className="space-y-1">
        <span className="text-[10px] text-amber-500 uppercase tracking-widest font-extrabold flex items-center space-x-1">
          <ShieldAlert className="h-4.5 w-4.5 text-amber-500 animate-pulse" />
          <span>Macro Sentiment Intelligence</span>
        </span>
        <h1 className="text-xl sm:text-3xl font-black text-white">Falcon Intelligence Newsroom</h1>
        <p className="text-xs text-slate-400 max-w-xl">
          Track high-impact macroeconomic releases, central bank hawkish/dovish statements, and systemic market liquidity changes affecting your trading bots.
        </p>
      </div>

      {/* Filters bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 border-b border-white/5 pb-4 items-center">
        
        {/* Sentiment dropdown select */}
        <div className="flex items-center space-x-2 bg-[#12121a] border border-white/5 rounded-xl px-3 py-1.5 max-w-[220px]">
          <SlidersHorizontal className="h-4 w-4 text-amber-500" />
          <select
            value={sentimentFilter}
            onChange={(e) => setSentimentFilter(e.target.value)}
            className="bg-transparent border-none text-slate-200 text-xs focus:ring-0 focus:outline-none"
          >
            <option value="All">All Sentiment Sweeps</option>
            <option value="Bullish">Bullish Sentiment Only</option>
            <option value="Neutral">Neutral Signals Only</option>
            <option value="Bearish">Bearish Sentiment Only</option>
          </select>
        </div>

        {/* Text keyword filter */}
        <div className="relative col-span-2">
          <input
            type="text"
            placeholder="Search newsroom archives, inflation statements, CPI targets..."
            value={searchVal}
            onChange={(e) => setSearchVal(e.target.value)}
            className="w-full bg-[#11111a] border border-white/5 rounded-xl py-2 pl-9 pr-3 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500"
          />
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
        </div>

      </div>

      {isLoading && news.length === 0 ? (
        <div className="py-20 flex flex-col items-center">
          <Spinner size="lg" />
          <p className="text-xs text-slate-500 font-mono">Reindexing flash bulletins archives...</p>
        </div>
      ) : (
        <div className="space-y-6">
          {news.length === 0 ? (
            <p className="text-xs text-slate-500 font-mono text-center py-10">No macroeconomic flash articles located. Modify criteria parameters.</p>
          ) : (
            news.map((item) => (
              <div key={item._id} className="bg-[#08080d] border border-white/5 rounded-2xl p-5 hover:border-amber-500/20 transition-all space-y-4">
                
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/5 pb-3">
                  <div className="flex flex-wrap items-center gap-1.5">
                    {getSentimentBadge(item.sentiment)}
                    {item.isFlashAlert && (
                      <span className="bg-red-500 text-white text-[8px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full select-none animate-pulse">
                        FLASH INDICATOR ALERT
                      </span>
                    )}
                    <Badge variant={item.importance === 'High' ? 'red' : item.importance === 'Medium' ? 'amber' : 'gray'}>
                      {item.importance} Impact Target
                    </Badge>
                  </div>

                  <span className="text-[11px] font-mono text-slate-500">
                    Source: {item.source} | {new Date(item.publishedAt).toLocaleDateString()}
                  </span>
                </div>

                <div className="space-y-2">
                  <h3 className="text-base font-extrabold text-[#f8fafc] leading-snug">{item.title}</h3>
                  <p className="text-xs sm:text-sm text-slate-400 leading-relaxed font-normal">{item.summary}</p>
                </div>

                {/* Cover full article text content */}
                {item.content && (
                  <div className="p-4 bg-[#11111a]/50 rounded-xl border border-white/5 text-xs text-slate-400 space-y-2">
                    <p className="whitespace-pre-line leading-relaxed font-normal">{item.content}</p>
                  </div>
                )}

                <div className="flex flex-wrap items-center justify-between gap-4 pt-2 text-[10px] text-slate-500 font-mono">
                  <div className="flex flex-wrap gap-1.5 items-center">
                    <span>Impacts Assets:</span>
                    {item.assetClassTags?.map((asst) => (
                      <span key={asst} className="bg-white/5 px-2 py-0.5 rounded border border-white/5 text-slate-300 font-bold uppercase">{asst}</span>
                    ))}
                  </div>

                  <span>Audited by Falcon Intelligence Desk</span>
                </div>

              </div>
            ))
          )}
        </div>
      )}

    </div>
  );
};
