import React, { useState, useEffect } from 'react';
import { apiService } from '../utils/api';
import { setSeo } from '../utils/seo';
import { Spinner } from '../components/ui/Spinner';
import { Badge } from '../components/ui/Badge';
import { 
  Activity, 
  RefreshCw, 
  TrendingUp, 
  ArrowRight, 
  HelpCircle, 
  Flame, 
  Filter, 
  VolumeX,
  LineChart
} from 'lucide-react';

/**
 * Advanced Interactive TradingView Chart Canvas Embed
 * Plugs directly into live exchange feeds on TradingView, mapping real-time pricing and full analysis tools.
 */
export const TradingViewChart = ({ symbol = 'BTCUSDT', theme = 'dark' }) => {
  let formattedSymbol = symbol;

  // Translate symbols appropriately so TradingView loads the correct feed instantly
  if (symbol.includes('USDT')) {
    formattedSymbol = `BINANCE:${symbol}`;
  } else if (symbol === 'EURUSD' || symbol === 'GBPUSD' || symbol === 'USDJPY' || symbol === 'AUDUSD') {
    formattedSymbol = `FX:${symbol}`;
  } else if (symbol === 'XAUUSD' || symbol === 'XAGUSD' || symbol === 'USOIL') {
    formattedSymbol = `OANDA:${symbol}`;
  } else {
    // AAPL, TSLA, NVDA, GOOG, MSFT
    formattedSymbol = `NASDAQ:${symbol}`;
  }

  const iframeSrc = `https://s.tradingview.com/widgetembed/?symbol=${encodeURIComponent(formattedSymbol)}&theme=${theme}&style=1&timezone=exchange&withdateranges=true&hide_side_toolbar=false&allow_symbol_change=true&saveimage=1&studies=%5B%5D`;

  return (
    <div className="w-full h-[450px] bg-[#0c0c14] border border-white/5 rounded-2xl overflow-hidden relative shadow-2xl transition-all duration-300">
      <div className="absolute top-3 left-4 z-10 flex items-center space-x-2 bg-[#050510]/95 backdrop-blur border border-white/10 px-3.5 py-1.5 rounded-xl text-[10px] font-mono text-amber-400 font-extrabold uppercase select-none tracking-widest shadow-lg">
        <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse"></span>
        <span>Interactive Chart Canvas &bull; {symbol}</span>
      </div>
      <iframe
        id={`tv-widget-${symbol}`}
        src={iframeSrc}
        title={`TradingView Advanced Chart for ${symbol}`}
        style={{ width: '100%', height: '100%', border: 'none' }}
        allowFullScreen
      />
    </div>
  );
};

export const Screener = () => {
  const [screenerItems, setScreenerItems] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [marketFilter, setMarketFilter] = useState('All');
  const [refreshCount, setRefreshCount] = useState(0);

  // Live charting linkage
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT');

  // Robust Search & Indicator State Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [minBullishScore, setMinBullishScore] = useState(0);
  const [rsiStateFilter, setRsiStateFilter] = useState('All'); // All, Oversold, Overbought, Neutral
  const [macdSignalFilter, setMacdSignalFilter] = useState('All'); // All, Bullish, Bearish
  const [emaTrendFilter, setEmaTrendFilter] = useState('All'); // All, Bullish, Bearish

  useEffect(() => {
    setSeo({
  title: `${fetchedInd.name} — Review, Parameters, and Audits | FalconSpido`,
  description: fetchedInd.description || `${fetchedInd.name} reviews, parameters, and trust score on FalconSpido.`,
  path: `/indicators/${fetchedInd.slug}`
});

    const fetchScreener = async () => {
      setIsLoading(true);
      try {
        const filterParam = marketFilter === 'All' ? undefined : marketFilter;
        const res = await apiService.getScreenerData(filterParam);
        if (res?.success) {
          setScreenerItems(res.data);
          // Auto-select first element from the new filter set if current selected active isn't in it
          const matchExists = res.data.some(it => it.symbol === selectedSymbol);
          if (!matchExists && res.data.length > 0) {
            setSelectedSymbol(res.data[0].symbol);
          }
        }
      } catch (err) {
        console.error('Failed to get technical screener results:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchScreener();
  }, [marketFilter, refreshCount]);

  // Automated pricing ticker update loop
  useEffect(() => {
    const timer = setInterval(() => {
      setRefreshCount(prev => prev + 1);
    }, 15000); // 15s updates to avoid rapid jitter on chart context
    return () => clearInterval(timer);
  }, []);

  const getScreenerBadge = (recom) => {
    switch (recom) {
      case 'Strong Buy':
        return <Badge variant="green">Strong Buy</Badge>;
      case 'Buy':
        return <Badge variant="green">Buy</Badge>;
      case 'Sell':
        return <Badge variant="red">Sell</Badge>;
      case 'Strong Sell':
        return <Badge variant="red">Strong Sell</Badge>;
      default:
        return <Badge variant="gray">Neutral</Badge>;
    }
  };

  const getRsiColor = (rsi) => {
    if (rsi >= 70) return 'text-rose-400 font-bold';
    if (rsi <= 30) return 'text-emerald-400 font-bold';
    return 'text-slate-300';
  };

  // Perform multi-stage interactive indicator screening
  const filteredScreenerItems = screenerItems.filter((item) => {
    // 1. Search filter
    if (searchTerm && !item.symbol.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }
    // 2. Minimum bullish percentage filter
    if (item.scoring.bullishPercent < minBullishScore) {
      return false;
    }
    // 3. RSI state filter
    if (rsiStateFilter !== 'All') {
      const rsiSig = item.indicators.rsi.signal?.toLowerCase() || '';
      if (rsiStateFilter === 'Oversold' && !rsiSig.includes('oversold') && item.indicators.rsi.value > 30) return false;
      if (rsiStateFilter === 'Overbought' && !rsiSig.includes('overbought') && item.indicators.rsi.value < 70) return false;
      if (rsiStateFilter === 'Neutral' && (item.indicators.rsi.value <= 30 || item.indicators.rsi.value >= 70)) return false;
    }
    // 4. MACD Signal cross filter
    if (macdSignalFilter !== 'All') {
      const macdSig = item.indicators.macd.signal?.toLowerCase() || '';
      if (macdSignalFilter === 'Bullish' && !macdSig.includes('bullish')) return false;
      if (macdSignalFilter === 'Bearish' && !macdSig.includes('bearish')) return false;
    }
    // 5. EMA trend bias filter
    if (emaTrendFilter !== 'All') {
      if (item.indicators.ema200Status !== emaTrendFilter) return false;
    }

    return true;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <span className="text-[10px] text-amber-500 uppercase tracking-widest font-extrabold flex items-center space-x-1">
            <Activity className="h-4.5 w-4.5 animate-pulse text-amber-500" />
            <span>Real-time Momentum Scanner & Charting Desk</span>
          </span>
          <h1 className="text-xl sm:text-3xl font-black text-white">Interactive Technical Screener</h1>
          <p className="text-xs text-slate-400 max-w-xl">
            Live evaluation matrix calculating momentum indexes, EMA trend deviations, and Bollinger ranges continuously. Click any asset line to lock its live charting canvas.
          </p>
        </div>

        <button 
          onClick={() => setRefreshCount(prev => prev + 1)}
          className="flex items-center space-x-1.5 bg-[#12121a] hover:bg-[#1a1a26] border border-white/5 hover:border-white/10 px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:text-white transition-all select-none"
        >
          <RefreshCw className="h-4 w-4 text-amber-500" />
          <span>Manual Refilter</span>
        </button>
      </div>

      {/* Filter Toggles Bar */}
      <div className="flex flex-wrap items-center gap-2 border-b border-white/5 pb-4">
        {['All', 'Crypto', 'Forex', 'Commodities', 'Stocks'].map((mkt) => (
          <button
            key={mkt}
            onClick={() => setMarketFilter(mkt)}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold border transition-colors leading-none ${
              marketFilter === mkt 
                ? 'bg-amber-500/10 border-amber-500/20 text-amber-400' 
                : 'bg-[#101017] border-white/5 text-slate-400 hover:text-white'
            }`}
          >
            {mkt} Market
          </button>
        ))}

        <div className="ml-auto text-[10px] font-mono text-slate-500 flex items-center space-x-2">
          <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>Automatic cycle updates: 15s interval</span>
        </div>
      </div>

      {/* Real-time Multi-exchange Advanced Chart Embed */}
      <div className="animate-fade-in">
        <TradingViewChart symbol={selectedSymbol} />
      </div>

      {/* Advanced Indicators Filtration Dashboard */}
      <div className="bg-[#0b0b14] border border-white/5 p-5 rounded-2xl grid grid-cols-1 md:grid-cols-5 gap-4 text-xs font-mono">
        {/* Search */}
        <div className="space-y-1.5">
          <label className="text-slate-400 font-bold block">Quick Search Ticker</label>
          <input
            type="text"
            placeholder="e.g. BTCUSDT..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#11111a] border border-white/5 text-slate-300 rounded-lg p-2 focus:outline-none focus:border-amber-500"
          />
        </div>

        {/* Min Bullish Index Score */}
        <div className="space-y-1.5">
          <div className="flex justify-between">
            <label className="text-slate-400 font-bold">Min Bullish Score</label>
            <span className="text-amber-500 font-extrabold">{minBullishScore}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            value={minBullishScore}
            onChange={(e) => setMinBullishScore(parseInt(e.target.value))}
            className="w-full h-2 accent-amber-500 bg-white/5 rounded-lg appearance-none cursor-pointer mt-1"
          />
        </div>

        {/* RSI levels */}
        <div className="space-y-1.5">
          <label className="text-slate-400 font-bold block">RSI Oscillator Class</label>
          <select
            value={rsiStateFilter}
            onChange={(e) => setRsiStateFilter(e.target.value)}
            className="w-full bg-[#11111a] border border-white/5 text-slate-300 rounded-lg p-2 focus:outline-none"
          >
            <option value="All">All Momentum Ranges</option>
            <option value="Oversold">Oversold Only (RSI &le; 30)</option>
            <option value="Overbought">Overbought Only (RSI &ge; 70)</option>
            <option value="Neutral">Neutral Ranges (30 &lt; RSI &lt; 70)</option>
          </select>
        </div>

        {/* MACD signals */}
        <div className="space-y-1.5">
          <label className="text-slate-400 font-bold block">MACD Signal Crossover</label>
          <select
            value={macdSignalFilter}
            onChange={(e) => setMacdSignalFilter(e.target.value)}
            className="w-full bg-[#11111a] border border-white/5 text-slate-300 rounded-lg p-2 focus:outline-none"
          >
            <option value="All">All MACD Crossovers</option>
            <option value="Bullish">Bullish Cross Status</option>
            <option value="Bearish">Bearish Cross Status</option>
          </select>
        </div>

        {/* EMA Trend bias */}
        <div className="space-y-1.5">
          <label className="text-slate-400 font-bold block">EMA 200 Daily Trend</label>
          <select
            value={emaTrendFilter}
            onChange={(e) => setEmaTrendFilter(e.target.value)}
            className="w-full bg-[#11111a] border border-white/5 text-slate-300 rounded-lg p-2 focus:outline-none"
          >
            <option value="All">All Trend Regimes</option>
            <option value="Bullish">Bullish Index Only</option>
            <option value="Bearish">Bearish Index Only</option>
          </select>
        </div>
      </div>

      {/* Main Grid display table */}
      {isLoading && screenerItems.length === 0 ? (
        <div className="py-20 flex flex-col items-center">
          <Spinner size="lg" />
          <p className="text-xs text-slate-500 font-mono mt-3">Compiling algorithmic calculations matrices...</p>
        </div>
      ) : filteredScreenerItems.length === 0 ? (
        <div className="text-center py-20 border border-dashed border-white/5 rounded-2xl bg-[#08080d]">
          <p className="text-xs text-slate-500 font-mono">No asset classes map onto current indicator filters. Broaden your values.</p>
        </div>
      ) : (
        <div className="bg-[#08080d] border border-white/5 rounded-2xl overflow-hidden shadow-2xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300 font-mono border-collapse">
              <thead>
                <tr className="border-b border-white/5 bg-[#0c0c14] text-[#94a3b8] text-[9px] uppercase tracking-wider select-none">
                  <th className="py-4 px-5 font-bold">Instrument Symbol</th>
                  <th className="py-4 px-5 font-bold">Action Signal</th>
                  <th className="py-4 px-5 font-bold">RSI (14)</th>
                  <th className="py-4 px-5 font-bold">MACD Cross</th>
                  <th className="py-4 px-5 font-bold">Bollinger Range</th>
                  <th className="py-4 px-5 font-bold text-center">EMA (200) Trend</th>
                  <th className="py-4 px-5 font-bold text-right">Bullish Index Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 leading-relaxed">
                {filteredScreenerItems.map((scr) => (
                  <tr 
                    key={scr.symbol} 
                    onClick={() => setSelectedSymbol(scr.symbol)}
                    className={`cursor-pointer transition-colors ${
                      selectedSymbol === scr.symbol 
                        ? 'bg-amber-500/10 hover:bg-amber-500/15 font-black text-amber-400' 
                        : 'hover:bg-white/5'
                    }`}
                  >
                    <td className="py-4 px-5 font-black text-white text-[13px] flex items-center space-x-2">
                      <LineChart className={`h-3.5 w-3.5 ${selectedSymbol === scr.symbol ? 'text-amber-400 animate-pulse' : 'text-slate-500'}`} />
                      <span>{scr.symbol}</span>
                    </td>
                    <td className="py-4 px-5">{getScreenerBadge(scr.scoring.recommendation)}</td>
                    <td className="py-4 px-5">
                      <div className="space-y-0.5">
                        <span className={getRsiColor(scr.indicators.rsi.value)}>
                          {scr.indicators.rsi.value.toFixed(1)}
                        </span>
                        <span className="block text-[8px] text-slate-500 uppercase">
                          ({scr.indicators.rsi.signal})
                        </span>
                      </div>
                    </td>
                    <td className="py-4 px-5">
                      <div className="space-y-0.5">
                        <span className={scr.indicators.macd.histogram >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                          {scr.indicators.macd.histogram >= 0 ? '+' : ''}
                          {scr.indicators.macd.histogram.toFixed(4)}
                        </span>
                        <span className="block text-[8px] text-slate-500 uppercase">
                          {scr.indicators.macd.signal}
                        </span>
                      </div>
                    </td>
                    <td className="py-4 px-5 text-slate-400 text-[11px]">
                      {scr.indicators.bollinger.signal}
                    </td>
                    <td className="py-4 px-5 text-center">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        scr.indicators.ema200Status === 'Bullish' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                      }`}>
                        {scr.indicators.ema200Status}
                      </span>
                    </td>
                    <td className="py-4 px-5 text-right font-bold">
                      <div className="flex items-center justify-end space-x-2">
                        <span className="font-extrabold text-slate-200">
                          {scr.scoring.bullishPercent}%
                        </span>
                        <div className="h-1.5 w-12 bg-white/5 rounded-full overflow-hidden">
                          <div 
                            className={`h-full ${scr.scoring.bullishPercent >= 55 ? 'bg-emerald-400' : 'bg-rose-400'}`}
                            style={{ width: `${scr.scoring.bullishPercent}%` }}
                          ></div>
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Guide explanation widget */}
      <div className="bg-gradient-to-tr from-[#10101b] to-[#0a0a10] border border-white/5 p-6 rounded-2xl grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="space-y-1.5 p-1">
          <h4 className="text-xs font-bold text-slate-200 flex items-center space-x-1">
            <span>RSI Momentum Oscillations</span>
          </h4>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Values &ge;70 denote overbought regimes, indicating potential short exhaustion. Values &le;30 represent oversold states supporting reversal entries.
          </p>
        </div>
        <div className="space-y-1.5 p-1 border-t md:border-t-0 md:border-l border-white/5 md:pl-6">
          <h4 className="text-xs font-bold text-slate-200 flex items-center space-x-1">
            <span>Trend Confirmation EMA 200</span>
          </h4>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Assets holding above the EMA 200 daily average signal structured long dominance. Trading beneath validates structural downtrend short regimes.
          </p>
        </div>
        <div className="space-y-1.5 p-1 border-t md:border-t-0 md:border-l border-white/5 md:pl-6">
          <h4 className="text-xs font-bold text-slate-200 flex items-center space-x-1">
            <span>Bollinger Ranges Volatility</span>
          </h4>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Band squeezes indicate tight consolidating distributions, preceding dynamic volatility breakthrough breakout spikes.
          </p>
        </div>
      </div>

    </div>
  );
};
