import mongoose from 'mongoose';

// Static seed arrays for high-fidelity fallback when MongoDB is not running/available in the sandbox environment
const MOCK_CATEGORIES = [
  { _id: 'cat_indicators', name: 'Indicators', icon: '📊', slug: 'indicators', description: 'Technical indicators, oscillators, overlay panels, and charts scripts.', color: '#F59E0B', sortOrder: 1, itemCount: 10 },
  { _id: 'cat_ea', name: 'Expert Advisors', icon: '🤖', slug: 'expert-advisors', description: 'MetaTrader Expert Advisors or automated trading desk EAs.', color: '#3B82F6', sortOrder: 2, itemCount: 4 },
  { _id: 'cat_bots', name: 'Trading Bots', icon: '⚙️', slug: 'trading-bots', description: 'Automated cryptocurrency or stock algorithmic trading bots.', color: '#10B981', sortOrder: 3, itemCount: 3 },
  { _id: 'cat_signals', name: 'Signals', icon: '📡', slug: 'signals', description: 'Live automated copy trading signal feeds and telegram alert networks.', color: '#8B5CF6', sortOrder: 4, itemCount: 3 },
  { _id: 'cat_strategies', name: 'Strategies', icon: '🧠', slug: 'strategies', description: 'Detailed templates, systematic logic playbooks, and strategic bundles.', color: '#EC4899', sortOrder: 5, itemCount: 3 },
  { _id: 'cat_screeners', name: 'Screeners', icon: '🔍', slug: 'screeners', description: 'Screener widgets, scanners, filters for finding active breakouts.', color: '#06B6D4', sortOrder: 6, itemCount: 2 },
  { _id: 'cat_scripts', name: 'Scripts & Alerts', icon: '🔔', slug: 'scripts-alerts', description: 'Lightweight pine scripts, alert triggers, webhooks setups.', color: '#EAB308', sortOrder: 7, itemCount: 2 },
  { _id: 'cat_copy', name: 'Copy Trading', icon: '👥', slug: 'copy-trading', description: 'Copy master trading pools and social copy network configs.', color: '#14B8A6', sortOrder: 8, itemCount: 2 },
  { _id: 'cat_templates', name: 'Templates', icon: '📋', slug: 'templates', description: 'Precompiled profiles, chart configurations, workspace layouts.', color: '#6B7280', sortOrder: 9, itemCount: 1 },
  { _id: 'cat_education', name: 'Education & Courses', icon: '🎓', slug: 'education-courses', description: 'Algorithmic trading guides, PineScript classes, video webinars.', color: '#6366F1', sortOrder: 10, itemCount: 1 }
];

const MOCK_PLATFORMS = [
  { _id: 'plat_tv', name: 'TradingView', slug: 'tradingview', description: 'The absolute king of modern charts visualization and PineScript execution.', userCount: '50M+', indicatorLanguage: 'Pine Script', affiliateUrl: 'https://tradingview.com/?aff=falconspido', commissionType: 'recurring_percent', commissionValue: '30', priority: 1, logo: 'https://picsum.photos/100/100?random=1' },
  { _id: 'plat_mt4', name: 'MetaTrader 4', slug: 'metatrader-4', description: 'The industry-standard platform for forex brokerage and automated EAs.', userCount: '20M+', indicatorLanguage: 'MQL4', affiliateUrl: 'https://metatrader4.com', commissionType: 'none', commissionValue: '0', priority: 2, logo: 'https://picsum.photos/100/100?random=2' },
  { _id: 'plat_mt5', name: 'MetaTrader 5', slug: 'metatrader-5', description: 'Advanced successor of MT4 with faster execution cycles and multi-market assets support.', userCount: '15M+', indicatorLanguage: 'MQL5', affiliateUrl: 'https://metatrader5.com', commissionType: 'none', commissionValue: '0', priority: 2, logo: 'https://picsum.photos/100/100?random=3' },
  { _id: 'plat_ctrader', name: 'cTrader', slug: 'ctrader', description: 'Premium institutional-grade retail forex broker platform with C# scripting.', userCount: '3M+', indicatorLanguage: 'C# (cAlgo)', affiliateUrl: 'https://spotware.com', commissionType: 'revenue_share', commissionValue: '15', priority: 3, logo: 'https://picsum.photos/100/100?random=4' },
  { _id: 'plat_ninja', name: 'NinjaTrader', slug: 'ninjatrader', description: 'Professional proprietary futures and forex charting software.', userCount: '500K+', indicatorLanguage: 'NinjaScript', affiliateUrl: 'https://ninjatrader.com', commissionType: 'cpa', commissionValue: '50', priority: 4, logo: 'https://picsum.photos/100/100?random=5' }
];

const MOCK_INDICATORS = [
  {
    _id: 'ind_rsi_div',
    name: 'RSI Divergence Pro',
    slug: 'rsi-divergence-pro',
    listingType: 'Indicator',
    category: { _id: 'cat_indicators', name: 'Indicators', icon: '📊' },
    platform: { _id: 'plat_tv', name: 'TradingView', logo: 'https://picsum.photos/100/100?random=1' },
    description: 'Auto-detects hidden and regular bearish/bullish divergences across RSI parameters.',
    longDescription: 'RSI Divergence Pro is an advanced volatility filter designed to pinpoint market reversals. It monitors multiple oscillators in tandem to detect regular and hidden divergences with high mathematical precision. Features include real-time telegram webhooks, customizable alerts thresholds, and clean visual overlays directly on live candles.',
    assetClass: ['Crypto', 'Forex', 'Stocks'],
    strategyType: ['Momentum', 'Reversal', 'Swing'],
    timeframes: ['M5', 'M15', 'H1', 'H4', 'D1'],
    difficulty: 'Intermediate',
    price: 0,
    pricingModel: 'Free',
    isVerified: true,
    isFeatured: true,
    viewCount: 1540,
    likeCount: 245,
    rating: 4.8,
    reviewsCount: 18,
    trendingScore: 88,
    tags: ['rsi', 'divergence', 'oscillator', 'tradingview', 'free-script'],
    author: 'FalconSpido Quant Labs',
    authorUrl: 'https://falconspido.com',
    externalUrl: 'https://tradingview.com/script/rsi-pro-divergence',
    imageUrl: 'https://picsum.photos/800/400?random=10',
    backtestData: {
      winRate: 67,
      sharpeRatio: 1.4,
      sortinoRatio: 1.8,
      maxDrawdown: 12,
      profitFactor: 1.6,
      totalTrades: 350,
      avgTradesPerMonth: 22,
      backtestPeriod: 'Jan 2021 - Dec 2025',
      backtestCapital: 10000,
      auditStatus: 'Verified',
      auditNotes: 'Verified over backtests on BTC/USDT with 10k initial capital.',
      forwardTestActive: true
    },
    compatibility: { tradingViewVersion: 'v5', minCapital: 500, requiresBroker: false },
    pros: ['Extremely quick signal generation', 'No repainting alerts', 'Compatible with commodities'],
    cons: ['False signals in heavy consolidating markets', 'High resource consumption during startup'],
    faqs: [
      { question: 'Does this indicator repaint?', answer: 'No, RSI Divergence Pro generates alerts strictly at candle closes.' },
      { question: 'Can I use it on mobile devices?', answer: 'Yes, because it is written for the TradingView platform, mobile notifications work flawlessly.' }
    ]
  },
  {
    _id: 'ind_macd_scalp',
    name: 'MACD Scalper Elite',
    slug: 'macd-scalper-elite',
    listingType: 'Indicator',
    category: { _id: 'cat_indicators', name: 'Indicators', icon: '📊' },
    platform: { _id: 'plat_tv', name: 'TradingView', logo: 'https://picsum.photos/100/100?random=1' },
    description: 'Ultra-fast intraday MACD trend overlays for short timeframe scalping strategies.',
    longDescription: 'MACD Scalper Elite isolates institutional-level volume trends on micro-timeframes. Using an exponential ribbon smoothing process, it screens out minor price fluctuations to identify pure momentum bursts. Useful for prop firm challenges or scalping index assets.',
    assetClass: ['Forex', 'Indices', 'Crypto'],
    strategyType: ['Scalping', 'Day Trading', 'Momentum'],
    timeframes: ['M1', 'M5', 'M15'],
    difficulty: 'Beginner',
    price: 29,
    pricingModel: 'Monthly',
    isVerified: true,
    isFeatured: true,
    viewCount: 2310,
    likeCount: 382,
    rating: 4.9,
    reviewsCount: 32,
    trendingScore: 95,
    tags: ['macd', 'scalping', 'intraday', 'forex-tools'],
    author: 'Apex Trading Corp',
    imageUrl: 'https://picsum.photos/800/400?random=11',
    backtestData: {
      winRate: 71,
      sharpeRatio: 1.8,
      maxDrawdown: 8,
      profitFactor: 2.1,
      totalTrades: 1200,
      avgTradesPerMonth: 85,
      backtestPeriod: 'Jun 2022 - Dec 2025',
      backtestCapital: 25000,
      auditStatus: 'Verified',
      auditNotes: 'Audited against historical EUR/USD index feeds on 5m spreads.'
    },
    pros: ['Exceptional win rate', 'Clear color-coded overlays', 'Daily support access'],
    cons: ['Subscription model', 'Not suited for swing trading'],
    faqs: [
      { question: 'What brokers work best?', answer: 'Any raw-spread broker is recommended to minimize slippage during scalps.' }
    ]
  },
  {
    _id: 'ind_smc_suite',
    name: 'Smart Money Concepts Suite',
    slug: 'smart-money-concepts-suite',
    listingType: 'Indicator',
    category: { _id: 'cat_indicators', name: 'Indicators', icon: '📊' },
    platform: { _id: 'plat_tv', name: 'TradingView', logo: 'https://picsum.photos/100/100?random=1' },
    description: 'Real-time automated mapping of market structures (BOS, CHoCH, Orderblocks, FVG).',
    longDescription: 'The ultimate visual kit mapping out institutional flow levels. Generates real-time structural markups including Break of Structure, Change of Character, mitigation blocks, and premium/discount equilibrium pricing zones.',
    assetClass: ['Forex', 'Crypto', 'Stocks', 'Indices'],
    strategyType: ['Smart Money', 'Price Action'],
    timeframes: ['M5', 'H1', 'H4', 'D1'],
    difficulty: 'Advanced',
    price: 49,
    pricingModel: 'Monthly',
    isVerified: true,
    isFeatured: true,
    viewCount: 5410,
    likeCount: 940,
    rating: 4.7,
    reviewsCount: 65,
    trendingScore: 99,
    tags: ['smc', 'ict', 'orderblock', 'fvg', 'market-structure'],
    author: 'LuxQuant Labs',
    imageUrl: 'https://picsum.photos/800/400?random=12',
    backtestData: {
      winRate: 74,
      sharpeRatio: 2.2,
      maxDrawdown: 6,
      profitFactor: 2.4,
      totalTrades: 195,
      backtestPeriod: 'Jan 2023 - Jan 2026',
      auditStatus: 'Verified',
      forwardTestActive: true
    },
    pros: ['Completely automated structural lines', 'Integrated multi-timeframe dashboard panels'],
    cons: ['Steep learning curve', 'High monthly subscription cost'],
    faqs: [
      { question: 'What is CHoCH?', answer: 'CHoCH stands for Change of Character, signifying the first structural shift in trend direction.' }
    ]
  },
  {
    _id: 'ind_gold_ea',
    name: 'Gold EA Scalper Plus',
    slug: 'gold-ea-scalper-plus',
    listingType: 'EA',
    category: { _id: 'cat_ea', name: 'Expert Advisors', icon: '🤖' },
    platform: { _id: 'plat_mt4', name: 'MetaTrader 4', logo: 'https://picsum.photos/100/100?random=2' },
    description: 'Fully automated algorithmic EA optimized for trading XAU/USD (Gold) on MT4.',
    longDescription: 'Gold EA Scalper Plus executes micro breakout strategies during highly volatile New York sessions on Gold. Uses localized ATR grids combined with custom Bollinger momentum bands. Strictly no martingales or averaging down.',
    assetClass: ['Gold'],
    strategyType: ['Scalping', 'Day Trading', 'Volatility'],
    timeframes: ['M5', 'M15'],
    difficulty: 'Expert',
    price: 199,
    pricingModel: 'One-time',
    isVerified: true,
    isFeatured: true,
    viewCount: 1840,
    likeCount: 298,
    rating: 4.6,
    reviewsCount: 14,
    trendingScore: 92,
    tags: ['gold-ea', 'xauusd', 'automated-trading', 'expert-advisor', 'grid-free'],
    author: 'XAU Algorithmic Group',
    imageUrl: 'https://picsum.photos/800/400?random=13',
    backtestData: {
      winRate: 68,
      sharpeRatio: 2.1,
      maxDrawdown: 15,
      profitFactor: 1.9,
      totalTrades: 850,
      avgTradesPerMonth: 60,
      backtestPeriod: 'Jan 2021 - Apr 2026',
      backtestCapital: 10000,
      auditStatus: 'Verified'
    },
    pros: ['Strict stop-loss per contract', 'Zero Martingale risks'],
    cons: ['Expensive startup price', 'Optimized strictly for Gold'],
    faqs: [{ question: 'Is a VPS required?', answer: 'Yes, a Virtual Private Server is highly advised to prevent network disconnects.' }]
  }
];

const MOCK_REVIEWS = [
  { _id: 'rev1', indicatorId: 'ind_rsi_div', reviewerName: 'Marcus Aurelius FX', rating: 5, title: 'Absolute Masterpiece', body: 'This divergence script has completely changed my swing setups on GBPUSD. The alerts do not repaint and are rock-solid.', usefulCount: 14, createdAt: '2026-05-14T10:00:00Z' },
  { _id: 'rev2', indicatorId: 'ind_rsi_div', reviewerName: 'CryptoTrader99', rating: 4, title: 'Very consistent indicators', body: 'Excellent on 1H charts for Bitcoin, but fails on low volatile altcoins. Highly recommended for majors.', usefulCount: 8, createdAt: '2026-05-18T14:30:00Z' },
  { _id: 'rev3', indicatorId: 'ind_smc_suite', reviewerName: 'SMC Scholar', rating: 5, title: 'Unbeatable structure plotting', body: 'LuxQuant is a godsend. It automates almost 90% of my manual SMC lines markup.', usefulCount: 42, createdAt: '2026-06-01T08:15:00Z' }
];

const MOCK_PRESETS = [
  { _id: 'p_1', indicatorId: 'ind_rsi_div', title: 'BTC/USDT 1H Conservative Reversals', assetClass: 'Crypto', symbol: 'BTCUSDT', timeframe: 'H1', parameters: 'RSI Length: 14, Overbought: 75, Oversold: 25, Divergence Lookback: 60', upvotes: 28, downvotes: 1, author: 'FalconSpido Quant' },
  { _id: 'p_2', indicatorId: 'ind_smc_suite', title: 'EUR/USD 15M High-Frequency Orderblock Scalp', assetClass: 'Forex', symbol: 'EURUSD', timeframe: 'M15', parameters: 'Structure length: 5, Mitigation filter: Active, FVG check: Strict', upvotes: 19, downvotes: 0, author: 'SMC King' }
];

const MOCK_BACKTESTS = [
  { _id: 'b_1', indicatorId: 'ind_rsi_div', testerName: 'QuantAudit Lab', timeframe: 'H1', marketSymbol: 'BTCUSDT', testPeriod: 'Jan 2024 - Dec 2025', metrics: { netProfitPercent: 124.5, profitFactor: 1.82, maxDrawdownPercent: 11.2, winRate: 64.8 }, dataSource: 'Binance Spot Premium Tick Data', auditStatus: 'Verified', reportsCount: 120 }
];

const MOCK_SIGNALS = [
  { _id: 'sig_1', name: 'FX Premium Major Trend Run', provider: 'FalconSpido Signal Desk', asset: 'GBPUSD', direction: 'BUY', entry: '1.2745', stopLoss: '1.2690', takeProfit1: '1.2810', takeProfit2: '1.2880', timeframe: 'H1', status: 'Active', createdAt: new Date() },
  { _id: 'sig_2', name: 'Crypto Momentum Break', provider: 'CoinBurst Signals', asset: 'BTCUSDT', direction: 'BUY', entry: '67400', stopLoss: '66100', takeProfit1: '69000', takeProfit2: '71500', timeframe: 'M15', status: 'Active', createdAt: new Date() }
];

const MOCK_BROKERS = [
  { _id: 'br_1', name: 'Pepperstone', slug: 'pepperstone', rating: 4.9, regulation: 'ASIC, FCA, CySEC', minDeposit: 0, leverage: '1:500', platforms: ['MT4', 'MT5', 'cTrader', 'TradingView'], spreadType: 'Raw Spread from 0.0 pips', affiliateUrl: 'https://pepperstone.com', isFeatured: true, logo: 'https://picsum.photos/100/100?random=20' },
  { _id: 'br_2', name: 'IC Markets', slug: 'ic-markets', rating: 4.8, regulation: 'ASIC, FSA, CySEC', minDeposit: 200, leverage: '1:500', platforms: ['MT4', 'MT5', 'cTrader'], spreadType: 'True ECN Spreads from 0.0 pips', affiliateUrl: 'https://icmarkets.com', isFeatured: true, logo: 'https://picsum.photos/100/100?random=21' }
];

const MOCK_NEWS = [
  { _id: 'n_1', title: 'FED Signals Interest Rate Hold Amid Balanced Inflation Swaps', slug: 'fed-signals-rate-hold-inflation-swaps', summary: 'Federal Reserve officials reiterated a data-dependent holding cycle, raising speculation regarding Q3 economic easement cycles.', content: 'Federal Reserve authorities emphasized that the economic cooling meets baseline expectations, but they prefer observing consecutive quarters of inflation targets nearing 2% before initiating systematic base points discounts. Institutional money indices reacted with heavy consolidation spikes across Forex majors.', source: 'FalconSpido Newsroom', sentiment: 'Neutral', publishedAt: new Date() },
  { _id: 'n_2', title: 'Bitcoin Spot ETF Net Outflows Accelerate as Retails Hedge Risk Capital', slug: 'bitcoin-spot-etf-outflows-accelerate-risk-capital', summary: 'Outflows from the top Bitcoin holdings vehicles reached record thresholds as geopolitical risk premiums grow.', content: 'Primary cryptocurrency index products marked a three-day outflow acceleration of $410M. Traditional funds seem to be swapping yield vehicles for commodity protections or high-density cash reserves as geopolitical risk measures elevate across global equity blocks.', source: 'Bloomberg Quant Desk Feed', sentiment: 'Bearish', publishedAt: new Date() }
];

const MOCK_CALENDAR = [
  { _id: 'cal_1', title: 'Core CPI m/m Deviation Index', eventTime: new Date(Date.now() + 24 * 3600 * 1000), currencyAffected: 'USD', impact: 'High', previousResult: '0.3%', forecastResult: '0.2%', actualResult: '' },
  { _id: 'cal_2', title: 'BoE Official Bank Rate Release', eventTime: new Date(Date.now() + 48 * 3600 * 1000), currencyAffected: 'GBP', impact: 'Critical', previousResult: '5.25%', forecastResult: '5.25%', actualResult: '' }
];

const MOCK_SCREENER = [
  { symbol: 'BTCUSDT', price: 68420.5, change24h: 2.45, rsi: 65.4, macdStatus: 'Bullish Cross', ema200Diff: 3.12, bollingerState: 'Consolidating Squeeze', volumeAlert: 'Normal', currentSignal: 'Neutral' },
  { symbol: 'ETHUSDT', price: 3510.2, change24h: 1.12, rsi: 52.1, macdStatus: 'Neutral', ema200Diff: 1.45, bollingerState: 'Normal Upper', volumeAlert: 'Slight Spike', currentSignal: 'Neutral' },
  { symbol: 'EURUSD', price: 1.0854, change24h: -0.15, rsi: 28.5, macdStatus: 'Bearish Trend', ema200Diff: -0.42, bollingerState: 'Oversold Out-of-Bands', volumeAlert: 'Institutional Entry', currentSignal: 'BUY Reversal' },
  { symbol: 'GBPUSD', price: 1.2721, change24h: -0.05, rsi: 42.0, macdStatus: 'Slight Bullish', ema200Diff: -0.12, bollingerState: 'Consolidating Squeeze', volumeAlert: 'Low Volatility', currentSignal: 'Neutral' },
  { symbol: 'XAUUSD', price: 2345.10, change24h: 1.85, rsi: 72.4, macdStatus: 'Extreme Momentum', ema200Diff: 4.85, bollingerState: 'Overbought Breakout', volumeAlert: 'Extreme Volume Spike', currentSignal: 'SELL Correction' }
];

// Fallback Controller Middleware
export default function dbFallback(req, res, next) {
  // If mongoose is connected (status === 1), proceed to actual database models
  if (mongoose.connection.readyState === 1) {
    return next();
  }

  // Intercepting /api/v1 routes with mock outputs to make FalconSpido fully functional and rapid
  const path = req.path;
  const method = req.method;

  // Logging fallback activation
  console.info(`[Database Fallback Controller] Serving mock data for: ${method} ${path}`);

  // Base utility for handling CORS and JSON headers
  res.setHeader('Content-Type', 'application/json');

  // Categories Router
  if (path.startsWith('/categories')) {
    if (path === '/categories' || path === '/categories/') {
      return res.status(200).json({ success: true, data: MOCK_CATEGORIES });
    }
    const matchSlug = path.split('/')[2];
    if (matchSlug) {
      if (path.endsWith('/indicators')) {
        const cat = MOCK_CATEGORIES.find(c => c.slug === matchSlug);
        const matchedIndicators = MOCK_INDICATORS.filter(ind => ind.category._id === cat?._id || ind.category === cat?._id);
        return res.status(200).json({ success: true, data: matchedIndicators, total: matchedIndicators.length, page: 1, pages: 1 });
      } else {
        const cat = MOCK_CATEGORIES.find(c => c.slug === matchSlug) || MOCK_CATEGORIES[0];
        return res.status(200).json({ success: true, data: cat });
      }
    }
  }

  // Platforms Router
  if (path.startsWith('/platforms')) {
    if (path === '/platforms' || path === '/platforms/') {
      return res.status(200).json({ success: true, data: MOCK_PLATFORMS });
    }
    const matchSlug = path.split('/')[2];
    if (matchSlug) {
      if (path.endsWith('/indicators')) {
        const plat = MOCK_PLATFORMS.find(p => p.slug === matchSlug);
        const matchedIndicators = MOCK_INDICATORS.filter(ind => ind.platform._id === plat?._id || ind.platform === plat?._id);
        return res.status(200).json({ success: true, data: matchedIndicators, total: matchedIndicators.length, page: 1, pages: 1 });
      } else {
        const plat = MOCK_PLATFORMS.find(p => p.slug === matchSlug) || MOCK_PLATFORMS[0];
        return res.status(200).json({ success: true, data: plat });
      }
    }
  }

  // Indicators Router
  if (path.startsWith('/indicators')) {
    if (path === '/indicators/trending' || path === '/indicators/featured' || path === '/indicators/top-rated' || path === '/indicators/new') {
      return res.status(200).json({ success: true, data: MOCK_INDICATORS });
    }
    if (path === '/indicators/stats') {
      return res.status(200).json({
        success: true,
        data: {
          indicatorsCount: MOCK_INDICATORS.length,
          categoriesCount: MOCK_CATEGORIES.length,
          platformsCount: MOCK_PLATFORMS.length,
          reviewsCount: MOCK_REVIEWS.length,
          signalsCount: MOCK_SIGNALS.length
        }
      });
    }
    if (path === '/indicators/compare') {
      const idsRaw = req.query.ids || '';
      const ids = idsRaw.split(',').filter(Boolean);
      const filtered = MOCK_INDICATORS.filter(ind => ids.includes(ind._id));
      return res.status(200).json({ success: true, data: filtered.length ? filtered : MOCK_INDICATORS.slice(0, 2) });
    }

    const matchSlug = path.split('/')[2];
    if (matchSlug) {
      if (path.endsWith('/similar')) {
        const parentSlug = path.split('/')[2];
        const matchedIndicators = MOCK_INDICATORS.filter(ind => ind.slug !== parentSlug);
        return res.status(200).json({ success: true, data: matchedIndicators });
      } else if (path.endsWith('/like') && method === 'PATCH') {
        const indId = path.split('/')[2];
        const ind = MOCK_INDICATORS.find(i => i._id === indId || i.slug === indId) || MOCK_INDICATORS[0];
        ind.likeCount = (ind.likeCount || 0) + 1;
        return res.status(200).json({ success: true, data: ind });
      } else if (path.endsWith('/flag-scam') && method === 'PATCH') {
        return res.status(200).json({ success: true, message: 'Indicator flagged successfully for manual investigation.' });
      } else if (path.endsWith('/view') && method === 'PATCH') {
        return res.status(200).json({ success: true });
      } else {
        const ind = MOCK_INDICATORS.find(i => i.slug === matchSlug || i._id === matchSlug) || MOCK_INDICATORS[0];
        return res.status(200).json({ success: true, data: ind });
      }
    }

    // Default indicator query matching filters
    let results = [...MOCK_INDICATORS];
    if (req.query.search) {
      const searchStr = req.query.search.toLowerCase();
      results = results.filter(ind => ind.name.toLowerCase().includes(searchStr) || ind.description.toLowerCase().includes(searchStr));
    }
    if (req.query.listingType) {
      results = results.filter(ind => ind.listingType === req.query.listingType);
    }
    return res.status(200).json({
      success: true,
      data: results,
      total: results.length,
      page: 1,
      pages: 1
    });
  }

  // Reviews Router
  if (path.startsWith('/reviews')) {
    if (method === 'POST') {
      const newReview = {
        _id: `rev_${Date.now()}`,
        indicatorId: req.body.indicatorId || 'ind_rsi_div',
        reviewerName: req.body.reviewerName || 'Anonymous',
        rating: req.body.rating || 5,
        title: req.body.title || 'Excellent Strategy',
        body: req.body.body || 'Very nice results so far.',
        usefulCount: 0,
        createdAt: new Date()
      };
      MOCK_REVIEWS.push(newReview);
      return res.status(201).json({ success: true, data: newReview });
    }
    if (path.startsWith('/reviews/indicator/')) {
      const indId = path.split('/').pop();
      const filtered = MOCK_REVIEWS.filter(rev => rev.indicatorId === indId);
      return res.status(200).json({ success: true, data: filtered });
    }
    if (path.endsWith('/helpful') && method === 'PATCH') {
      const revId = path.split('/')[2];
      const rev = MOCK_REVIEWS.find(r => r._id === revId);
      if (rev) rev.usefulCount += 1;
      return res.status(200).json({ success: true, data: rev });
    }
  }

  // Presets Router
  if (path.startsWith('/presets')) {
    if (method === 'POST') {
      const newPreset = {
        _id: `p_${Date.now()}`,
        indicatorId: req.body.indicatorId || 'ind_rsi_div',
        title: req.body.title || 'Custom Preset',
        assetClass: req.body.assetClass || 'Crypto',
        symbol: req.body.symbol || 'Generic',
        timeframe: req.body.timeframe || 'H1',
        parameters: req.body.parameters || '',
        upvotes: 0,
        downvotes: 0,
        author: 'FalconSpido Guest'
      };
      MOCK_PRESETS.push(newPreset);
      return res.status(201).json({ success: true, data: newPreset });
    }
    if (path.startsWith('/presets/indicator/')) {
      const indId = path.split('/').pop();
      const filtered = MOCK_PRESETS.filter(p => p.indicatorId === indId);
      return res.status(200).json({ success: true, data: filtered });
    }
    if (path.endsWith('/vote') && method === 'PATCH') {
      const pId = path.split('/')[2];
      const p = MOCK_PRESETS.find(pr => pr._id === pId);
      if (p) {
        if (req.body.direction === 'up') p.upvotes += 1;
        else p.downvotes += 1;
      }
      return res.status(200).json({ success: true, data: p });
    }
  }

  // Backtests Router
  if (path.startsWith('/backtest-reports')) {
    if (method === 'POST') {
      const newReport = {
        _id: `b_${Date.now()}`,
        indicatorId: req.body.indicatorId || 'ind_rsi_div',
        testerName: req.body.testerName || 'Guest Auditor',
        timeframe: req.body.timeframe || 'H1',
        marketSymbol: req.body.marketSymbol || 'EURUSD',
        testPeriod: req.body.testPeriod || 'Past 1 Year',
        metrics: req.body.metrics || { netProfitPercent: 65, profitFactor: 1.5, maxDrawdownPercent: 8, winRate: 60 },
        dataSource: req.body.dataSource || 'Broker Tick Feeds',
        auditStatus: 'Unaudited',
        createdAt: new Date()
      };
      MOCK_BACKTESTS.push(newReport);
      return res.status(201).json({ success: true, data: newReport });
    }
    if (path.startsWith('/backtest-reports/indicator/')) {
      const indId = path.split('/').pop();
      const filtered = MOCK_BACKTESTS.filter(b => b.indicatorId === indId);
      return res.status(200).json({ success: true, data: filtered });
    }
  }

  // Signals Router
  if (path.startsWith('/signals')) {
    return res.status(200).json({ success: true, data: MOCK_SIGNALS });
  }

  // Brokers Router
  if (path.startsWith('/brokers')) {
    return res.status(200).json({ success: true, data: MOCK_BROKERS });
  }

  // News Router
  if (path.startsWith('/news')) {
    const slug = path.split('/').pop();
    if (slug && slug !== 'news') {
      const story = MOCK_NEWS.find(n => n.slug === slug || n._id === slug) || MOCK_NEWS[0];
      return res.status(200).json({ success: true, data: story });
    }
    return res.status(200).json({ success: true, data: MOCK_NEWS });
  }

  // Macro calendar Router
  if (path.startsWith('/macro-calendar')) {
    return res.status(200).json({ success: true, data: MOCK_CALENDAR });
  }

  // Technical Screener Router
  if (path.startsWith('/screener')) {
    return res.status(200).json({ success: true, data: MOCK_SCREENER });
  }

  // Submit Listing Form Router
  if (path === '/submit' && method === 'POST') {
    return res.status(200).json({ success: true, message: 'Thank you! Your FalconSpido trading tool listing proposal has been submitted for verification.' });
  }

  // Default fallback responder
  res.status(404).json({ success: false, error: 'Target API route not found in sandbox environment.' });
}
