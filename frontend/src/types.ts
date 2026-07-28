export interface Category {
  _id: string;
  name: string;
  slug: string;
  icon: string;
  description: string;
  color: string;
  sortOrder: number;
  itemCount: number;
}

export interface Platform {
  _id: string;
  name: string;
  slug: string;
  logo: string;
  description: string;
  userCount: string;
  indicatorLanguage: string;
  affiliateUrl: string;
  commissionType: string;
  commissionValue: string;
  priority: number;
}

export interface BacktestData {
  winRate: number;
  sharpeRatio?: number;
  sortinoRatio?: number;
  maxDrawdown: number;
  profitFactor?: number;
  totalTrades?: number;
  avgTradesPerMonth?: number;
  backtestPeriod?: string;
  backtestCapital?: number;
  auditStatus: 'Verified' | 'Suspicious' | 'Unaudited';
  auditNotes?: string;
  forwardTestActive?: boolean;
}

export interface Compatibility {
  tradingViewVersion?: string;
  mtVersion?: string;
  minCapital?: number;
  requiresBroker?: boolean;
  brokerRecommended?: string;
}

export interface FAQ {
  question: string;
  answer: string;
}

export interface Indicator {
  _id: string;
  name: string;
  slug: string;
  listingType: 'Indicator' | 'EA' | 'Bot' | 'Signal' | 'Strategy' | 'Screener' | 'Script' | 'Alert' | 'CopyTrading' | 'Template' | 'Course';
  category?: Category | string;
  platform?: Platform | string;
  description: string;
  longDescription?: string;
  assetClass: string[];
  strategyType: string[];
  timeframes: string[];
  difficulty: 'Beginner' | 'Intermediate' | 'Advanced' | 'Expert';
  price: number;
  pricingModel: 'Free' | 'One-time' | 'Monthly' | 'Yearly' | 'Freemium' | 'Rental';
  isFree: boolean;
  isPremiumListing: boolean;
  isFeatured: boolean;
  isVerified: boolean;
  isScamFlagged: boolean;
  scamReason?: string;
  trendingScore: number;
  weeklyViews: number;
  totalViews: number;
  weeklyLikes: number;
  totalLikes: number;
  tags: string[];
  author: string;
  authorUrl?: string;
  externalUrl?: string;
  affiliateUrl?: string;
  imageUrl?: string;
  screenshots?: string[];
  videoUrl?: string;
  demoUrl?: string;
  rating: number;
  totalReviews: number;
  trustScore: number;
  backtestData?: BacktestData;
  compatibility?: Compatibility;
  pros?: string[];
  cons?: string[];
  faqs?: FAQ[];
  relatedIds?: string[];
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface Review {
  _id: string;
  indicatorId: string;
  reviewerName: string;
  reviewerType: 'Beginner' | 'Intermediate' | 'Pro' | 'Institutional';
  rating: number;
  title: string;
  body: string;
  tradingPeriod?: string;
  assetTraded?: string;
  timeframeUsed?: string;
  profitableForReviewer: boolean;
  wouldRecommend: boolean;
  helpful: number;
  notHelpful: number;
  verified: boolean;
  isScam: boolean;
  createdAt: string;
}

export interface Signal {
  _id: string;
  name: string;
  provider: string;
  indicatorRef?: string;
  asset: string;
  direction: 'Buy' | 'Sell' | 'Neutral';
  entry: number;
  stopLoss: number;
  takeProfit1: number;
  takeProfit2?: number;
  takeProfit3?: number;
  timeframe: string;
  signalType: string;
  deliveryMethod: string;
  isActive: boolean;
  winRateHistoric?: number;
  totalSignalsIssued?: number;
  successfulSignals?: number;
  createdAt: string;
}

export interface Broker {
  _id: string;
  name: string;
  slug: string;
  logo: string;
  description: string;
  regulatedBy: string[];
  licenseNumbers?: string[];
  assetsCovered: string[];
  minDeposit: number;
  platforms: string[];
  spreadType: 'Fixed' | 'Variable' | 'Raw';
  cpaCommission?: number;
  revenueShare?: number;
  affiliateUrl: string;
  signupUrl: string;
  rating: number;
  trustScore: number;
  countryRestrictions?: string[];
  isRecommended: boolean;
  isFeatured: boolean;
}

export interface MarketNews {
  _id: string;
  title: string;
  slug: string;
  summary: string;
  content: string;
  source: string;
  sourceUrl?: string;
  assetClassTags: string[];
  symbolsAffected?: string[];
  sentiment: 'Bullish' | 'Neutral' | 'Bearish';
  importance: 'Low' | 'Medium' | 'High';
  author: string;
  coverImage: string;
  views: number;
  isFlashAlert: boolean;
  publishedAt: string;
}

export interface ConfigPreset {
  _id: string;
  indicatorId: string;
  title: string;
  description?: string;
  assetClass: string;
  symbol: string;
  timeframe: string;
  parameters: Record<string, string>;
  backtestResults?: {
    winRate?: number;
    profitFactor?: number;
    maxDrawdown?: number;
    totalTrades?: number;
    period?: string;
  };
  author: string;
  votes: {
    upvotes: number;
    downvotes: number;
  };
  isVerifiedByStaff: boolean;
  createdAt: string;
}

export interface BacktestReport {
  _id: string;
  indicatorId: string;
  testerName: string;
  testerType: string;
  timeframe: string;
  marketSymbol: string;
  testPeriod: string;
  metrics: {
    netProfitPercent: number;
    maxDrawdownPercent: number;
    profitFactor: number;
    winRatePercent: number;
    totalTrades: number;
    sharpeRatio?: number;
    recoveryFactor?: number;
  };
  dataSource: string;
  verifiedWithLogs: boolean;
  tradeHistoryFileUrl?: string;
  userReviewNotes?: string;
  discrepancyFlag: boolean;
  discrepancyReason?: string;
  upvotes: number;
  createdAt: string;
}

export interface MacroEvent {
  _id: string;
  title: string;
  country: string;
  impact: 'Low' | 'Medium' | 'High';
  previousValue?: string;
  forecastValue?: string;
  actualValue?: string;
  currencyAffected: string;
  affectedMarkets: string[];
  eventTime: string;
  recommendedAction: string;
  reportedSentiment: string;
}

export interface PriceData {
  symbol: string;
  price: number;
  changePercent: number;
  high: number;
  low: number;
  volume: any;
  market: 'Crypto' | 'Forex' | 'Commodities' | 'Stocks';
  lastUpdated: string;
}

export interface ScreenerData {
  symbol: string;
  market: string;
  indicators: {
    rsi: { value: number; signal: 'Overbought' | 'Oversold' | 'Neutral' };
    macd: { histogram: number; signal: string };
    bollinger: { signal: string };
    ema200Status: string;
  };
  scoring: {
    bullishPercent: number;
    recommendation: 'Strong Buy' | 'Buy' | 'Neutral' | 'Sell' | 'Strong Sell';
  };
  updatedAt: string;
}
