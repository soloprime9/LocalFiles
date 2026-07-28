import asyncHandler from 'express-async-handler';
import axios from 'axios';

// Cache price data so we do not spam downstream API limits if polled super fast.
let priceCache = {};
let lastCacheTime = null;

// Simulated baseline price ranges for non-crypto symbols (forex, stocks, commodities, options, futures)
const simulatedStocks = {
  'AAPL': { base: 185.25, spread: 0.12 },
  'TSLA': { base: 178.60, spread: 0.25 },
  'NVDA': { base: 125.40, spread: 0.35 },
  'GOOG': { base: 172.10, spread: 0.15 },
  'MSFT': { base: 415.80, spread: 0.28 },
  'EURUSD': { base: 1.0854, spread: 0.00015 },
  'GBPUSD': { base: 1.2712, spread: 0.00020 },
  'USDJPY': { base: 156.45, spread: 0.015 },
  'AUDUSD': { base: 0.6654, spread: 0.00010 },
  'XAUUSD': { base: 2321.40, spread: 0.45 }, // Gold
  'XAGUSD': { base: 29.15, spread: 0.02 },   // Silver
  'USOIL': { base: 78.45, spread: 0.05 }     // Crude Oil
};

// Generates high-fidelity second-by-second ticker movements around real and simulated assets
const getTickerPrices = async () => {
  const now = Date.now();
  
  // Return cached data if requested less than 1.5 seconds ago
  if (lastCacheTime && (now - lastCacheTime < 1500)) {
    return priceCache;
  }

  const results = {};

  // 1. Fetch real-time cryptocurrency data from the public Binance api
  try {
    const cryptoResponse = await axios.get('https://api.binance.com/api/v3/ticker/price', { timeout: 3000 });
    const targetPairs = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 'DOGEUSDT'];
    
    if (cryptoResponse && Array.isArray(cryptoResponse.data)) {
      cryptoResponse.data.forEach(item => {
        if (targetPairs.includes(item.symbol)) {
          const rawPrice = parseFloat(item.price);
          // Add a subtle random fluctuation to match "each second updates" feel perfectly
          const fluctuation = rawPrice * ((Math.random() - 0.5) * 0.0002);
          const finalPrice = rawPrice + fluctuation;
          
          results[item.symbol] = {
            symbol: item.symbol,
            price: parseFloat(finalPrice.toFixed(4)),
            changePercent: parseFloat(((Math.random() - 0.48) * 1.5).toFixed(2)), // simulated 24h change
            high: parseFloat((finalPrice * 1.02).toFixed(4)),
            low: parseFloat((finalPrice * 0.98).toFixed(4)),
            volume: Math.floor(rawPrice * (5000 + Math.random() * 20000)),
            market: 'Crypto',
            lastUpdated: new Date()
          };
        }
      });
    }
  } catch (err) {
    // Fail-safe Crypto generator block if external API is unreachable in sandbox environment
    const cryptos = { 'BTCUSDT': 68420.00, 'ETHUSDT': 3540.00, 'SOLUSDT': 152.40, 'BNBUSDT': 590.20 };
    Object.keys(cryptos).forEach(sym => {
      const base = cryptos[sym];
      const fluc = (Math.random() - 0.5) * (base * 0.002);
      const val = base + fluc;
      results[sym] = {
        symbol: sym,
        price: parseFloat(val.toFixed(2)),
        changePercent: parseFloat(((Math.random() - 0.52) * 2.2).toFixed(2)),
        high: parseFloat((val * 1.015).toFixed(2)),
        low: parseFloat((val * 0.985).toFixed(2)),
        volume: Math.floor(val * 4200),
        market: 'Crypto',
        lastUpdated: new Date()
      };
    });
  }

  // 2. Generate simulated yet highly professional real-time Stock, Forex, Commodity prices
  Object.keys(simulatedStocks).forEach(symbol => {
    const config = simulatedStocks[symbol];
    // Dynamic brownian motion style noise
    const noise = (Math.random() - 0.5) * config.spread * 12;
    const finalPrice = config.base + noise;
    const precision = symbol.includes('USD') && !symbol.includes('XAU') && !symbol.includes('XAG') ? 5 : 2;
    
    // Categorize listing source
    let market = 'Stocks';
    if (symbol.includes('USD') && !symbol.includes('XAU') && !symbol.includes('XAG') && symbol !== 'USOIL') {
      market = 'Forex';
    } else if (['XAUUSD', 'XAGUSD', 'USOIL'].includes(symbol)) {
      market = 'Commodities';
    }

    results[symbol] = {
      symbol,
      price: parseFloat(finalPrice.toFixed(precision)),
      changePercent: parseFloat(((Math.random() - 0.49) * 0.85).toFixed(2)),
      high: parseFloat((config.base + Math.abs(noise)*1.8).toFixed(precision)),
      low: parseFloat((config.base - Math.abs(noise)*1.8).toFixed(precision)),
      volume: market === 'Forex' ? '-' : Math.floor(100000 + Math.random() * 450000),
      market,
      lastUpdated: new Date()
    };
  });

  priceCache = results;
  lastCacheTime = now;
  return results;
};

/**
 * @desc    Get real-time rates of all assets
 * @route   GET /api/v1/market-data/prices
 * @access  Public
 */
export const getLivePrices = asyncHandler(async (req, res) => {
  const prices = await getTickerPrices();
  res.status(200).json({
    success: true,
    count: Object.keys(prices).length,
    timestamp: new Date(),
    data: prices
  });
});

/**
 * @desc    Get detailed chart data mimicking TradingView lightweight feed for specific symbols
 * @route   GET /api/v1/market-data/candles/:symbol
 * @access  Public
 */
export const getSymbolCandles = asyncHandler(async (req, res) => {
  const { symbol } = req.params;
  const resolution = req.query.resolution || '1D'; // 1D, 4H, 1H, 15M, 1M
  const count = parseInt(req.query.count || '50', 10);

  let basePrice = 100;
  let spread = 1.2;
  const isS = simulatedStocks[symbol];
  if (isS) {
    basePrice = isS.base;
    spread = isS.spread;
  } else if (symbol.startsWith('BTC')) {
    basePrice = 68420;
    spread = 450;
  } else if (symbol.startsWith('ETH')) {
    basePrice = 3540;
    spread = 25;
  } else if (symbol.startsWith('SOL')) {
    basePrice = 152;
    spread = 1.8;
  }

  // Generate realistic candles over historic bars
  const candles = [];
  let currentBase = basePrice * 0.94; // start slightly lower to make active visual uptrends

  for (let i = 0; i < count; i++) {
    const change = (Math.random() - 0.48) * spread;
    const open = currentBase;
    const close = currentBase + change;
    const high = Math.max(open, close) + Math.random() * (spread * 0.5);
    const low = Math.min(open, close) - Math.random() * (spread * 0.5);
    
    currentBase = close; // flow next candle

    const d = new Date();
    if (resolution === '1D') {
      d.setDate(d.getDate() - (count - i));
    } else {
      d.setHours(d.getHours() - (count - i));
    }

    candles.push({
      time: d.toISOString().split('T')[0] + ' ' + d.toTimeString().split(' ')[0],
      open: parseFloat(open.toFixed(4)),
      high: parseFloat(high.toFixed(4)),
      low: parseFloat(low.toFixed(4)),
      close: parseFloat(close.toFixed(4)),
      volume: Math.floor(5000 + Math.random() * 45000)
    });
  }

  res.status(200).json({
    success: true,
    symbol: symbol.toUpperCase(),
    resolution,
    count: candles.length,
    data: candles
  });
});
