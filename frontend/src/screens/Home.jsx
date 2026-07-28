import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiService } from '../utils/api';
import { setSeo } from '../utils/seo';
import { StarRating } from '../components/ui/StarRating';
import { Badge } from '../components/ui/Badge';
import { useApp } from '../context/AppContext';
import { 
  Flame, 
  Zap, 
  Award, 
  HelpCircle, 
  TrendingUp, 
  Search, 
  PlusCircle, 
  Layers, 
  Cpu, 
  ShieldCheck, 
  BookOpen, 
  ChevronRight, 
  ArrowUpRight, 
  ExternalLink,
  MessageSquareCode
} from 'lucide-react';

export const Home = () => {
  const [trending, setTrending] = useState([]);
  const [featured, setFeatured] = useState([]);
  const [recentNews, setRecentNews] = useState([]);
  const [stats, setStats] = useState(null);
  const [prices, setPrices] = useState({});
  const [searchQuery, setSearchQuery] = useState('');
  const { categories, platforms } = useApp();
  const navigate = useNavigate();

  useEffect(() => {
    // Set Document SEO Title
    setSeo({
  title: "FalconSpido — Elite Trading Indicators, EAs, Bots & TradingView Scripts 2026",
  description: "Discover, compare, and audit elite retail trading indicators, EAs, and quant strategies. Everything on single Platform.",
  path: "/"
});

    const fetchHomeData = async () => {
      try {
        const [trendRes, statsRes, newsRes, pricesRes] = await Promise.all([
          apiService.getTrending(),
          apiService.getStats(),
          apiService.getMarketNews({ limits: 3 }),
          apiService.getLivePrices()
        ]);

        if (trendRes?.success) {
          setTrending(trendRes.data.slice(0, 5));
          setFeatured(trendRes.data.filter(i => i.isFeatured).slice(0, 4));
        }
        if (statsRes?.success) setStats(statsRes.data);
        if (newsRes?.success) setRecentNews(newsRes.data);
        if (pricesRes?.success) setPrices(pricesRes.data);
      } catch (err) {
        console.error('Failed to pre-fetch landing analytics:', err);
      }
    };
    fetchHomeData();

    // Setup micro price interval updates for active ticker ticks
    const interval = setInterval(async () => {
      try {
        const pricesRes = await apiService.getLivePrices();
        if (pricesRes?.success) setPrices(pricesRes.data);
      } catch (err) {
        // silent error
      }
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/indicators?search=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  const tradingTickerPairs = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'EURUSD', 'GBPUSD', 'XAUUSD'];

  return (
    <div className="space-y-16 pb-16">
      
      {/* Dynamic price strip */}
      <div className="w-full bg-[#07070a] border-b border-white/5 py-2.5 overflow-hidden select-none">
        <div className="max-w-7xl mx-auto px-4 flex items-center justify-between gap-6 overflow-x-auto scrollbar-none text-[11px] font-mono">
          <div className="flex items-center space-x-2 text-slate-500 uppercase tracking-wider text-[9px] font-bold">
            <span className="h-1.5 w-1.5 rounded-full bg-[#22c55e] animate-ping"></span>
            <span>Live Feed</span>
          </div>
          <div className="flex items-center space-x-8">
            {tradingTickerPairs.map((pair) => {
              const tick = prices[pair];
              if (!tick) return null;
              const isBull = tick.changePercent >= 0;
              return (
                <div key={pair} className="flex items-center space-x-2 flex-shrink-0">
                  <span className="text-slate-300 font-medium">{tick.symbol.replace('USDT', '')}</span>
                  <span className="text-slate-200 font-bold">{tick.price.toFixed(tick.price > 1000 ? 2 : 4)}</span>
                  <span className={`font-semibold ${isBull ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {isBull ? '+' : ''}{tick.changePercent}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Cinematic Hero */}
      <section className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-10 text-center">
        {/* Background ambient lighting */}
        <div className="absolute top-[-100px] left-1/2 -translate-x-1/2 w-[350px] sm:w-[600px] h-[350px] bg-amber-500/10 blur-[100px] rounded-full pointer-events-none"></div>

        <div className="space-y-6 max-w-4xl mx-auto relative z-10">
          <div className="inline-flex items-center space-x-2 bg-amber-500/10 border border-amber-500/20 px-3 py-1 rounded-full text-[10px] sm:text-xs font-semibold text-amber-400 uppercase tracking-widest leading-none">
            <Award className="h-3.5 w-3.5" />
            <span>THE LEADING ALPHA RESOURCE MATRIX FOR TRADERS</span>
          </div>

          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-black text-white leading-[1.1] tracking-tight">
            Discover Elite Trading <span className="bg-gradient-to-r from-amber-400 to-amber-200 bg-clip-text text-transparent">Indicators</span> & EAs
          </h1>

          <p className="text-sm sm:text-base text-slate-400 max-w-2xl mx-auto leading-relaxed">
            FalconSpido brings transparent, audited analytical insights to your desk. Navigate backtest ratings, verify custom presets, avoid scam models, and execute high-fidelity risks calculations.
          </p>

          {/* Majestic Hero Search Bar */}
          <form onSubmit={handleSearchSubmit} className="max-w-2xl mx-auto relative pt-4">
            <input
              type="text"
              placeholder="Search strategy codes, MT5 bots, TradingView alerts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#10101b]/90 border border-white/10 rounded-xl py-3.5 sm:py-4 pl-12 pr-32 text-xs sm:text-sm text-slate-200 shadow-xl shadow-black/80 focus:outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 transition-all font-medium"
            />
            <Search className="absolute left-4.5 top-8.5 sm:top-9 h-5 w-5 text-slate-500" />
            <button
              type="submit"
              className="absolute right-2 top-6 sm:top-6.5 bg-amber-500 hover:bg-amber-400 text-black py-2.5 px-5 sm:px-6 rounded-lg text-xs font-extrabold shadow-md shadow-amber-500/15 tracking-wide transition-all"
            >
              FIND ALPHA
            </button>
          </form>

          {/* Quick Platform chips */}
          <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-extrabold mr-1">Supported platforms:</span>
            {platforms.slice(0, 5).map((plat) => (
              <Link 
                key={plat._id} 
                to={`/indicators?platform=${plat._id}`}
                className="bg-[#12121e] border border-white/5 px-2.5 py-1 rounded-md text-[10px] font-mono text-slate-400 hover:text-white hover:border-amber-500/30 transition-all"
              >
                {plat.name}
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Stats Dashboard */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 bg-[#0d0d14] border border-white/5 rounded-2xl p-6 shadow-2xl">
          <div className="text-center space-y-1">
            <div className="text-slate-500 font-bold uppercase tracking-widest text-[9px]">Screener Matrix</div>
            <div className="text-xl sm:text-3xl font-extrabold text-white font-mono">18+ Ass.</div>
            <p className="text-[10px] text-slate-400">Crypto, Forex equities</p>
          </div>
          <div className="text-center space-y-1 border-l border-white/5">
            <div className="text-slate-500 font-bold uppercase tracking-widest text-[9px]">Total Listed scripts</div>
            <div className="text-xl sm:text-3xl font-extrabold text-white font-mono">
              {stats?.totalIndicators || 30}+
            </div>
            <p className="text-[10px] text-slate-400">EAs, Bots & Indicators</p>
          </div>
          <div className="text-center space-y-1 border-l border-white/5">
            <div className="text-slate-500 font-bold uppercase tracking-widest text-[9px]">System trust index</div>
            <div className="text-xl sm:text-3xl font-extrabold text-emerald-400 font-mono">
              {stats?.avgRating?.toFixed(1) || '4.6'} ★
            </div>
            <p className="text-[10px] text-slate-400">Community audits verified</p>
          </div>
          <div className="text-center space-y-1 border-l border-white/5">
            <div className="text-slate-500 font-bold uppercase tracking-widest text-[9px]">Calculated Free access</div>
            <div className="text-xl sm:text-3xl font-extrabold text-amber-500 font-mono">
              {stats?.totalFree || 8} tools
            </div>
            <p className="text-[10px] text-slate-400">Zero subscription fees</p>
          </div>
        </div>
      </section>

      {/* Featured Slide Deck / Grid */}
      {featured.length > 0 && (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-[10px] text-amber-500 uppercase tracking-widest font-extrabold flex items-center space-x-1">
                <Award className="h-3.5 w-3.5" />
                <span>Premium Spotlights</span>
              </span>
              <h2 className="text-lg sm:text-2xl font-black text-white">Elite Verified Publications</h2>
            </div>
            <Link to="/indicators?pinned=true" className="text-xs font-semibold text-slate-400 hover:text-amber-500 flex items-center space-x-1 transition-all">
              <span>View All Featured</span>
              <ChevronRight className="h-4 w-4 text-slate-400" />
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {featured.map(item => (
              <div key={item._id} className="relative rounded-xl border border-amber-500/15 bg-gradient-to-tr from-[#0a0a14] to-[#121226] p-4 group hover:border-amber-400 hover:bg-gradient-to-tr hover:from-[#0d0d1a] hover:to-[#171733] transition-all flex flex-col justify-between">
                <span className="absolute top-2 right-2 text-[8px] bg-amber-500 text-black px-1.5 py-0.5 rounded font-bold uppercase tracking-wider">Premium</span>
                <div className="space-y-2">
                  <span className="text-[9px] text-slate-500 font-mono flex items-center space-x-1">
                    <Cpu className="h-3 w-3 text-slate-400" />
                    <span>{item.listingType}</span>
                  </span>
                  <Link to={`/indicators/${item.slug}`} className="block">
                    <h3 className="text-sm font-bold text-white group-hover:text-amber-400 transition-colors duration-150 line-clamp-1">{item.name}</h3>
                  </Link>
                  <p className="text-[11px] text-slate-400 line-clamp-2 h-8 leading-relaxed mb-4">{item.description}</p>
                </div>
                <div className="flex items-center justify-between text-[10px] font-mono border-t border-white/5 pt-3 mt-4">
                  <span className="text-emerald-400 font-bold">{item.backtestData?.winRate}% Win</span>
                  <Link to={`/indicators/${item.slug}`} className="text-[#a78bfa] hover:underline flex items-center space-x-0.5">
                    <span>Audit Data</span>
                    <ArrowUpRight className="h-3 w-3" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Trending & Multi-Screener Split */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          
          {/* Trending column (Left 4 cols) */}
          <div className="lg:col-span-5 bg-[#08080c] border border-white/5 rounded-2xl p-5 space-y-5 shadow-xl">
            <h3 className="text-md sm:text-lg font-black text-white flex items-center space-x-2">
              <Flame className="h-5 w-5 text-amber-500 select-none" />
              <span>Trending Indicators 🔥</span>
            </h3>
            
            <div className="space-y-4">
              {trending.map((item, index) => (
                <div key={item._id} className="flex items-start space-x-3.5 bg-white/5 border border-white/5 hover:border-amber-500/20 rounded-xl p-3 hover:bg-[#0c0c16] transition-all">
                  <div className="h-7 w-7 rounded-lg bg-[#141421] text-amber-400 border border-white/10 flex items-center justify-center font-mono font-bold text-xs">
                    #{index + 1}
                  </div>
                  <div className="flex-grow space-y-1">
                    <Link to={`/indicators/${item.slug}`} className="block">
                      <h4 className="text-xs font-bold text-slate-100 hover:text-amber-400 transition-all truncate max-w-[200px]">
                        {item.name}
                      </h4>
                    </Link>
                    <div className="flex items-center space-x-2 text-[10px] text-slate-500 font-mono">
                      <span>{item.listingType}</span>
                      <span>•</span>
                      <span className="text-amber-500 font-bold">{item.backtestData?.winRate || 64}% WR</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] font-mono text-slate-400 block font-bold">{item.isFree ? 'FREE' : `$${item.price}`}</span>
                    <span className="text-[8px] text-slate-500 uppercase tracking-widest">{item.pricingModel}</span>
                  </div>
                </div>
              ))}
            </div>
            <Link to="/indicators" className="block text-center text-xs font-bold text-amber-500 hover:text-amber-400 hover:underline pt-2">
              View All 30+ Active Tools
            </Link>
          </div>

          {/* Interactive Screen Preview */}
          <div className="lg:col-span-7 bg-[#0b0b11] border border-[#1b1b22] rounded-2xl p-6 space-y-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="space-y-1">
                <span className="text-[10px] text-emerald-400 uppercase tracking-widest font-extrabold flex items-center space-x-1">
                  <Zap className="h-3.5 w-3.5" />
                  <span>Interactive Screener Core</span>
                </span>
                <h3 className="text-md sm:text-lg font-black text-white">Algorithmic Technical Grid</h3>
              </div>
              <Link 
                to="/screener" 
                className="bg-white/5 border border-white/5 hover:border-amber-500 hover:bg-[#141421] text-xs font-bold px-3.5 py-1.5 rounded-lg text-slate-300 hover:text-white transition-all flex items-center space-x-1"
              >
                <span>Launch Full Screener Console</span>
                <ChevronRight className="h-4 w-4 text-slate-500" />
              </Link>
            </div>

            <p className="text-[11px] text-slate-400 leading-relaxed">
              Programs screen active momentum deviations continuously. Analyze RSI targets, MACD crossovers, and dynamic buy/sell suggestions calculated using Falcon algorithms.
            </p>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-[11px] font-mono">
                <thead>
                  <tr className="border-b border-white/5 text-slate-500">
                    <th className="pb-2.5 font-bold uppercase tracking-wider text-[9px]">Symbol</th>
                    <th className="pb-2.5 font-bold uppercase tracking-wider text-[9px]">Signal</th>
                    <th className="pb-2.5 font-bold uppercase tracking-wider text-[9px]">RSI</th>
                    <th className="pb-2.5 font-bold uppercase tracking-wider text-[9px]">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-slate-300">
                  <tr className="hover:bg-white/5 font-mono">
                    <td className="py-2.5 font-bold text-white">BTCUSDT</td>
                    <td className="py-2.5 text-emerald-400">Bullish Momentum</td>
                    <td className="py-2.5">64.0 (Neutral)</td>
                    <td className="py-2.5"><Badge variant="green">Strong Buy</Badge></td>
                  </tr>
                  <tr className="hover:bg-white/5 font-mono">
                    <td className="py-2.5 font-bold text-white">TSLA</td>
                    <td className="py-2.5 text-emerald-400">Oversold rebound</td>
                    <td className="py-2.5 text-emerald-400">19.0 (Oversold)</td>
                    <td className="py-2.5"><Badge variant="amber">Buy</Badge></td>
                  </tr>
                  <tr className="hover:bg-white/5 font-mono">
                    <td className="py-2.5 font-bold text-white">EURUSD</td>
                    <td className="py-2.5 text-slate-400">Sideways drift</td>
                    <td className="py-2.5 font-bold">51.0 (Neutral)</td>
                    <td className="py-2.5"><Badge variant="gray">Hold</Badge></td>
                  </tr>
                  <tr className="hover:bg-white/5 font-mono">
                    <td className="py-2.5 font-bold text-white">NVDA</td>
                    <td className="py-2.5 text-rose-400">Bearish divergence</td>
                    <td className="py-2.5 text-rose-400">84.0 (Overbought)</td>
                    <td className="py-2.5"><Badge variant="red">Strong Sell</Badge></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      {/* Categories block */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        <h2 className="text-xl sm:text-2xl font-black text-white text-center">Quantify by Specialization</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {categories.slice(0, 8).map((cat) => (
            <Link 
              key={cat._id} 
              to={`/indicators?category=${cat._id}`}
              className="bg-[#08080c] border border-white/5 rounded-xl p-4 hover:border-amber-500/20 hover:bg-[#0c0c16] transition-all flex items-center space-x-3 shadow-md"
            >
              <div className="h-10 w-10 text-lg rounded-lg bg-white/5 flex items-center justify-center font-bold">
                {cat.icon}
              </div>
              <div>
                <h4 className="text-xs font-bold text-white tracking-wide">{cat.name}</h4>
                <p className="text-[10px] text-slate-500 mt-0.5">{cat.itemCount || 0} tools catalogued</p>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* Regulated Broker partners */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 bg-[#09090e] border border-white/5 rounded-2xl p-6 sm:p-8 space-y-6 relative overflow-hidden shadow-2xl">
        <div className="space-y-1 text-center sm:text-left relative z-10">
          <span className="text-[10px] text-amber-500 uppercase tracking-widest font-extrabold font-bold">Liquidity gateways</span>
          <h2 className="text-xl sm:text-2xl font-black text-white">Regulated Trading Brokers</h2>
          <p className="text-xs text-slate-400 max-w-xl">
            Execute your automated bots on tier-1 regulated broker feeds. High-speed connectivity helps eliminate slippage and spread leaks.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative z-10 pt-4">
          <div className="bg-[#12121a] p-5 rounded-xl border border-white/5 flex flex-col justify-between hover:border-white/10 transition-all">
            <div className="space-y-2">
              <h4 className="text-sm font-bold text-white">IC Markets</h4>
              <p className="text-xs text-slate-400">Raw Spreads model. Regulated by ASIC and CySEC. Ideal for high-frequency EAs.</p>
              <div className="flex flex-wrap gap-1 pt-1">
                <Badge variant="blue">MT4/MT5</Badge>
                <Badge variant="blue">cTrader</Badge>
              </div>
            </div>
            <a 
              href="https://icmarkets.com" 
              target="_blank" 
              rel="noopener noreferrer" 
              className="mt-6 flex items-center justify-center space-x-1 bg-amber-500 hover:bg-amber-400 text-black py-2 rounded-lg font-bold text-xs"
            >
              <span>Verify Spreads</span>
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>

          <div className="bg-[#12121a] p-5 rounded-xl border border-white/5 flex flex-col justify-between hover:border-white/10 transition-all">
            <div className="space-y-2">
              <h4 className="text-sm font-bold text-white">Exness</h4>
              <p className="text-xs text-slate-400">Micro deposits starting at $10. Maximum leverage scaling configs. Regulated by FCA.</p>
              <div className="flex flex-wrap gap-1 pt-1">
                <Badge variant="blue">Forex</Badge>
                <Badge variant="blue">Gold</Badge>
              </div>
            </div>
            <a 
              href="https://exness.com" 
              target="_blank" 
              rel="noopener noreferrer" 
              className="mt-6 flex items-center justify-center space-x-1 bg-amber-500 hover:bg-amber-400 text-black py-2 rounded-lg font-bold text-xs"
            >
              <span>Explore Spreads</span>
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>

          <div className="bg-[#12121a] p-5 rounded-xl border border-white/5 flex flex-col justify-between hover:border-white/10 transition-all">
            <div className="space-y-2">
              <h4 className="text-sm font-bold text-white">Bybit</h4>
              <p className="text-xs text-slate-400">The premier platform for high-volatility cryptocurrency options, scalp indicators, and grid bots.</p>
              <div className="flex flex-wrap gap-1 pt-1">
                <Badge variant="green">VIP rebates</Badge>
                <Badge variant="blue">Crypto APIs</Badge>
              </div>
            </div>
            <a 
              href="https://bybit.com" 
              target="_blank" 
              rel="noopener noreferrer" 
              className="mt-6 flex items-center justify-center space-x-1 bg-amber-500 hover:bg-amber-400 text-black py-2 rounded-lg font-bold text-xs"
            >
              <span>Claim Rebates</span>
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>
      </section>

      {/* Latest macro insights */}
      {recentNews.length > 0 && (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg sm:text-2xl font-black text-white">Falcon Intelligence Newsroom</h2>
            <Link to="/news" className="text-xs font-semibold text-amber-500 hover:underline">
              View Newsroom Feed
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {recentNews.map(item => (
              <div key={item._id} className="relative rounded-xl border border-white/5 bg-[#0a0a10] p-4 group hover:border-[#37374a] transition-all flex flex-col justify-between h-full">
                <div className="space-y-2.5">
                  <div className="flex items-center justify-between text-[9px] font-mono text-slate-500">
                    <span>{item.source}</span>
                    <span className={item.sentiment === 'Bullish' ? 'text-emerald-400' : item.sentiment === 'Bearish' ? 'text-rose-400' : 'text-slate-400'}>
                      {item.sentiment}
                    </span>
                  </div>
                  <Link to={`/news`} className="block">
                    <h3 className="text-xs sm:text-sm font-bold text-white group-hover:text-amber-400 transition-colors duration-150 line-clamp-2 leading-snug">
                      {item.title}
                    </h3>
                  </Link>
                  <p className="text-[11px] text-slate-400 line-clamp-3 leading-relaxed">
                    {item.summary}
                  </p>
                </div>
                {item.symbolsAffected && item.symbolsAffected.length > 0 && (
                  <div className="flex gap-1 pt-4 text-[9px] font-mono font-bold text-amber-500">
                    <span>Impacts:</span>
                    {item.symbolsAffected.map((sym, i) => (
                      <span key={i} className="bg-white/5 px-1.5 rounded text-slate-300">{sym}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Final Submit CTA Banner */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-gradient-to-tr from-[#120f01] via-[#101017] to-[#040407] rounded-3xl border border-amber-500/20 p-8 sm:p-12 text-center space-y-6 relative overflow-hidden">
          {/* subtle radial decoration strip */}
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_bottom_left,rgba(245,158,11,0.06),transparent_50%)] pointer-events-none"></div>

          <h3 className="text-2xl sm:text-4xl font-black text-white leading-tight">
            Earn Volatility Revenue. List Your Custom Strategy.
          </h3>
          <p className="text-xs sm:text-sm text-slate-400 max-w-xl mx-auto leading-relaxed">
            Gain exposure among 450K+ targeted quant traders scanning falconspido.com daily. Share your backtest audits, configure presets, and build user trust indicators.
          </p>
          <div className="pt-4 flex justify-center">
            <Link 
              to="/submit" 
              className="flex items-center space-x-2 bg-amber-500 hover:bg-amber-400 text-black py-3 px-8 rounded-lg font-black text-sm shadow-xl shadow-amber-500/10 transition-all duration-150 transform hover:scale-[1.01]"
            >
              <PlusCircle className="h-5 w-5" />
              <span>LIST YOUR INDICATOR FREE</span>
            </Link>
          </div>
        </div>
      </section>

    </div>
  );
};
