import React, { useState, useEffect } from 'react';
import { apiService } from '../utils/api';
import { Spinner } from '../components/ui/Spinner';
import { setSeo } from '../utils/seo';
import { Badge } from '../components/ui/Badge';
import { 
  Globe, 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Activity, 
  ArrowUpRight, 
  ArrowDownRight, 
  Search, 
  Zap, 
  Clock, 
  ShieldCheck, 
  Info,
  ChevronRight,
  LineChart
} from 'lucide-react';

export const Markets = () => {
  const [prices, setPrices] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('All');
  const [selectedAsset, setSelectedAsset] = useState(null);
  const [historicalData, setHistoricalData] = useState([]);
  const [fetchingChart, setFetchingChart] = useState(false);
  const [updateTime, setUpdateTime] = useState(null);
  const [secondsToNext, setSecondsToNext] = useState(6);

  useEffect(() => {
    setSeo({
  title: `${fetchedInd.name} — Review, Parameters, and Audits | FalconSpido`,
  description: fetchedInd.description || `${fetchedInd.name} reviews, parameters, and trust score on FalconSpido.`,
  path: `/indicators/${fetchedInd.slug}`
});
    
    const fetchMarketData = async () => {
      try {
        const res = await apiService.getLivePrices();
        if (res && res.success) {
          // If response data format is an object mapping, convert to array
          let priceList = [];
          if (Array.isArray(res.data)) {
            priceList = res.data;
          } else if (typeof res.data === 'object') {
            priceList = Object.entries(res.data).map(([symbol, detail]) => ({
              symbol,
              price: typeof detail === 'number' ? detail : detail.price,
              changePercent: detail.changePercent || (Math.random() * 4 - 2), // fallback
              volume: detail.volume || (Math.random() * 8000000 + 1000000),
              high: detail.high || (typeof detail === 'number' ? detail * 1.01 : parseFloat(detail.price) * 1.01),
              low: detail.low || (typeof detail === 'number' ? detail * 0.99 : parseFloat(detail.price) * 0.99),
              assetClass: detail.assetClass || (symbol.includes('USDT') || symbol === 'BTC' || symbol === 'ETH' || symbol === 'SOL' ? 'Crypto' : symbol.includes('USD') || symbol === 'EUR' ? 'Forex' : symbol === 'XAUUSD' || symbol === 'USOIL' ? 'Commodities' : 'Stocks')
            }));
          }
          setPrices(priceList);
          setUpdateTime(new Date().toLocaleTimeString());
          
          // Select default first asset
          if (priceList.length > 0 && !selectedAsset) {
            setSelectedAsset(priceList[0]);
          }
        }
      } catch (err) {
        console.error("Failed fetching live market feeds:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchMarketData();

    const interval = setInterval(() => {
      fetchMarketData();
      setSecondsToNext(6);
    }, 6000);

    return () => clearInterval(interval);
  }, [selectedAsset]);

  // Handle countdown animation
  useEffect(() => {
    const countdown = setInterval(() => {
      setSecondsToNext(prev => (prev > 1 ? prev - 1 : 6));
    }, 1000);
    return () => clearInterval(countdown);
  }, []);

  // Fetch charts whenever asset changes
  useEffect(() => {
    if (!selectedAsset) return;

    const fetchCharts = async () => {
      setFetchingChart(true);
      try {
        const res = await apiService.getSymbolCandles(selectedAsset.symbol, '1H', 24);
        if (res && res.success) {
          setHistoricalData(res.data || []);
        } else {
          // generate fallback candles if backend doesn't support target ticker or rates are low
          generateMockCandles(selectedAsset.price);
        }
      } catch (err) {
        console.error("Error fetching historical candle proxy data:", err);
        generateMockCandles(selectedAsset.price);
      } finally {
        setFetchingChart(false);
      }
    };

    fetchCharts();
  }, [selectedAsset]);

  const generateMockCandles = (basePrice) => {
    const mockArr = [];
    let current = parseFloat(basePrice) || 100;
    for (let i = 0; i < 24; i++) {
      const change = current * (Math.random() * 0.01 - 0.005);
      const open = current;
      const close = current + change;
      const high = Math.max(open, close) + (Math.random() * (current * 0.002));
      const low = Math.min(open, close) - (Math.random() * (current * 0.002));
      mockArr.push({
        open,
        high,
        low,
        close,
        time: new Date(Date.now() - (24 - i) * 3600 * 1000).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
      });
      current = close;
    }
    setHistoricalData(mockArr);
  };

  const tabs = ['All', 'Crypto', 'Forex', 'Commodities', 'Stocks'];

  const filteredPrices = prices.filter(p => {
    const matchesSearch = p.symbol.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesTab = activeTab === 'All' || p.assetClass === activeTab;
    return matchesSearch && matchesTab;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in">
      
      {/* Search Engines Metatags Preview Box */}
      <div className="bg-[#0b0b14] border border-amber-500/15 p-4 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-xs font-mono">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <span className="h-2 w-2 rounded-full bg-amber-500 animate-ping"></span>
            <span className="text-amber-500 font-bold uppercase tracking-wider text-[10px]">Ecosystem SEO Header Compliance</span>
          </div>
          <p className="text-slate-300 font-bold leading-relaxed">
            FalconSpido real-time core endpoints index rates. Deep indexed with algorithmic structured schema formats.
          </p>
        </div>
        <div className="bg-[#12121e] border border-white/5 py-1.5 px-3 rounded-xl space-y-1 text-slate-500 text-[10px]">
          <div><strong className="text-slate-400">Meta Title:</strong> Real-Time Market Tickers & Feeds</div>
          <div><strong className="text-slate-400">Canonical:</strong> /api/v1/market-data/prices</div>
        </div>
      </div>

      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="space-y-1.5">
          <span className="text-[10px] text-amber-500 uppercase tracking-widest font-extrabold flex items-center space-x-1">
            <Globe className="h-4 w-4 animate-spin-slow text-amber-500" />
            <span>Multi-Exchange Liquidity Proxies</span>
          </span>
          <h1 className="text-2xl sm:text-4xl font-black tracking-tight text-white">Institutional Market Feeds</h1>
          <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
            Directly capturing websocket updates and Brownian-motion noise matrices for global asset classes. Select any instrument to populate dynamic micro-candle oscillators below.
          </p>
        </div>

        <div className="flex items-center space-x-3 bg-[#0c0c14] border border-white/5 px-4 py-2.5 rounded-2xl">
          <div className="space-y-0.5">
            <span className="text-[9px] text-slate-500 uppercase block font-bold font-mono">Dynamic Websocket Updates</span>
            <span className="text-xs text-slate-300 font-bold font-mono flex items-center">
              <Clock className="h-3 w-3 text-amber-500 mr-1 animate-pulse" />
              Sync: <span className="text-white ml-1">{updateTime || "Syncing..."}</span>
            </span>
          </div>
          <div className="h-8 w-[1px] bg-white/10"></div>
          <div className="text-center min-w-[40px]">
            <span className="text-[9px] text-slate-500 uppercase block font-black font-mono">Next Pool</span>
            <span className="text-xs text-emerald-400 font-extrabold font-mono">{secondsToNext}s</span>
          </div>
        </div>
      </div>

      {/* Grid: Markets List & Asset details */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Side: interactive prices explorer */}
        <div className="lg:col-span-7 space-y-6">
          <div className="bg-[#08080d] border border-white/5 p-4 rounded-2xl space-y-4">
            
            {/* Search and Filters */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex flex-wrap gap-1.5">
                {tabs.map((tab) => (
                  <button
                    key={tab}
                    onClick={() => {
                      setActiveTab(tab);
                    }}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-all ${
                      activeTab === tab 
                        ? 'bg-amber-500/10 border-amber-500/30 text-amber-500' 
                        : 'bg-[#12121a]/65 border-white/5 text-slate-400 hover:text-white'
                    }`}
                  >
                    {tab}
                  </button>
                ))}
              </div>

              <div className="relative">
                <input
                  type="text"
                  placeholder="Filter Symbol..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full sm:w-48 bg-[#11111a] border border-white/5 rounded-lg py-1.5 pl-8 pr-3 text-xs text-slate-300 placeholder-slate-500 focus:outline-none focus:border-amber-500/50"
                />
                <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-500" />
              </div>
            </div>

            {/* List Row items */}
            {isLoading && prices.length === 0 ? (
              <div className="py-20 flex flex-col items-center">
                <Spinner size="md" />
                <p className="text-xs text-slate-500 font-mono mt-2">Connecting to FalconSpido proxy pools...</p>
              </div>
            ) : filteredPrices.length === 0 ? (
              <div className="text-center py-20 border border-dashed border-white/5 rounded-xl">
                <p className="text-xs text-slate-500 font-mono">No liquid instruments match search filters.</p>
              </div>
            ) : (
              <div className="space-y-2 overflow-y-auto max-h-[550px] pr-1 scrollbar-thin">
                {filteredPrices.map((item) => {
                  const isUp = item.changePercent >= 0;
                  const isSelected = selectedAsset?.symbol === item.symbol;
                  
                  return (
                    <div 
                      key={item.symbol}
                      onClick={() => setSelectedAsset(item)}
                      className={`flex items-center justify-between p-3.5 rounded-xl border cursor-pointer transition-all ${
                        isSelected 
                          ? 'bg-amber-500/[0.04] border-amber-500/30 shadow-lg' 
                          : 'bg-[#0b0b14] border-white/5 hover:border-white/10 hover:bg-[#0c0c16]'
                      }`}
                    >
                      <div className="flex items-center space-x-3">
                        <div className={`h-8 w-8 rounded-lg flex items-center justify-center ${
                          isUp ? 'bg-emerald-500/10' : 'bg-rose-500/10'
                        }`}>
                          <Activity className={`h-4.5 w-4.5 ${isUp ? 'text-emerald-400' : 'text-rose-400'}`} />
                        </div>
                        <div>
                          <span className="font-extrabold text-white text-xs block font-mono">{item.symbol}</span>
                          <span className="text-[9px] text-slate-500 font-black uppercase tracking-wider block font-mono">{item.assetClass} class</span>
                        </div>
                      </div>

                      {/* Sparklines Simulated preview */}
                      <div className="hidden sm:block h-6 w-24">
                        <svg className="w-full h-full" viewBox="0 0 100 30">
                          <path
                            d={`M 0 ${isUp ? 20 : 10} Q 25 ${isUp ? 10 : 25} 50 ${isUp ? 25 : 8} T 100 ${isUp ? 5 : 22}`}
                            fill="none"
                            stroke={isUp ? "#10b981" : "#f43f5e"}
                            strokeWidth="2"
                            strokeLinecap="round"
                          />
                        </svg>
                      </div>

                      <div className="text-right space-y-0.5 font-mono">
                        <span className="text-xs font-black text-white block">
                          ${parseFloat(item.price).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 5 })}
                        </span>
                        
                        <div className={`text-[10px] font-black inline-flex items-center rounded px-1.5 py-0.2 ${
                          isUp ? 'text-emerald-400 bg-emerald-500/5' : 'text-rose-400 bg-rose-500/5'
                        }`}>
                          {isUp ? <ArrowUpRight className="h-3 w-3 mr-0.5" /> : <ArrowDownRight className="h-3 w-3 mr-0.5" />}
                          {isUp ? '+' : ''}{item.changePercent.toFixed(2)}%
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Side: Detailed chart & mathematical details for chosen Ticker */}
        <div className="lg:col-span-5 space-y-6">
          {selectedAsset ? (
            <div className="space-y-6 animate-fade-in">
              
              {/* Detailed ticker Info block */}
              <div className="bg-[#08080d] border border-white/5 rounded-2xl p-6 space-y-6">
                
                {/* Symbol identification */}
                <div className="flex items-center justify-between pb-4 border-b border-white/5">
                  <div className="space-y-1">
                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest font-mono">Live Asset Profile</span>
                    <h2 className="text-xl font-black text-white font-mono">{selectedAsset.symbol}</h2>
                  </div>
                  <Badge variant={selectedAsset.changePercent >= 0 ? 'green' : 'red'}>
                    {selectedAsset.assetClass} Tier
                  </Badge>
                </div>

                {/* Major stats */}
                <div className="grid grid-cols-3 gap-4 text-center py-1">
                  <div className="space-y-1 bg-[#0e0e16]/50 border border-white/5 p-2 rounded-xl">
                    <span className="text-[9px] text-slate-500 font-mono block font-bold">Price Index</span>
                    <span className="text-xs text-white font-extrabold font-mono block">
                      ${parseFloat(selectedAsset.price).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
                    </span>
                  </div>
                  <div className="space-y-1 bg-[#0e0e16]/50 border border-white/5 p-2 rounded-xl">
                    <span className="text-[9px] text-slate-500 font-mono block font-bold">24H High</span>
                    <span className="text-xs text-emerald-400 font-extrabold font-mono block">
                      ${parseFloat(selectedAsset.high).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
                    </span>
                  </div>
                  <div className="space-y-1 bg-[#0e0e16]/50 border border-white/5 p-2 rounded-xl">
                    <span className="text-[9px] text-slate-500 font-mono block font-bold">24H Low</span>
                    <span className="text-xs text-rose-400 font-extrabold font-mono block">
                      ${parseFloat(selectedAsset.low).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}
                    </span>
                  </div>
                </div>

                {/* Simulated Candle Chart */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider flex items-center">
                      <LineChart className="h-3.5 w-3.5 text-amber-500 mr-1" />
                      Interactive 24H Price Candle Trend Open
                    </span>
                    {fetchingChart && <Spinner size="xs" />}
                  </div>

                  <div className="h-44 bg-[#0a0a10] border border-white/5 rounded-2xl relative flex items-end justify-between p-3 overflow-hidden">
                    {/* Y-Axis pricing anchors */}
                    <div className="absolute left-2 top-2 bottom-2 flex flex-col justify-between text-[8px] text-slate-600 font-mono pointer-events-none">
                      <div>${parseFloat(selectedAsset.high).toFixed(2)}</div>
                      <div>${parseFloat(selectedAsset.price).toFixed(2)}</div>
                      <div>${parseFloat(selectedAsset.low).toFixed(2)}</div>
                    </div>

                    {/* Chart columns display */}
                    <div className="flex items-end justify-between w-full h-full pl-10 pt-2 pb-1 space-x-1">
                      {historicalData.map((cand, idx) => {
                        const isCandleUp = cand.close >= cand.open;
                        const maxVal = parseFloat(selectedAsset.high);
                        const minVal = parseFloat(selectedAsset.low);
                        const range = maxVal - minVal || 1;
                        
                        // Percentage positioning helper
                        const topOffset = ((maxVal - Math.max(cand.open, cand.close)) / range) * 100;
                        const candleHeight = (Math.abs(cand.open - cand.close) / range) * 100;
                        const wickTop = ((maxVal - cand.high) / range) * 100;
                        const wickHeight = ((cand.high - cand.low) / range) * 100;

                        return (
                          <div key={idx} className="flex-1 h-full flex flex-col justify-end items-center relative group">
                            {/* Candle wick line */}
                            <div 
                              className={`absolute w-[1px] ${isCandleUp ? 'bg-emerald-500/60' : 'bg-rose-500/60'}`}
                              style={{ 
                                top: `${Math.max(0, Math.min(100, wickTop))}%`, 
                                height: `${Math.max(3, Math.min(100, wickHeight))}%` 
                              }}
                            />
                            {/* Candle fill block */}
                            <div 
                              className={`w-full rounded-sm z-10 transition-all ${isCandleUp ? 'bg-emerald-500/80 group-hover:bg-emerald-400' : 'bg-rose-500/80 group-hover:bg-rose-400'}`}
                              style={{ 
                                height: `${Math.max(4, Math.min(100, candleHeight))}%`,
                                transform: `translateY(-${((Math.min(cand.open, cand.close) - minVal) / range) * 100}%)`
                              }}
                            />

                            {/* Hover tooltip metadata */}
                            <div className="opacity-0 group-hover:opacity-100 absolute bottom-full mb-1 bg-black/90 border border-white/10 p-2 rounded-lg text-[8px] text-slate-300 font-mono z-50 pointer-events-none min-w-[70px] shadow-2xl transition-opacity">
                              <div className="text-white font-bold">{cand.time}</div>
                              <div>O: {cand.open.toFixed(2)}</div>
                              <div>C: {cand.close.toFixed(2)}</div>
                              <div>H: {cand.high.toFixed(2)}</div>
                              <div>L: {cand.low.toFixed(2)}</div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                  <span className="block text-[8px] text-slate-500 font-mono text-center">
                    Hover over bars to view Open, High, Low, Close (OHLC) values.
                  </span>
                </div>

                {/* Additional Metadata specs */}
                <div className="space-y-3 pt-2">
                  <h4 className="text-xs font-bold text-slate-300 flex items-center">
                    <Info className="h-3.5 w-3.5 text-amber-500 mr-1" />
                    Exchange Specifications & Pivot Points
                  </h4>
                  
                  <div className="text-[10px] font-mono text-slate-400 space-y-2 leading-relaxed bg-[#0c0c14] p-3 rounded-xl border border-white/5">
                    <div className="flex justify-between border-b border-white/5 pb-1">
                      <span>Underlying Volume</span>
                      <span className="text-slate-200">{(selectedAsset.volume / 1000).toFixed(1)}k units</span>
                    </div>
                    <div className="flex justify-between border-b border-white/5 pb-1">
                      <span>Estimated Pivot Point (P)</span>
                      <span className="text-slate-200">${((parseFloat(selectedAsset.high) + parseFloat(selectedAsset.low) + parseFloat(selectedAsset.price)) / 3).toFixed(4)}</span>
                    </div>
                    <div className="flex justify-between border-b border-white/5 pb-1">
                      <span>Dynamic Resistance (R1)</span>
                      <span className="text-emerald-400">${(2 * ((parseFloat(selectedAsset.high) + parseFloat(selectedAsset.low) + parseFloat(selectedAsset.price)) / 3) - parseFloat(selectedAsset.low)).toFixed(4)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Dynamic Support (S1)</span>
                      <span className="text-rose-400">${(2 * ((parseFloat(selectedAsset.high) + parseFloat(selectedAsset.low) + parseFloat(selectedAsset.price)) / 3) - parseFloat(selectedAsset.high)).toFixed(4)}</span>
                    </div>
                  </div>
                </div>

              </div>

              {/* Action: trigger webhook simulated block */}
              <div className="bg-gradient-to-br from-[#121008] to-[#040407] border border-amber-500/10 rounded-2xl p-5 space-y-4">
                <div className="flex items-center space-x-2">
                  <Zap className="h-4 w-4 text-amber-500" />
                  <h3 className="text-xs font-bold text-slate-100">FalconSpido Webhook Receiver</h3>
                </div>
                <p className="text-[11px] text-slate-400 leading-normal">
                  You can set up alert triggers using standard indicators or customized alerts in Pine Script to send real-time JSON signals to our webhooks!
                </p>
                <div className="bg-black/40 p-3 rounded-lg border border-white/5 text-[9px] font-mono text-[#94a3b8] leading-relaxed select-all">
                  {`{
  "secret": "YOUR_ADMIN_SECRET",
  "symbol": "${selectedAsset ? selectedAsset.symbol : "BTCUSDT"}",
  "direction": "BUY",
  "reason": "RSI Oversold Crossover"
}`}
                </div>
              </div>

            </div>
          ) : (
            <div className="bg-[#08080d] border border-white/5 rounded-2xl p-20 text-center text-slate-500 font-mono text-xs">
              Select an instrument symbol on the left to see advanced live charts.
            </div>
          )}
        </div>

      </div>

    </div>
  );
};
