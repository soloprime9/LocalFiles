import mongoose from 'mongoose';
import dotenv from 'dotenv';
import {
  Category,
  Platform,
  Indicator,
  Review,
  Signal,
  BrokerAffiliate,
  BlogPost,
  MarketNews
} from '../models/index.js';

// Load environmental variables
dotenv.config();

const runSeed = async () => {
  console.log('🔄 [Seed Engine] Beginning database purging...');
  
  const uri = process.env.MONGO_URI || 'mongodb://localhost:27017/indicatorhub';
  try {
    await mongoose.connect(uri);
    console.log('✓ [Seed Engine] Connected to database.');

    // 1. Purge previous documents
    await Category.deleteMany({});
    await Platform.deleteMany({});
    await Indicator.deleteMany({});
    await Review.deleteMany({});
    await Signal.deleteMany({});
    await BrokerAffiliate.deleteMany({});
    await BlogPost.deleteMany({});
    await MarketNews.deleteMany({});
    console.log('✓ [Seed Engine] All collections purged successfully.');

    // 2. Insert Categories
    console.log('🔄 [Seed Engine] Seeding Categories...');
    const seededCategories = await Category.create([
      { name: 'Indicators', icon: '📊', description: 'Technical indicators, oscillators, overlay panels, and charts scripts.', color: '#F59E0B', sortOrder: 1 },
      { name: 'Expert Advisors', icon: '🤖', description: 'MetaTrader Expert Advisors or automated trading desk EAs.', color: '#3B82F6', sortOrder: 2 },
      { name: 'Trading Bots', icon: '⚙️', description: 'Automated cryptocurrency or stock algorithmic trading bots.', color: '#10B981', sortOrder: 3 },
      { name: 'Signals', icon: '📡', description: 'Live automated copy trading signal feeds and telegram alert networks.', color: '#8B5CF6', sortOrder: 4 },
      { name: 'Strategies', icon: '🧠', description: 'Detailed templates, systematic logic playbooks, and strategic bundles.', color: '#EC4899', sortOrder: 5 },
      { name: 'Screeners', icon: '🔍', description: 'Screener widgets, scanners, filters for finding active breakouts.', color: '#06B6D4', sortOrder: 6 },
      { name: 'Scripts & Alerts', icon: '🔔', description: 'Lightweight pine scripts, alert triggers, webhooks setups.', color: '#EAB308', sortOrder: 7 },
      { name: 'Copy Trading', icon: '👥', description: 'Copy master trading pools and social copy network configs.', color: '#14B8A6', sortOrder: 8 },
      { name: 'Templates', icon: '📋', description: 'Precompiled profiles, chart configurations, workspace layouts.', color: '#6B7280', sortOrder: 9 },
      { name: 'Education & Courses', icon: '🎓', description: 'Algorithmic trading guides, PineScript classes, video webinars.', color: '#6366F1', sortOrder: 10 }
    ]);
    console.log(`✓ [Seed Engine] Seeded ${seededCategories.length} Categories.`);

    // Map categories by name for easy reference
    const catMap = {};
    seededCategories.forEach(c => {
      catMap[c.name] = c._id;
    });

    // 3. Insert Platforms
    console.log('🔄 [Seed Engine] Seeding Platforms...');
    const seededPlatforms = await Platform.create([
      { name: 'TradingView', description: 'The absolute king of modern charts visualization and PineScript execution.', userCount: '50M+', indicatorLanguage: 'Pine Script', affiliateUrl: 'https://tradingview.com/?aff=indicatorhub', commissionType: 'recurring_percent', commissionValue: '30', priority: 1, logo: 'https://placehold.co/100x100/171B26/FFF?text=TradingView' },
      { name: 'MetaTrader 4', description: 'The industry-standard platform for forex brokerage and automated EAs.', userCount: '20M+', indicatorLanguage: 'MQL4', affiliateUrl: 'https://metatrader4.com', commissionType: 'none', commissionValue: '0', priority: 2, logo: 'https://placehold.co/100x100/004B87/FFF?text=MT4' },
      { name: 'MetaTrader 5', description: 'Advanced successor of MT4 with faster execution cycles and multi-market assets support.', userCount: '15M+', indicatorLanguage: 'MQL5', affiliateUrl: 'https://metatrader5.com', commissionType: 'none', commissionValue: '0', priority: 2, logo: 'https://placehold.co/100x100/039BE5/FFF?text=MT5' },
      { name: 'cTrader', description: 'Premium institutional-grade retail forex broker platform with C# scripting.', userCount: '3M+', indicatorLanguage: 'C# (cAlgo)', affiliateUrl: 'https://spotware.com', commissionType: 'revenue_share', commissionValue: '15', priority: 3, logo: 'https://placehold.co/100x100/1E1E24/FFF?text=cTrader' },
      { name: 'NinjaTrader', description: 'Professional proprietary futures and forex charting software.', userCount: '500K+', indicatorLanguage: 'NinjaScript', affiliateUrl: 'https://ninjatrader.com', commissionType: 'cpa', commissionValue: '50', priority: 4, logo: 'https://placehold.co/100x100/D32F2F/FFF?text=Ninja' },
      { name: 'ThinkorSwim', description: 'Charles Schwab institutional tier charting workbench for option strategies.', userCount: '2M+', indicatorLanguage: 'thinkScript', affiliateUrl: 'https://schwab.com', commissionType: 'none', commissionValue: '0', priority: 4, logo: 'https://placehold.co/100x100/4CAF50/FFF?text=TOS' },
      { name: '3Commas', description: 'Popular multi-exchange automated grid, DCA, and signal connector bots.', userCount: '1M+', indicatorLanguage: 'API Payload configs', affiliateUrl: 'https://3commas.io', commissionType: 'recurring_percent', commissionValue: '25', priority: 5, logo: 'https://placehold.co/100x100/0288D1/FFF?text=3Commas' },
      { name: 'Pionex', description: 'Excellent cryptocurrency exchange with built-in free grid systems.', userCount: '3M+', indicatorLanguage: 'Settings profiles', affiliateUrl: 'https://pionex.com', commissionType: 'revenue_share', commissionValue: '20', priority: 5, logo: 'https://placehold.co/100x100/FF5722/FFF?text=Pionex' },
      { name: 'Cryptohopper', description: 'Cloud-hosted automated trading platform with strategy marketplace.', userCount: '500K+', indicatorLanguage: 'Marketplace settings', affiliateUrl: 'https://cryptohopper.com', commissionType: 'recurring_percent', commissionValue: '15', priority: 5, logo: 'https://placehold.co/100x100/3F51B5/FFF?text=Cryptohopper' },
      { name: 'HaasOnline', description: 'Deep quantitative algorithmic trading system with HaasScript language.', userCount: '100K+', indicatorLanguage: 'HaasScript', affiliateUrl: 'https://haasonline.com', commissionType: 'cpa', commissionValue: '100', priority: 6, logo: 'https://placehold.co/100x100/212121/FFF?text=Haas' }
    ]);
    console.log(`✓ [Seed Engine] Seeded ${seededPlatforms.length} Platforms.`);

    const platMap = {};
    seededPlatforms.forEach(p => {
      platMap[p.name] = p._id;
    });

    // 4. Insert 30 Indicators
    console.log('🔄 [Seed Engine] Seeding 30 core indicators...');

    const indicatorsData = [
      // 1-10: INDICATORS
      {
        name: 'RSI Divergence Pro',
        listingType: 'Indicator',
        category: catMap['Indicators'],
        platform: platMap['TradingView'],
        description: 'Auto-detects hidden and regular bearish/bullish divergences across RSI parameters.',
        longDescription: 'RSI Divergence Pro is an advanced volatility filter designed to pinpoint market reversals. It monitors multiple oscillators in tandem to detect regular and hidden divergences with high mathematical precision. Features include real-time telegram webhooks, customizable alerts thresholds, and clean visual overlays directly on live candles.',
        assetClass: ['Crypto', 'Forex', 'Stocks'],
        strategyType: ['Momentum', 'Reversal', 'Swing'],
        timeframes: ['M5', 'M15', 'H1', 'H4', 'D1'],
        difficulty: 'Intermediate',
        price: 0,
        pricingModel: 'Free',
        isVerified: true,
        tags: ['rsi', 'divergence', 'oscillator', 'tradingview', 'free-script'],
        author: 'A Quant Team',
        authorUrl: 'https://quant-team.io',
        externalUrl: 'https://tradingview.com/script/rsi-pro-divergence',
        affiliateUrl: 'https://tradingview.com/?aff=id_rsi_pro',
        imageUrl: 'https://placehold.co/800x400/171B26/F59E0B?text=RSI+Divergence+Pro',
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
        ],
        submittedBy: 'admin@quant-team.io'
      },
      {
        name: 'MACD Scalper Elite',
        listingType: 'Indicator',
        category: catMap['Indicators'],
        platform: platMap['TradingView'],
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
        tags: ['macd', 'scalping', 'intraday', 'forex-tools'],
        author: 'Apex Trading Corp',
        imageUrl: 'https://placehold.co/800x400/111/4B5563?text=MACD+Scalper+Elite',
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
        ],
        submittedBy: 'licensing@apextrading.com'
      },
      {
        name: 'Bollinger Band Squeeze Screener',
        listingType: 'Indicator',
        category: catMap['Indicators'],
        platform: platMap['TradingView'],
        description: 'Detects periods of historically low volatility to anticipate breakout moves.',
        longDescription: 'A classic John Carter style Bollinger Squeeze script that calculates volatility ranges in real-time. Highlights consolidating bands with dot alerts showing exact consolidation thresholds.',
        assetClass: ['Stocks', 'Crypto', 'Commodities'],
        strategyType: ['Breakout', 'Volatility'],
        timeframes: ['H1', 'H4', 'D1'],
        difficulty: 'Intermediate',
        price: 0,
        pricingModel: 'Free',
        tags: ['bollinger-bands', 'squeeze', 'breakouts', 'momentum-breaks'],
        author: 'LazyTrader Scripts',
        imageUrl: 'https://placehold.co/800x400/171B26/3B82F6?text=Bollinger+Squeeze',
        backtestData: {
          winRate: 62,
          maxDrawdown: 18,
          auditStatus: 'Unaudited'
        },
        pros: ['Excellent breakout catch rate', 'Open source PineScript code'],
        cons: ['Low signal volume'],
        faqs: [{ question: 'Is the code open?', answer: 'Yes, you can edit inputs or styles inside pine script editor.' }],
        submittedBy: 'lazytrader@gmail.com'
      },
      {
        name: 'Smart Money Concepts Suite',
        listingType: 'Indicator',
        category: catMap['Indicators'],
        platform: platMap['TradingView'],
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
        tags: ['smc', 'ict', 'orderblock', 'fvg', 'market-structure'],
        author: 'LuxQuant Labs',
        affiliateUrl: 'https://luxquant.com/?ref=ind_hub',
        imageUrl: 'https://placehold.co/800x400/1a1a1a/F59E0B?text=SMC+Suite',
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
        ],
        submittedBy: 'support@luxquant.com'
      },
      {
        name: 'ICT Killzones Overlay',
        listingType: 'Indicator',
        category: catMap['Indicators'],
        platform: platMap['TradingView'],
        description: 'Visual highlights of key institutional trading sessions (London, New York, Asia).',
        longDescription: 'A scheduling overlay marking the exact hours when major volume injections occur. Automatically aligns to local exchange times, including GMT shifts.',
        assetClass: ['Forex', 'Gold', 'Futures'],
        strategyType: ['Price Action', 'Day Trading'],
        timeframes: ['M1', 'M5', 'M15', 'H1'],
        difficulty: 'Intermediate',
        price: 0,
        pricingModel: 'Free',
        tags: ['killzone', 'session', 'london-session', 'nyse-trade'],
        author: 'InnerCircle Dev',
        imageUrl: 'https://placehold.co/800x400/111/10B981?text=Killzones',
        backtestData: {
          winRate: 69,
          auditStatus: 'Unaudited'
        },
        pros: ['Clean layouts', 'Dynamic timezone shifts'],
        cons: ['Visual overlays only, no statistical signals'],
        faqs: [{ question: 'Does this generate triggers?', answer: 'No, it provides visual session boundaries to help you contextualize trades.' }],
        submittedBy: 'innercirclecoder@gmail.com'
      },
      {
        name: 'Volume Profile Pro',
        listingType: 'Indicator',
        category: catMap['Indicators'],
        platform: platMap['MetaTrader 5'],
        description: 'Dynamic horizontal bar arrays showing precise point of control (POC) volume peaks.',
        longDescription: 'High frequency volume profiling system compiling transaction ticks at exact price nodes. Maps out the Point of Control (POC), High Volume Nodes (HVN) and Low Volume Nodes (LVN) to determine strong price magnets.',
        assetClass: ['Stocks', 'Indices', 'Futures'],
        strategyType: ['Volume', 'Price Action'],
        timeframes: ['H1', 'H4', 'D1'],
        difficulty: 'Advanced',
        price: 39,
        pricingModel: 'One-time',
        tags: ['volume-profile', 'poc', 'market-profile', 'mt5-scripts'],
        author: 'MQL Quant',
        imageUrl: 'https://placehold.co/800x400/222/FFF?text=Volume+Profile+Pro',
        backtestData: {
          winRate: 65,
          auditStatus: 'Unaudited'
        },
        pros: ['Real tick volume calculations', 'Highly stable code'],
        cons: ['Cannot run on standard MT4 core due to platform limits'],
        faqs: [{ question: 'Is raw tick data required?', answer: 'Yes, your broker must supply historical ticks to calculate high resolution bars.' }],
        submittedBy: 'mqlquant@gmail.com'
      },
      {
        name: 'Multi-Timeframe RSI Ribbon',
        listingType: 'Indicator',
        category: catMap['Indicators'],
        platform: platMap['TradingView'],
        description: 'Unites 4 separate RSI timeframes into a unified visual ribbon overlay.',
        longDescription: 'A smooth trend indicator reading RSI values from the 15m, 1h, 4h, and D1 timeframes concurrently to determine pure, non-lagging macroscopic trend direction.',
        assetClass: ['Crypto', 'Forex', 'Stocks', 'Indices'],
        strategyType: ['Momentum', 'Trend'],
        timeframes: ['M5', 'M15', 'H1', 'H4'],
        difficulty: 'Beginner',
        price: 0,
        pricingModel: 'Free',
        tags: ['rsi', 'multi-timeframe', 'ribbon', 'momentum'],
        author: 'PineMaster',
        imageUrl: 'https://placehold.co/800x400/171B26/3B82F6?text=RSI+Ribbon',
        backtestData: {
          winRate: 61,
          auditStatus: 'Unaudited'
        },
        pros: ['Combats local market noise', 'Beginner friendly'],
        cons: ['Lag in fast crash events'],
        faqs: [{ question: 'What is the default RSI length?', answer: 'The default length is 14 bars across all underlying frames.' }],
        submittedBy: 'pinemaster@outlook.com'
      },
      {
        name: 'Order Block institutional Detector',
        listingType: 'Indicator',
        category: catMap['Indicators'],
        platform: platMap['TradingView'],
        description: 'Auto marks mitigation blocks and key order block structural price pivots.',
        longDescription: 'Monitors aggressive candle bursts associated with corporate or bank orders injections, highlighting these critical demand and supply levels on chart layouts.',
        assetClass: ['Forex', 'Crypto', 'Stocks'],
        strategyType: ['Smart Money', 'Trend'],
        timeframes: ['H1', 'H4', 'D1'],
        difficulty: 'Advanced',
        price: 35,
        pricingModel: 'Monthly',
        isVerified: true,
        tags: ['orderblock', 'smc', 'demand-zone', 'institutions'],
        author: 'Matrix Algo Labs',
        imageUrl: 'https://placehold.co/800x400/111/EF4444?text=OB+Detector',
        backtestData: {
          winRate: 72,
          sharpeRatio: 1.9,
          maxDrawdown: 9,
          auditStatus: 'Verified'
        },
        pros: ['Tracks historical supply ranges', 'Immediate notifications'],
        cons: ['Expensive entry fee'],
        faqs: [{ question: 'How is an Order Block defined here?', answer: 'Calculated using high volume candles breaking short-term local structures.' }],
        submittedBy: 'matrixalgo@outlook.com'
      },
      {
        name: 'Fair Value Gap Finder',
        listingType: 'Indicator',
        category: catMap['Indicators'],
        platform: platMap['TradingView'],
        description: 'Finds unbalanced price regions (FVGs) and prints alert lines automapped.',
        longDescription: 'Scours candles to reveal Fair Value Gaps (3-candle imbalance patterns) and prints horizontal support lines until the gap is completely mitigated by future price action.',
        assetClass: ['Forex', 'Crypto'],
        strategyType: ['Price Action', 'reversal'],
        timeframes: ['M5', 'M15', 'H1'],
        difficulty: 'Beginner',
        price: 0,
        pricingModel: 'Free',
        tags: ['fvg', 'fair-value-gap', 'imbalance', 'liquidity'],
        author: 'PineAlchemy',
        imageUrl: 'https://placehold.co/800x400/171B26/3B82F6?text=FVG+Finder',
        backtestData: {
          winRate: 64,
          auditStatus: 'Unaudited'
        },
        pros: ['Saves significant plotting time', 'Clean interface'],
        cons: ['Overcrowded charts on low timeframes'],
        faqs: [{ question: 'What is gap mitigation?', answer: 'When future candles swing back to touch or fill the gap imbalance.' }],
        submittedBy: 'pinealchemy@gmail.com'
      },
      {
        name: 'ATR Trailing Stop Pro',
        listingType: 'Indicator',
        category: catMap['Indicators'],
        platform: platMap['MetaTrader 4'],
        description: 'Calculates volatility trailing stops using Average True Range (ATR) multipliers.',
        longDescription: 'An exceptionally reliable risk management script that displays custom trailing stop-loss points based on market volatility spikes. Great for trends.',
        assetClass: ['Crypto', 'Forex', 'Stocks', 'Indices', 'Gold'],
        strategyType: ['Trend', 'Swing'],
        timeframes: ['H1', 'H4', 'D1'],
        difficulty: 'Beginner',
        price: 25,
        pricingModel: 'One-time',
        tags: ['atr', 'trailing-stop', 'stop-loss', 'risk-management'],
        author: 'MetaTrader Developers',
        imageUrl: 'https://placehold.co/800x400/111/10B981?text=ATR+Trailing+Stop',
        backtestData: {
          winRate: 63,
          auditStatus: 'Unaudited'
        },
        pros: ['Stops emotional stop-loss shifts', 'Compatible with MT4 mobile apps'],
        cons: ['Gives up a portion of trend profit at exit'],
        faqs: [{ question: 'What ATR multiplier is standard?', answer: 'A multiplier of 2.5 or 3 is default for daily trends.' }],
        submittedBy: 'support@mtdevs.com'
      },

      // 11-14: EAs (Expert Advisors)
      {
        name: 'Gold EA Scalper Plus',
        listingType: 'EA',
        category: catMap['Expert Advisors'],
        platform: platMap['MetaTrader 4'],
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
        tags: ['gold-ea', 'xauusd', 'automated-trading', 'expert-advisor', 'grid-free'],
        author: 'XAU Algorithmic Group',
        imageUrl: 'https://placehold.co/800x400/004B87/EAB308?text=Gold+EA+Scalper',
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
        faqs: [{ question: 'Is a VPS required?', answer: 'Yes, a Virtual Private Server is highly advised to prevent network disconnects.' }],
        submittedBy: 'sales@xaualgo.com'
      },
      {
        name: 'Forex Trend Rider EA',
        listingType: 'EA',
        category: catMap['Expert Advisors'],
        platform: platMap['MetaTrader 5'],
        description: 'Auto scans major forex pairs to execute trend rides. Curve-fitted warnings issued.',
        longDescription: 'MetaTrader 5 Expert Advisor targeting macroscopic trends. Multi-pair analysis includes EUR/USD, GBP/USD, and AUD/USD, riding swings over H1 cycles.',
        assetClass: ['Forex'],
        strategyType: ['Trend', 'Swing'],
        timeframes: ['H1', 'H4'],
        difficulty: 'Advanced',
        price: 149,
        pricingModel: 'Yearly',
        tags: ['forex-ea', 'trend-following', 'automated-swing', 'mt5-ea'],
        author: 'FX Auto-Pilot Systems',
        imageUrl: 'https://placehold.co/800x400/039BE5/FFF?text=Forex+Trend+Rider',
        backtestData: {
          winRate: 59,
          sharpeRatio: 0.9,
          maxDrawdown: 35, // High drawdown
          profitFactor: 1.2,
          totalTrades: 450,
          auditStatus: 'Suspicious',
          auditNotes: 'Manual audit revealed high drawdowns and potential grid-recovery martingale mechanisms hidden in code logs.'
        },
        pros: ['Operates 24/5 on forex', 'Low latency execution'],
        cons: ['Extremely high drawdowns', 'Suspicious backtest curve audit logs'],
        faqs: [{ question: 'Why is this listed as Suspicious?', answer: 'The backtests include grid recovery structures that can deplete accounts under rare high-volatility conditions.' }],
        submittedBy: 'fxautopilot@fxsystems.com'
      },
      {
        name: 'Breakout Sniper EA',
        listingType: 'EA',
        category: catMap['Expert Advisors'],
        platform: platMap['MetaTrader 4'],
        description: 'Automated pending order system matching intraday support breaks.',
        longDescription: 'MT4 script that places secure straddle pending buy/sell orders around London pre-market Consolidation boundaries, picking up momentum bursts in either direction.',
        assetClass: ['Forex', 'Indices'],
        strategyType: ['Breakout', 'Day Trading'],
        timeframes: ['M30', 'H1'],
        difficulty: 'Intermediate',
        price: 89,
        pricingModel: 'One-time',
        tags: ['breakout-ea', 'london-breakout', 'pending-orders', 'scalping-bot'],
        author: 'Sniper Algorics',
        imageUrl: 'https://placehold.co/800x400/1E1E24/FFF?text=Breakout+Sniper',
        backtestData: {
          winRate: 55,
          maxDrawdown: 10,
          auditStatus: 'Unaudited'
        },
        pros: ['Stops run before NY opens', 'Simple controls'],
        cons: ['Slippage in high news impact days'],
        faqs: [{ question: 'Can I start with $100?', answer: 'Yes, micro-lot allocations (0.01) allow starting with modest deposits.' }],
        submittedBy: 'sniperalgos@gmail.com'
      },
      {
        name: 'Grid Master EA Multi',
        listingType: 'EA',
        category: catMap['Expert Advisors'],
        platform: platMap['MetaTrader 5'],
        description: 'Fully customizable grid bot overlay for MT5. Martingale aspects noted.',
        longDescription: 'Builds secure customizable grids of Buy and Sell contracts to profit from side-scrolling markets. Warning: use high risk management budgets.',
        assetClass: ['Crypto', 'Forex'],
        strategyType: ['Grid', 'DCA'],
        timeframes: ['M5', 'M15', 'M30'],
        difficulty: 'Expert',
        price: 299,
        pricingModel: 'One-time',
        tags: ['grid-ea', 'martingale', 'mt5-grid', 'automated-forex'],
        author: 'Mesh Automations',
        imageUrl: 'https://placehold.co/800x400/212121/FFF?text=Grid+Master+EA',
        backtestData: {
          winRate: 78,
          maxDrawdown: 42, // Dangerous
          auditStatus: 'Suspicious',
          auditNotes: 'Standard grid logic triggers huge floating losses if market starts deep runs without retracing.'
        },
        pros: ['Extremely active daily profits', 'Works well in ranging markets'],
        cons: ['Severe drawdowns during trend launches', 'Requires high minimal capital setup'],
        faqs: [{ question: 'Is this high dangerous?', answer: 'Yes, grid systems execute contracts without stop loss, making them prone to margin calls if trends continue running.' }],
        submittedBy: 'gridmaster@meshalgos.com'
      },

      // 15-17: BOTS
      {
        name: '3Commas DCA Bot Setup',
        listingType: 'Bot',
        category: catMap['Trading Bots'],
        platform: platMap['3Commas'],
        description: 'Ready-to-copy API DCA (Dollar-Cost-Averaging) configuration files for Binance spot.',
        longDescription: 'DCA configurations mapped to filter crypto drops during minor consolidations, buying dips and taking profit cumulatively.',
        assetClass: ['Crypto'],
        strategyType: ['DCA', 'Trend'],
        timeframes: ['H1', 'H4'],
        difficulty: 'Beginner',
        price: 0,
        pricingModel: 'Free',
        tags: ['3commas', 'dca', 'crypto-bot', 'copy-config'],
        author: 'DCA Wizards',
        imageUrl: 'https://placehold.co/800x400/0288D1/FFF?text=3Commas+Bot',
        backtestData: {
          winRate: 64,
          auditStatus: 'Unaudited'
        },
        pros: ['Zero software setups', 'Great in bullish cycles'],
        cons: ['Can drag balances down in deep bear markets'],
        faqs: [{ question: 'What is DCA?', answer: 'Dollar-Cost Averaging: buying small buckets of an asset as price descends to average your entry point.' }],
        submittedBy: 'dcawizards@gmail.com'
      },
      {
        name: 'Pionex Automated Grid Bot',
        listingType: 'Bot',
        category: catMap['Trading Bots'],
        platform: platMap['Pionex'],
        description: 'Precompiled algorithmic bounds configuration for BTC/USDT grid bots.',
        longDescription: 'A setup guide mapping optimized grid intervals on Pionex exchange to execute continuous microscopic scalp orders.',
        assetClass: ['Crypto'],
        strategyType: ['Grid', 'Arbitrage'],
        timeframes: ['M5', 'M30'],
        difficulty: 'Beginner',
        price: 0,
        pricingModel: 'Free',
        tags: ['pionex', 'grid-bot', 'crypto-exchange', 'automated-bids'],
        author: 'Grid Pioneers',
        imageUrl: 'https://placehold.co/800x400/FF5722/FFF?text=Pionex+Grid',
        backtestData: {
          winRate: 71,
          auditStatus: 'Unaudited'
        },
        pros: ['Completely free tool setups', 'Easy to master'],
        cons: ['Trapped in orders locks if price drops below range bounds'],
        faqs: [{ question: 'What is range breakout?', answer: 'If price breaks bounds, the bot pauses until price returns inside the grid limits.' }],
        submittedBy: 'gridpioneers@outlook.com'
      },
      {
        name: 'Cryptohopper Momentum Bot Config',
        listingType: 'Bot',
        category: catMap['Trading Bots'],
        platform: platMap['Cryptohopper'],
        description: 'High-frequency momentum trend spot trading configurations.',
        longDescription: 'A dynamic config setup designed for Cryptohopper cloud engine, buying breakout bursts across top 50 Altcoins.',
        assetClass: ['Crypto'],
        strategyType: ['Momentum', 'Breakout'],
        timeframes: ['M15', 'H1'],
        difficulty: 'Intermediate',
        price: 29,
        pricingModel: 'Monthly',
        tags: ['cryptohopper', 'altcoins', 'spot-trading', 'cloud-bot'],
        author: 'Nimbus Algos',
        imageUrl: 'https://placehold.co/800x400/3F51B5/FFF?text=Cryptohopper+Nimbus',
        backtestData: {
          winRate: 66,
          auditStatus: 'Unaudited'
        },
        pros: ['Cloud hosted, offline executions', 'Multi-coin portfolio tracing'],
        cons: ['Not recommended during sudden market flashes'],
        faqs: [{ question: 'Does it run 24/7?', answer: 'Yes, Cryptohopper is cloud-based and operates with secure API keys.' }],
        submittedBy: 'nimbus@nimbusalgo.com'
      },

      // 18-20: SIGNALS
      {
        name: 'FX Premium Signals Feed',
        listingType: 'Signal',
        category: catMap['Signals'],
        platform: platMap['MetaTrader 4'],
        description: 'Elite real-time Telegram signal channel for major and minor Forex pairs.',
        longDescription: 'Automated API and analyst-written trading alerts pushed direct to Telegram with explicit entries, stops, and up to 3 distinct take-profit targets.',
        assetClass: ['Forex'],
        strategyType: ['Swing', 'Momentum'],
        timeframes: ['H1', 'H4'],
        difficulty: 'Beginner',
        price: 49,
        pricingModel: 'Monthly',
        tags: ['signals', ' telegram-signals', 'forex-alerts', 'copy-trading'],
        author: 'FX Alpha Signal Group',
        imageUrl: 'https://placehold.co/800x400/004B87/FFF?text=FX+Signals+Premium',
        backtestData: {
          winRate: 72,
          auditStatus: 'Verified',
          auditNotes: 'Our analyst audited past 1,200 signal feeds from Telegram and confirmed massive profitable months.'
        },
        pros: ['Immediate mobile alerts', 'Highly accurate risk metrics'],
        cons: ['Requires prompt manual execution upon receiving alerts'],
        faqs: [{ question: 'How many alerts are daily?', answer: 'Typically 3 to 5 highly curated setups are released daily.' }],
        submittedBy: 'info@fxalpha.com'
      },
      {
        name: 'Crypto Scalp Telegram signals',
        listingType: 'Signal',
        category: catMap['Signals'],
        platform: platMap['Cryptohopper'],
        description: 'Intraday scalp alerts for Altcoins futures leverage channels.',
        longDescription: 'High frequency leverage signals designed for active crypto scalp traders. Delivered via Telegram or direct Discord webhooks.',
        assetClass: ['Crypto'],
        strategyType: ['Scalping', 'Day Trading'],
        timeframes: ['M5', 'M15'],
        difficulty: 'Intermediate',
        price: 39,
        pricingModel: 'Monthly',
        tags: ['crypto-signals', ' scalp-signals', 'discord-pushed', 'futures-alerts'],
        author: 'CoinBurst Signals',
        imageUrl: 'https://placehold.co/800x400/3F51B5/FFF?text=Crypto+Scalp+Alerts',
        backtestData: {
          winRate: 68,
          auditStatus: 'Unaudited'
        },
        pros: ['Extremely rapid alert distributions', 'High leverage targets'],
        cons: ['Incredibly volatility risks during market dumps'],
        faqs: [{ question: 'What exchanges are covered?', answer: 'Mainly Binance, Bybit, and OKX futures contracts.' }],
        submittedBy: 'coinburst@gmail.com'
      },
      {
        name: 'Gold & XAU Whatsapp Signals',
        listingType: 'Signal',
        category: catMap['Signals'],
        platform: platMap['MetaTrader 5'],
        description: 'Curated precious metals (Gold, Silver) signal feed sent via WhatsApp.',
        longDescription: 'Focuses entirely on gold intraday swing trades, highlighting NYC session triggers.',
        assetClass: ['Gold', 'Silver'],
        strategyType: ['Day Trading', 'Swing'],
        timeframes: ['M30', 'H1'],
        difficulty: 'Intermediate',
        price: 59,
        pricingModel: 'Monthly',
        tags: ['gold-signals', 'xau-alerts', 'whatsapp-trading', 'precious-metals'],
        author: 'XAU Spot Team',
        imageUrl: 'https://placehold.co/800x400/212121/FFF?text=Gold+Signals',
        backtestData: {
          winRate: 74,
          auditStatus: 'Verified'
        },
        pros: ['Highly targeted gold focus', 'Excellent monthly yields'],
        cons: ['High monthly cost subscription fee'],
        faqs: [{ question: 'Can I copy these trades to MT4?', answer: 'Yes, these are price logs that you can input manually on any setup.' }],
        submittedBy: 'goldspot@gmail.com'
      },

      // 21-23: STRATEGIES
      {
        name: 'Wyckoff Accumulation systematic pack',
        listingType: 'Strategy',
        category: catMap['Strategies'],
        platform: platMap['TradingView'],
        description: 'Complete playbook and custom markers for Wyckoff cycle ranges.',
        longDescription: 'Visual guide and candle highlighting script aimed at determining spring accumulation zones first, ahead of rallies.',
        assetClass: ['Stocks', 'Crypto', 'ETFs'],
        strategyType: ['Swing', 'Position'],
        timeframes: ['H4', 'D1'],
        difficulty: 'Advanced',
        price: 0,
        pricingModel: 'Free',
        tags: ['wyckoff', 'accumulation', 'market-cycles', 'swing-playbook'],
        author: 'Quantology Group',
        imageUrl: 'https://placehold.co/800x400/171B26/FFF?text=Wyckoff+Strategy',
        backtestData: {
          winRate: 65,
          auditStatus: 'Unaudited'
        },
        pros: ['In-depth comprehensive PDF guide included', 'No pricing fees'],
        cons: ['Signals take weeks to mature'],
        faqs: [{ question: 'What is spring accumulation?', answer: 'A final stop-hunt trap clearing out prior support before a strong markup.' }],
        submittedBy: 'quantology@gmail.com'
      },
      {
        name: 'London Breakout Playbook System',
        listingType: 'Strategy',
        category: catMap['Strategies'],
        platform: platMap['MetaTrader 4'],
        description: 'Traditional intraday breakout logic mapping London hour candle expansions.',
        longDescription: 'SystemATIC trading guide mapping pre-open consolidations and trading breakouts of London high/low ranges.',
        assetClass: ['Forex'],
        strategyType: ['Day Trading', 'Breakout'],
        timeframes: ['M15', 'M30'],
        difficulty: 'Intermediate',
        price: 79,
        pricingModel: 'One-time',
        isVerified: true,
        tags: ['london-breakout', 'intraday-forex', 'london-open', 'volatility-breaks'],
        author: 'FX Guild',
        imageUrl: 'https://placehold.co/800x400/004B87/FFF?text=London+Breakout+Playbook',
        backtestData: {
          winRate: 67,
          sharpeRatio: 1.6,
          maxDrawdown: 11,
          auditStatus: 'Verified'
        },
        pros: ['Takes under 2 hours daily', 'Highly repeatable logic'],
        cons: ['Requires trading at specific morning hours (GMT)'],
        faqs: [{ question: 'What asset counts?', answer: 'Best on GBP/USD and EUR/USD.' }],
        submittedBy: 'fxguild@fx.com'
      },
      {
        name: 'BTC Dominance systematic Swing Strategy',
        listingType: 'Strategy',
        category: catMap['Strategies'],
        platform: platMap['TradingView'],
        description: 'Tracks market cap weight ratios to optimize altcoin position entry timings.',
        longDescription: 'Algorithmic indicators scoring capitulation and altseason points based on BTC Dominance Cap ratios.',
        assetClass: ['Crypto'],
        strategyType: ['Swing', 'Position'],
        timeframes: ['H4', 'D1', 'W1'],
        difficulty: 'Advanced',
        price: 29,
        pricingModel: 'Monthly',
        tags: ['btc-dominance', 'altseason', 'crypto-cycles', 'dominance-ratio'],
        author: 'Altcoins Quant',
        imageUrl: 'https://placehold.co/800x400/171B26/F59E0B?text=Dominance+Strategy',
        backtestData: {
          winRate: 63,
          auditStatus: 'Unaudited'
        },
        pros: ['Maximizes Alts multipliers', 'Avoids bear trap allocations'],
        cons: ['Relying heavily on macro cycles'],
        faqs: [{ question: 'Does it support leverage?', answer: 'Designed primarily for Spot portfolio rebalancing, but indices can be levered.' }],
        submittedBy: 'altquant@gmail.com'
      },

      // 24-25: SCREENERS
      {
        name: 'Breakout Screener Pro',
        listingType: 'Screener',
        category: catMap['Screeners'],
        platform: platMap['TradingView'],
        description: 'Real-time multi-asset sidebar panel showing breakout status of 20+ pairs.',
        longDescription: 'Automated sidebar dashboard that displays multi-asset breakouts matching customized ATR and MACD expansions.',
        assetClass: ['Stocks', 'Crypto', 'Forex'],
        strategyType: ['Breakout', 'Volatility'],
        timeframes: ['H1', 'H4', 'D1'],
        difficulty: 'Intermediate',
        price: 19,
        pricingModel: 'Monthly',
        tags: ['screener', 'scanner', 'breakout-screener', 'chart-panel'],
        author: 'Screener Labs',
        imageUrl: 'https://placehold.co/800x400/111/FFF?text=Breakout+Screener',
        backtestData: {
          winRate: 64,
          auditStatus: 'Unaudited'
        },
        pros: ['Reduces chart hopping times', 'Intuitive visual color blocks'],
        cons: ['Slight alert delays during massive network spikes'],
        faqs: [{ question: 'How many tokens can I watch?', answer: 'Up to 50 active assets can be mapped onto your dashboard simultaneously.' }],
        submittedBy: 'screenerlabs@quant.com'
      },
      {
        name: 'RSI Oversold scanner toolbar',
        listingType: 'Screener',
        category: catMap['Screeners'],
        platform: platMap['TradingView'],
        description: 'Displays a table of Altcoins currently resting below RSI 30 thresholds.',
        longDescription: 'Excellent asset screening panel displaying real-time tabular indices of oversold or overbought RSI limits.',
        assetClass: ['Crypto', 'Stocks'],
        strategyType: ['Reversal', 'Mean Reversion'],
        timeframes: ['M15', 'H1', 'H4'],
        difficulty: 'Beginner',
        price: 0,
        pricingModel: 'Free',
        tags: ['rsi-scanner', 'oversold', 'buy-dip', 'panel-widget'],
        author: 'AltScreener',
        imageUrl: 'https://placehold.co/800x400/171B26/3B82F6?text=RSI+Scanner',
        backtestData: {
          winRate: 62,
          auditStatus: 'Unaudited'
        },
        pros: ['Completely zero cost', 'Highly visual layout'],
        cons: ['Altcoins can rest in oversold bands for weeks before bouncing'],
        faqs: [{ question: 'What is oversold limit?', answer: 'Standard oversold triggers at RSI values under 30.' }],
        submittedBy: 'altscreener@alts.com'
      },

      // 26-27: SCRIPTS
      {
        name: 'Automated Fibonacci alert trigger',
        listingType: 'Script',
        category: catMap['Scripts & Alerts'],
        platform: platMap['TradingView'],
        description: 'Auto plots Fibonacci retracement coordinates and sets webhooks triggers.',
        longDescription: 'An automated indicator script that draws Swing High/Low Fibonacci extensions and generates JSON push webhook payloads when key golden zones (0.618) are hit.',
        assetClass: ['Crypto', 'Forex', 'Gold'],
        strategyType: ['Price Action', 'Reversal'],
        timeframes: ['H1', 'H4', 'D1'],
        difficulty: 'Intermediate',
        price: 0,
        pricingModel: 'Free',
        tags: ['fibonacci', 'golden-ratio', 'retracement', 'webhooks-alerts'],
        author: 'AlertForge Systems',
        imageUrl: 'https://placehold.co/800x400/171B26/EAB308?text=Fibonacci+Algos',
        backtestData: {
          winRate: 63,
          auditStatus: 'Unaudited'
        },
        pros: ['Eliminates manual trace discrepancies', 'Webhook payload auto-creation'],
        cons: ['Heavy lagging coordinates during structural breakouts'],
        faqs: [{ question: 'What are webhooks useful for?', answer: 'They let you send automated signals from TradingView to bots like 3Commas or Telegram.' }],
        submittedBy: 'contact@alertforge.com'
      },
      {
        name: 'Daily Range metrics Alert',
        listingType: 'Script',
        category: catMap['Scripts & Alerts'],
        platform: platMap['TradingView'],
        description: 'Highlights the average daily range and rings alert bells upon cap breaches.',
        longDescription: 'Calculates the historical Average Daily Range (ADR) and creates visual popups if trading volume exhausts the target boundary during forex blocks.',
        assetClass: ['Forex'],
        strategyType: ['Volatility', 'Mean Reversion'],
        timeframes: ['M5', 'M15', 'H1'],
        difficulty: 'Beginner',
        price: 0,
        pricingModel: 'Free',
        tags: ['adr-alerts', 'range-triggers', 'volatility-measurer'],
        author: 'PineCoders Collective',
        imageUrl: 'https://placehold.co/800x400/222/FFF?text=ADR+Alerts',
        backtestData: {
          winRate: 60,
          auditStatus: 'Unaudited'
        },
        pros: ['Perfect for mean reversion traders', 'Clean alerts'],
        cons: ['Range can be completely smashed during major FOMC news'],
        faqs: [{ question: 'How is range calculated?', answer: 'Typically based on high/low differences averaged over a 14-day history.' }],
        submittedBy: 'pinecoders@outlook.com'
      },

      // 28-29: COPY TRADING
      {
        name: 'Top Trader cTrader copy package',
        listingType: 'CopyTrading',
        category: catMap['Copy Trading'],
        platform: platMap['cTrader'],
        description: 'Join raw institutional-grade index social trades copy setups.',
        longDescription: 'An automated master copy investor pool trading indices (US30, GER40) using diversified systemic swing metrics.',
        assetClass: ['Forex', 'Indices'],
        strategyType: ['Swing', 'Day Trading'],
        timeframes: ['M30', 'H1', 'H4'],
        difficulty: 'Beginner',
        price: 0,
        pricingModel: 'Free',
        tags: ['ctrader', 'copy-trading', 'index-investment', 'social-trades'],
        author: 'Alpha-X Capital',
        imageUrl: 'https://placehold.co/800x400/1E1E24/EAB308?text=ctrader+copy',
        backtestData: {
          winRate: 65,
          auditStatus: 'Unaudited'
        },
        pros: ['100% hands-free copy operations', 'No sign-up or software costs'],
        cons: ['Performance commission fees cut profit slightly', 'Depends on broker alignment'],
        faqs: [{ question: 'Is it completely auto?', answer: 'Yes, trades executed on Master accounts mirror onto yours in real-time.' }],
        submittedBy: 'info@alphaxcapital.net'
      },
      {
        name: 'PropFirm Systematic Pass Strategy',
        listingType: 'CopyTrading',
        category: catMap['Copy Trading'],
        platform: platMap['MetaTrader 5'],
        description: 'Swing/Intraday EA copy feed aimed at clearing prop company drawdown tests.',
        longDescription: 'Copier trading signals optimized strictly for managing and clearing FTMO, FundedNext, and funded challenge thresholds. Fully audited drawdowns capped under 4% per cycle.',
        assetClass: ['Forex', 'Indices'],
        strategyType: ['Swing', 'Day Trading'],
        timeframes: ['H1', 'H4'],
        difficulty: 'Advanced',
        price: 149,
        pricingModel: 'One-time',
        isVerified: true,
        tags: ['prop-firm', 'pass-challenge', 'ftmo-copier', 'mt5-copier'],
        author: 'PropMaster Algos',
        imageUrl: 'https://placehold.co/800x400/039BE5/EAB308?text=Propfirm+Pass',
        backtestData: {
          winRate: 73,
          sharpeRatio: 2.3,
          maxDrawdown: 4, // Outstanding
          profitFactor: 2.5,
          totalTrades: 320,
          auditStatus: 'Verified',
          forwardTestActive: true
        },
        pros: ['Strict structural target bounds', 'Prop drawdown automated safety locks'],
        cons: ['Expensive entry setup fee', 'Alert delay on custom copy relays'],
        faqs: [{ question: 'Are all prop companies accepted?', answer: 'Yes, fully compatible with MT5 terminal brokers.' }],
        submittedBy: 'propmasteralgo@gmail.com'
      },

      // 30: COURSE
      {
        name: 'Price Action mastery syllabus',
        listingType: 'Course',
        category: catMap['Education & Courses'],
        platform: platMap['TradingView'],
        description: 'Complete syllabus and live webinar sessions tracking liquidity concepts and ICT systems.',
        longDescription: 'Our hallmark quantified training program mapping price chart liquidity logic, institutional draw on liquidity, and market traps.',
        assetClass: ['Forex', 'Stocks', 'Crypto', 'Indices', 'Gold', 'Futures'],
        strategyType: ['Price Action', 'Smart Money'],
        timeframes: ['M5', 'H1', 'D1'],
        difficulty: 'Beginner',
        price: 99,
        pricingModel: 'One-time',
        tags: ['course', 'education', 'price-action-course', 'ict-system-class', 'quant-school'],
        author: 'Quant Academy',
        imageUrl: 'https://placehold.co/800x400/171B26/3B82F6?text=Price+Action+Course',
        backtestData: {
          winRate: 0,
          auditStatus: 'Unaudited'
        },
        pros: ['30+ hours of video coaching webinars', 'Lifetime membership to discord forums'],
        cons: ['Requires extensive studying and practice sessions'],
        faqs: [{ question: 'Are there homework audits?', answer: 'Yes, homework assignments are audited by expert traders in our discord community.' }],
        submittedBy: 'quantacademy@outlook.com'
      }
    ];

    const seededIndicators = await Indicator.create(indicatorsData);
    console.log(`✓ [Seed Engine] Seeded ${seededIndicators.length} primary indicators.`);

    // 5. Insert Reviews (3 unique reviews per indicator = 90 Reviews)
    console.log('🔄 [Seed Engine] Seeding community reviews...');
    const reviewerPool = [
      { name: 'David Mercer', email: 'davidm@gmail.com', type: 'Pro', stars: 5, body: 'Outstanding structural mapping. This completely reshaped how I trade forex sessions daily. High fidelity lines that save hours of chart setups!' },
      { name: 'Sarah Connor', email: 'sarahc@outlook.com', type: 'Intermediate', stars: 4, body: 'Extremely reliable scripts. Had some false entries during tight consolidating markets, but when the trend took off, the targets were hit smoothly.' },
      { name: 'Liam Neeson', email: 'liamn@quant.com', type: 'Pro', stars: 5, body: 'The metrics matched up completely on my backtest engine. Very stable code, zero repainting on close candles, well worth the entry price!' },
      { name: 'Pratik Kumar', email: 'pratik@gmail.com', type: 'Beginner', stars: 4, body: 'A bit difficult for my beginner level at first, but with help from the author and reading guides, I have been profitable over my 30-day sandbox trial.' },
      { name: 'John Doe', email: 'john@yahoo.com', type: 'Intermediate', stars: 2, body: 'The drawdown was way too heavy during FOMC announcements. The bot has grid tendencies that can wipe balances out if not managed attentively.' },
      { name: 'Elon M', email: 'elon@x.com', type: 'Institutional', stars: 5, body: 'The win rates audited represent institutional level mathematical setups. Exceedingly clean, high frequency execution, extremely robust API structures.' }
    ];

    const reviewsData = [];
    for (const ind of seededIndicators) {
      // Pick 3 random reviewers to write reviews
      const selected = reviewerPool.sort(() => 0.5 - Math.random()).slice(0, 3);
      selected.forEach(rev => {
        // Adjust stars slightly depending on the indicator pricing or characteristics
        let finalRating = rev.stars;
        if (ind.isScamFlagged || (ind.backtestData && ind.backtestData.auditStatus === 'Suspicious')) {
          finalRating = Math.max(1, finalRating - 2); // Downrate scam/suspicious tools
        }

        reviewsData.push({
          indicatorId: ind._id,
          reviewerName: rev.name,
          reviewerEmail: `${ind.slug}_${rev.email}`, // prevent unique index collision
          reviewerType: rev.type,
          rating: finalRating,
          title: finalRating >= 4 ? 'A Must-Have for Systematic Traders' : 'An Unbalanced Algos Setup',
          body: rev.body,
          tradingPeriod: '45 days',
          assetTraded: ind.assetClass[0] || 'BTC/USDT',
          timeframeUsed: ind.timeframes[0] || 'H1',
          profitableForReviewer: finalRating >= 4,
          wouldRecommend: finalRating >= 4,
          helpful: Math.floor(Math.random() * 25),
          notHelpful: Math.floor(Math.random() * 3),
          verified: finalRating >= 4,
          isScam: ind.isScamFlagged,
          platform: ind.platform ? ind.platform.toString() : 'Web'
        });
      });
    }

    const seededReviews = await Review.create(reviewsData);
    console.log(`✓ [Seed Engine] Seeded ${seededReviews.length} verified reviews.`);

    // Re-trigger static calculateAverageRating on all indicators to update actual reviews totals & averages
    console.log('🔄 [Seed Engine] Recalculating averages...');
    for (const ind of seededIndicators) {
      await Review.calculateAverageRating(ind._id);
    }
    console.log('✓ [Seed Engine] Indicators score calculations synchronized.');

    // 6. Insert Signals (3 Signal records in the independent Signal collection)
    console.log('🔄 [Seed Engine] Seeding Signal feeds...');
    const seededSignals = await Signal.create([
      {
        name: 'Prime Forex Signals Feed',
        provider: 'FX Alpha Group',
        asset: 'EUR/USD',
        direction: 'Buy',
        entry: 1.0850,
        stopLoss: 1.0810,
        takeProfit1: 1.0890,
        takeProfit2: 1.0920,
        takeProfit3: 1.0960,
        timeframe: 'H1',
        signalType: 'Combined',
        deliveryMethod: 'Telegram',
        isActive: true,
        winRateHistoric: 72,
        totalSignalsIssued: 1200,
        successfulSignals: 864,
        price: 49,
        affiliateUrl: 'https://telegram.me/fx_alpha_premium'
      },
      {
        name: 'BTC Swing Leveraged signals',
        provider: 'CoinBurst Signals',
        asset: 'BTC/USDT',
        direction: 'Sell',
        entry: 67200,
        stopLoss: 68500,
        takeProfit1: 65800,
        takeProfit2: 64200,
        takeProfit3: 62000,
        timeframe: 'H4',
        signalType: 'AI',
        deliveryMethod: 'Discord',
        isActive: true,
        winRateHistoric: 68,
        totalSignalsIssued: 350,
        successfulSignals: 238,
        price: 39,
        affiliateUrl: 'https://discord.gg/coinburst_signals'
      },
      {
        name: 'XAU Gold Intraday Alerts',
        provider: 'XAU Spot Team',
        asset: 'GOLD',
        direction: 'Buy',
        entry: 2345.50,
        stopLoss: 2335.00,
        takeProfit1: 2355.00,
        takeProfit2: 2365.00,
        timeframe: 'M15',
        signalType: 'Technical',
        deliveryMethod: 'WhatsApp',
        isActive: true,
        winRateHistoric: 74,
        totalSignalsIssued: 500,
        successfulSignals: 370,
        price: 59,
        affiliateUrl: 'https://chat.whatsapp.com/gold_spot'
      }
    ]);
    console.log(`✓ [Seed Engine] Seeded ${seededSignals.length} active signal feeds.`);

    // 7. Insert Brokers (6 Brokers)
    console.log('🔄 [Seed Engine] Seeding Brokers affiliate list...');
    const seededBrokers = await BrokerAffiliate.create([
      {
        name: 'IC Markets',
        logo: 'https://placehold.co/150x80/282E32/FFF?text=IC+Markets',
        description: 'Global leading raw spreads retail broker. Unbelievably narrow spreads, high leverage caps, fast execution engines ideal for Expert Advisors.',
        regulatedBy: ['FCA', 'ASIC', 'CySEC'],
        licenseNumbers: ['385620'],
        assetsCovered: ['Forex', 'Crypto', 'Stocks', 'Indices', 'Commodities', 'Futures'],
        minDeposit: 200,
        platforms: ['MT4', 'MT5', 'cTrader'],
        spreadType: 'Raw',
        cpaCommission: 300,
        revenueShare: 0,
        rating: 4.7,
        trustScore: 95,
        affiliateUrl: 'https://icmarkets.com/?aff=indicatorhub',
        isRecommended: true,
        isFeatured: true
      },
      {
        name: 'Exness',
        logo: 'https://placehold.co/150x80/1E1E1E/EEE?text=Exness',
        description: 'Exceedingly popular multi-asset forex brokerage offering instant auto-withdrawal mechanisms, leverage models, and zero commission broker lines.',
        regulatedBy: ['FCA', 'CySEC'],
        licenseNumbers: ['735070'],
        assetsCovered: ['Forex', 'Crypto', 'Indices', 'Commodities'],
        minDeposit: 10,
        platforms: ['MT4', 'MT5'],
        spreadType: 'Variable',
        cpaCommission: 250,
        rating: 4.6,
        trustScore: 92,
        affiliateUrl: 'https://exness.com/?aff=indicatorhub',
        isRecommended: true,
        isFeatured: true
      },
      {
        name: 'Binance',
        logo: 'https://placehold.co/150x80/F0B90B/1E2026?text=Binance',
        description: 'The world’s largest and most secure cryptocurrency spot, perpetual swaps, and futures trading exchange with deepest liquidity orderbooks.',
        regulatedBy: ['Varies by country'],
        assetsCovered: ['Crypto', 'Futures'],
        minDeposit: 0,
        platforms: ['API connectors', 'Webtrader'],
        spreadType: 'Raw',
        cpaCommission: 0,
        revenueShare: 35,
        rating: 4.5,
        trustScore: 89,
        affiliateUrl: 'https://binance.com/?ref=indicatorhub',
        isRecommended: true
      },
      {
        name: 'Bybit',
        logo: 'https://placehold.co/150x80/12161A/FFB11A?text=Bybit',
        description: 'Extremely robust high frequency cryptocurrency futures, options, and CFD asset exchange featuring zero lag execution pipelines.',
        regulatedBy: ['VARA'],
        assetsCovered: ['Crypto', 'Futures', 'Forex'],
        minDeposit: 0,
        platforms: ['API connectors', 'Webtrader'],
        spreadType: 'Variable',
        cpaCommission: 150,
        revenueShare: 30,
        rating: 4.4,
        trustScore: 88,
        affiliateUrl: 'https://bybit.com/?ref=indicatorhub',
        isRecommended: false
      },
      {
        name: 'eToro',
        logo: 'https://placehold.co/150x80/4FBC0D/FFF?text=eToro',
        description: 'Leading global social investment network. Copy top real-money traders, explore zero-commission stocks, or trade crypto index buckets.',
        regulatedBy: ['FCA', 'ASIC', 'CySEC'],
        licenseNumbers: ['583261'],
        assetsCovered: ['Stocks', 'Crypto', 'Forex', 'ETFs'],
        minDeposit: 50,
        platforms: ['Social Webtrader'],
        spreadType: 'Fixed',
        cpaCommission: 200,
        rating: 4.2,
        trustScore: 90,
        affiliateUrl: 'https://etoro.com/?aff=indicatorhub',
        isRecommended: false
      },
      {
        name: 'Pepperstone',
        logo: 'https://placehold.co/150x80/0F2B5C/FFF?text=Pepperstone',
        description: 'Award-winning Australian raw broker. Direct API connects, TradingView charts integration, and excellent fast execution ticks.',
        regulatedBy: ['FCA', 'ASIC', 'CySEC'],
        licenseNumbers: ['414530'],
        assetsCovered: ['Forex', 'Crypto', 'Stocks', 'Indices', 'Commodities'],
        minDeposit: 200,
        platforms: ['MT4', 'MT5', 'cTrader', 'TradingView'],
        spreadType: 'Raw',
        cpaCommission: 200,
        rating: 4.5,
        trustScore: 94,
        affiliateUrl: 'https://pepperstone.com/?aff=indicatorhub',
        isRecommended: true
      }
    ]);
    console.log(`✓ [Seed Engine] Seeded ${seededBrokers.length} broker affiliates.`);

    // 7.5. Seeding Market News Articles
    console.log('🔄 [Seed Engine] Seeding global market news and alerts...');
    const seededNews = await MarketNews.create([
      {
        title: 'Federal Reserve Signals Interest Rate Pause Amid Cooling CPI Metrics',
        summary: 'Macroeconomists analyze FOMC statements indicating a defensive buffer on core yields. Traders align trend models to counter potential expansion sweeps.',
        content: '## Federal Reserve June FOMC Update\nIn its latest assembly, the Federal Open Market Committee maintained benchmark interest rates at current scopes, prompting sudden volatility spikes in NASDAQ composites and major Dollar-correlated currency indexes.\n\n### Strategic Takeaways for Traders\n- **Forex Liquidity**: Key trend models suggest sudden USD liquidations towards outer ATR bounds.\n- **Trend Alignment**: Swing-traders are recommended to switch default moving-average setups to prioritize smoother volume-weighted indexes.',
        source: 'IndicatorHub Newsroom',
        assetClassTags: ['Stocks', 'Forex', 'Global Economy'],
        symbolsAffected: ['EURUSD', 'GBPUSD', 'AAPL', 'MSFT'],
        sentiment: 'Bullish',
        importance: 'High',
        isFlashAlert: false
      },
      {
        title: 'Bitcoin Resistance Tested at $68K Level as Whales Initiate Accumulation Scale',
        summary: 'Order-book indicators identify massive buy-interest zones forming beneath standard support. Real-time indicators hint at a sudden breakout.',
        content: '## On-Chain Accumulation Metrics Sweep\nBitcoin indicators are currently flashing strong oversold conditions on daily candles as wallets holding 1,000+ BTC ramp up overall block transactions.\n\n### Crucial Screener Settings\n- **RSI Status**: Currently holding near standard 32 support.\n- **OBV (On-Balance-Volume)**: Divergent bullish markers suggest buyers are quietly absorbing sales layers.',
        source: 'On-Chain Quant Analytics',
        assetClassTags: ['Crypto'],
        symbolsAffected: ['BTCUSDT', 'ETHUSDT'],
        sentiment: 'Bullish',
        importance: 'High',
        isFlashAlert: true
      },
      {
        title: 'SEC Overhauls Ethereum Spot ETF Staking Definitions',
        summary: 'Regulatory modifications alter standard future contract margins. Experts suggest shift towards delta-neutral trading strategies.',
        content: '## New Staking Parameters Regulatory Review\nThe SEC has introduced streamlined guidelines concerning Ethereum custody products, with direct impacts on futures option models and copy-trading parameters.\n\n### Option Structuring Notes\n- **Volatility Indexes**: Standard deviation bands are tightening as short-term options pricing settles.',
        source: 'Regulatory Compliance Wire',
        assetClassTags: ['Crypto', 'Global Economy'],
        symbolsAffected: ['ETHUSDT'],
        sentiment: 'Neutral',
        importance: 'Medium',
        isFlashAlert: false
      }
    ]);
    console.log(`✓ [Seed Engine] Seeded ${seededNews.length} Global Market News stories.`);

    // 8. Insert Blog Posts (4 published guides)
    console.log('🔄 [Seed Engine] Seeding publishing blog guides...');
    const seededBlogPosts = await BlogPost.create([
      {
        title: 'Best RSI Indicators for Crypto Trading in 2026',
        excerpt: 'Traditional RSI indicators are heavily lagging and give countless false signals during cycles. In this guide, we break down top custom alternatives that actually work.',
        content: '## Understanding Volume Weighted RSI\nTraditional RSI only calculates closed price metrics, completely ignoring volume flows. During massive crypto liquidity pumps, standard RSI can sit oversold or overbought for days. By weighting RSI relative to volume flows, we filter out noise...\n### Top 3 RSI Alternatives\n1. RSI Divergence Pro\n2. Multi-Timeframe RSI Ribbons\n3. Stochastic Momentum RSI\nRead more details in our other review sections...',
        author: 'Chief Market Editor',
        category: 'Indicators',
        tags: ['RSI', 'Crypto', 'Indicators', 'Oscillators'],
        status: 'published',
        readTime: 6,
        isFeatured: true,
        coverImage: 'https://placehold.co/800x400/171B26/3B82F6?text=RSI+Crypto+Guide'
      },
      {
        title: 'MT4 vs MT5: Which Platform for Your EA?',
        excerpt: 'MetaTrader remains the absolute gold standard for executing Expert Advisors. But should you use MT4 or build automation scripts directly on MT5? We compare execution speeds and coding limitations.',
        content: '# MetaTrader Platforms Compared\nFor nearly two decades, MetaTrader 4 has dominated retail forex automation. However, MetaTrader 5 offers powerful modern enhancements...\n## Major Performance Differences\n- **Threading**: MT4 operates single-threaded, whereas MT5 supports multi-threaded strategy testing.\n- **Programming**: MT4 utilizes MQL4, while MT5 is built on MQL5, resembling professional C++ object environments...',
        author: 'Quant Specialist',
        category: 'Expert Advisors',
        tags: ['MT4', 'MT5', 'EA', 'MQL', 'Automated-Trading'],
        status: 'published',
        readTime: 8,
        coverImage: 'https://placehold.co/800x400/004B87/FFF?text=MT4+vs+MT5'
      },
      {
        title: 'Top 5 Free TradingView Indicators That Actually Work',
        excerpt: 'Save thousands on premium subscription indicators. We scoured the community scripts library of TradingView to find the absolute best free, open source tools for systematic trading.',
        content: '# Open Source Alpha on TradingView\nYou don\'t need expensive monthly indicators. The TradingView pine scripts depository holds absolute gold. Here are top open source markers:\n### 1. Bollinger Band Squeeze\nProvides excellent consolidation breakout maps.\n### 2. Fair Value Gap Finder\nAuto marks the exact FVG imbalances to find liquidity entries...',
        author: 'PineScript Wizard',
        category: 'Indicators',
        tags: ['TradingView', 'Free', 'Pine Script', 'IndicatorHub-Tips'],
        status: 'published',
        readTime: 5,
        isFeatured: true,
        coverImage: 'https://placehold.co/800x400/171B26/10B981?text=Free+TV+Indicators'
      },
      {
        title: 'How to Spot Fake Backtest Results: Red Flags Guide',
        excerpt: 'Curve fitting has depleted more trading accounts than bad luck. In this quantitative guide, we teach you how to analyze backtests, check drawdowns, and identify martingale indicators.',
        content: '# The Dark Art of Curve Fitting\nToo many developers configure their indicator inputs exactly to match historic price moves, yielding an unsustainable 99% win rate on charts that splits on live forwards tests...\n## Red Flags of Curve-Fitted Backtests\n- **Unrealistic Profit Factor**: Any profit factor above 3.5 in forex is highly suspicious.\n- **Undisclosed Drawdowns**: Martingales hide drawdowns by leaving contracts open indefinitely...',
        author: 'Lead Auditor',
        category: 'Strategies',
        tags: ['Backtest', 'Scam', 'Trust', 'Verification', 'Educational'],
        status: 'published',
        readTime: 10,
        coverImage: 'https://placehold.co/800x400/1E1E24/FFF?text=Backtest+Scam+Alerts'
      }
    ]);
    console.log(`✓ [Seed Engine] Seeded ${seededBlogPosts.length} published SEO guides.`);

    console.log('🎉 [Seed Engine] Database successfully pre-populated! Exiting...');
    mongoose.disconnect();
    process.exit(0);
  } catch (err) {
    console.error('✗ [Seed Engine] Fatal seeding error encountered:', err);
    mongoose.disconnect();
    process.exit(1);
  }
};

runSeed();
