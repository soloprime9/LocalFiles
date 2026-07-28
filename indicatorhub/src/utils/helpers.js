import { formatDistanceToNow } from 'date-fns';

export const formatPrice = (price, pricingModel) => {
  if (!price || pricingModel === 'free') return 'Free';
  if (pricingModel === 'subscription') return `$${price}/mo`;
  if (pricingModel === 'one-time') return `$${price}`;
  if (pricingModel === 'freemium') return `Free / $${price}`;
  return `$${price}`;
};

export const formatNumber = (n) => {
  if (!n && n !== 0) return '0';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
};

export const timeAgo = (date) => {
  if (!date) return '';
  try {
    return formatDistanceToNow(new Date(date), { addSuffix: true });
  } catch {
    return '';
  }
};

export const getPlatformColor = (platformName) => {
  const map = {
    TradingView: 'text-blue-400 bg-blue-900/30 border-blue-800/40',
    MetaTrader4: 'text-purple-400 bg-purple-900/30 border-purple-800/40',
    MetaTrader5: 'text-violet-400 bg-violet-900/30 border-violet-800/40',
    'MT4': 'text-purple-400 bg-purple-900/30 border-purple-800/40',
    'MT5': 'text-violet-400 bg-violet-900/30 border-violet-800/40',
    cTrader: 'text-teal-400 bg-teal-900/30 border-teal-800/40',
    NinjaTrader: 'text-orange-400 bg-orange-900/30 border-orange-800/40',
    ThinkOrSwim: 'text-cyan-400 bg-cyan-900/30 border-cyan-800/40',
    Binance: 'text-yellow-400 bg-yellow-900/30 border-yellow-800/40',
  };
  return map[platformName] || 'text-gray-400 bg-gray-900/30 border-gray-800/40';
};

export const getListingTypeIcon = (type) => {
  const map = {
    indicator: '📊',
    ea: '🤖',
    bot: '⚙️',
    signal: '📡',
    strategy: '🎯',
    script: '📝',
    tool: '🔧',
  };
  return map[type?.toLowerCase()] || '📦';
};

export const getAssetEmoji = (asset) => {
  const map = {
    forex: '💱',
    crypto: '₿',
    stocks: '📈',
    indices: '🏦',
    commodities: '🛢️',
    futures: '📋',
    options: '🎯',
    bonds: '📄',
  };
  return map[asset?.toLowerCase()] || '💹';
};

export const getRatingColor = (rating) => {
  if (rating >= 4.5) return 'text-green-400';
  if (rating >= 3.5) return 'text-amber-400';
  if (rating >= 2.5) return 'text-orange-400';
  return 'text-red-400';
};

export const getTrustScoreColor = (score) => {
  if (score >= 80) return 'text-green-400';
  if (score >= 60) return 'text-amber-400';
  if (score >= 40) return 'text-orange-400';
  return 'text-red-400';
};

export const truncate = (str, n) => {
  if (!str) return '';
  return str.length > n ? str.slice(0, n) + '...' : str;
};

export const slugify = (str) => {
  if (!str) return '';
  return str
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_-]+/g, '-')
    .replace(/^-+|-+$/g, '');
};
