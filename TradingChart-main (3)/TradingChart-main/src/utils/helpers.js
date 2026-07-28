import { format } from 'date-fns';

/**
 * 1. Convert Date into 'X time ago' format
 */
export function timeAgo(dateInput) {
  if (!dateInput) return '';
  const date = new Date(dateInput);
  if (isNaN(date.getTime())) return '';
  
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return 'just now';
  
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  
  const years = Math.floor(months / 12);
  return `${years}y ago`;
}

/**
 * 2. Format Price based on pricing model
 */
export function formatPrice(price, pricingModel) {
  if (price === 0 || pricingModel === 'Free' || !price) return 'FREE';
  
  const suffix =
    pricingModel === 'Monthly'
      ? '/mo'
      : pricingModel === 'Yearly'
      ? '/yr'
      : pricingModel === 'Rental'
      ? '/rental'
      : '';
      
  return `$${price}${suffix}`;
}

/**
 * 3. Compact long numbers into K, M, B format
 */
export function formatNumber(num) {
  if (num === undefined || num === null || isNaN(num)) return '0';
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1).replace(/\.0$/, '') + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1).replace(/\.0$/, '') + 'K';
  }
  return num.toString();
}

/**
 * 4. Get Tailwind color tokens based on Trading Platform
 */
export function getPlatformColor(platformName = '') {
  const platform = platformName.toLowerCase().trim();
  if (platform.includes('tradingview')) return 'bg-blue-600 text-white';
  if (platform.includes('metatrader 4') || platform.includes('mt4')) return 'bg-sky-500 text-white';
  if (platform.includes('metatrader 5') || platform.includes('mt5')) return 'bg-indigo-600 text-white';
  if (platform.includes('ctrader')) return 'bg-teal-500 text-white';
  if (platform.includes('ninjatrader')) return 'bg-orange-600 text-white';
  if (platform.includes('3commas')) return 'bg-emerald-600 text-white';
  if (platform.includes('pionex')) return 'bg-amber-600 text-white';
  if (platform.includes('cryptohopper')) return 'bg-cyan-600 text-white';
  return 'bg-[#1A1A1A] text-gray-300 border border-[#374151]';
}

/**
 * 5. Map listing types to icons for badge structures
 */
export function getListingTypeIcon(type = '') {
  const cleanType = type.toLowerCase().trim();
  switch (cleanType) {
    case 'indicator': return '📊';
    case 'ea': return '🤖';
    case 'bot': return '⚙️';
    case 'signal': return '📡';
    case 'strategy': return '🧠';
    case 'screener': return '🔍';
    case 'script':
    case 'alert': return '🔔';
    case 'copytrading': return '👥';
    case 'template': return '📋';
    case 'course': return '🎓';
    default: return '💼';
  }
}

/**
 * 6. Get Emojis for Asset Classes to match backend Enums
 */
export function getAssetEmoji(asset = '') {
  const cleanAsset = asset.toLowerCase().trim();
  if (cleanAsset.includes('crypto') || cleanAsset.includes('bitcoin')) return '🪙';
  if (cleanAsset.includes('forex') || cleanAsset.includes('fx')) return '💱';
  if (cleanAsset.includes('stock') || cleanAsset.includes('share')) return '📈';
  if (cleanAsset.includes('index') || cleanAsset.includes('indices')) return '📊';
  if (cleanAsset.includes('gold') || cleanAsset.includes('xau')) return '🥇';
  if (cleanAsset.includes('silver')) return '🥈';
  if (cleanAsset.includes('oil') || cleanAsset.includes('crude')) return '🛢️';
  if (cleanAsset.includes('commodit')) return '🌾';
  if (cleanAsset.includes('future')) return '⏳';
  if (cleanAsset.includes('option')) return '🔮';
  if (cleanAsset.includes('etf')) return '🗂️';
  return '💼';
}

/**
 * 7. Colors for Trust Scores dynamically matching Tailwind spec
 */
export function getTrustScoreColor(score) {
  const numScore = Number(score);
  if (numScore <= 30) return { text: 'text-red-400', bg: 'bg-red-500', ring: 'ring-red-500/30', label: 'Suspicious' };
  if (numScore <= 60) return { text: 'text-amber-400', bg: 'bg-amber-500', ring: 'ring-amber-500/30', label: 'Low Trust' };
  if (numScore <= 80) return { text: 'text-blue-400', bg: 'bg-blue-500', ring: 'ring-blue-500/30', label: 'Good' };
  return { text: 'text-emerald-400', bg: 'bg-emerald-500', ring: 'ring-emerald-500/30', label: 'Excellent' };
}

/**
 * 8. Truncate long descriptions smoothly
 */
export function truncate(str = '', max = 120) {
  if (str.length <= max) return str;
  return `${str.slice(0, max).trim()}…`;
}

/**
 * 9. Get dynamic colors based on Star Ratings
 */
export function getRatingColor(rating) {
  const r = Number(rating);
  if (r >= 4.5) return 'text-emerald-400';
  if (r >= 3.5) return 'text-amber-400';
  return 'text-red-400';
}

/**
 * 10. Helper to construct clean strings into slugs
 */
export function slugify(str = '') {
  return str
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_-]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

/**
 * 11. Initial Name Parser for Avatar circles
 */
export function initials(name = '') {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('');
}

/**
 * 12. Pure mathematical clamp for strict UI parameters
 */
export function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}





// export function timeAgo(dateInput) {
//   if (!dateInput) return '';
//   const date = new Date(dateInput);
//   const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
//   if (seconds < 60) return 'just now';
//   const minutes = Math.floor(seconds / 60);
//   if (minutes < 60) return `${minutes}m ago`;
//   const hours = Math.floor(minutes / 60);
//   if (hours < 24) return `${hours}h ago`;
//   const days = Math.floor(hours / 24);
//   if (days < 30) return `${days}d ago`;
//   const months = Math.floor(days / 30);
//   if (months < 12) return `${months}mo ago`;
//   const years = Math.floor(months / 12);
//   return `${years}y ago`;
// }

// export function formatPrice(price, pricingModel) {
//   if (price === 0 || pricingModel === 'Free') return 'FREE';
//   const suffix =
//     pricingModel === 'Monthly'
//       ? '/mo'
//       : pricingModel === 'Yearly'
//       ? '/yr'
//       : pricingModel === 'Rental'
//       ? '/rental'
//       : '';
//   return `$${price}${suffix}`;
// }

// export function initials(name = '') {
//   return name
//     .trim()
//     .split(/\s+/)
//     .slice(0, 2)
//     .map((p) => p[0]?.toUpperCase())
//     .join('');
// }

// const AVATAR_COLORS = [
//   'bg-rose-500',
//   'bg-amber-500',
//   'bg-emerald-500',
//   'bg-blue-500',
//   'bg-violet-500',
//   'bg-pink-500',
//   'bg-cyan-500',
// ];

// export function colorFromString(str = '') {
//   let hash = 0;
//   for (let i = 0; i < str.length; i++) {
//     hash = (hash << 5) - hash + str.charCodeAt(i);
//     hash |= 0;
//   }
//   const idx = Math.abs(hash) % AVATAR_COLORS.length;
//   return AVATAR_COLORS[idx];
// }

// export function clamp(value, min, max) {
//   return Math.min(Math.max(value, min), max);
// }

// export function trustScoreColor(score) {
//   if (score <= 30) return { text: 'text-red-400', bg: 'bg-red-500', ring: 'ring-red-500/30' };
//   if (score <= 60) return { text: 'text-amber-400', bg: 'bg-amber-500', ring: 'ring-amber-500/30' };
//   if (score <= 80) return { text: 'text-blue-400', bg: 'bg-blue-500', ring: 'ring-blue-500/30' };
//   return { text: 'text-emerald-400', bg: 'bg-emerald-500', ring: 'ring-emerald-500/30' };
// }

// export function truncate(str = '', max = 120) {
//   if (str.length <= max) return str;
//   return `${str.slice(0, max).trim()}…`;
// }
