'use client'
import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  FireIcon,
  ShieldCheckIcon,
  ChartBarIcon,
  MagnifyingGlassIcon,
  ArrowRightIcon,
  StarIcon,
  CheckBadgeIcon,
  ExclamationTriangleIcon,
  GlobeAltIcon,
  DocumentChartBarIcon,
  ArrowTrendingUpIcon,
  SparklesIcon,
  ClockIcon,
  BookOpenIcon,
} from '@heroicons/react/24/outline';
import { useAppContext } from '../context/AppContext';

import IndicatorCard from '../components/indicators/IndicatorCard';
import SkeletonCard from '../components/ui/SkeletonCard';
import StatCard from '../components/ui/StatCard';
import SectionHeader from '../components/ui/SectionHeader';
import {
  getNewest,
  getFeatured,
  getTrending,
  getFeaturedBrokers,
  getBlogPosts,
  getCategories,
  getStats,
} from '../utils/api';
import { formatNumber } from '../utils/helpers';

// ── Platform strip data ────────────────────────────────────────
const PLATFORMS = [
  { name: 'TradingView', color: '#2962FF', abbr: 'TV' },
  { name: 'MetaTrader 4', color: '#8B5CF6', abbr: 'MT4' },
  { name: 'MetaTrader 5', color: '#7C3AED', abbr: 'MT5' },
  { name: 'cTrader', color: '#0EA5E9', abbr: 'cT' },
  { name: 'NinjaTrader', color: '#F97316', abbr: 'NT' },
  { name: 'ThinkOrSwim', color: '#06B6D4', abbr: 'ToS' },
  { name: 'Binance', color: '#F59E0B', abbr: 'BNB' },
  { name: 'Interactive Brokers', color: '#EF4444', abbr: 'IB' },
];

// ── Listing types ──────────────────────────────────────────────
const LISTING_TYPES = [
  { label: 'Indicators', type: 'indicator', color: 'border-blue-700/50 hover:border-blue-500 text-blue-400' },
  { label: 'Expert Advisors', type: 'ea', color: 'border-purple-700/50 hover:border-purple-500 text-purple-400' },
  { label: 'Bots', type: 'bot', color: 'border-cyan-700/50 hover:border-cyan-500 text-cyan-400' },
  { label: 'Signals', type: 'signal', color: 'border-pink-700/50 hover:border-pink-500 text-pink-400' },
  { label: 'Strategies', type: 'strategy', color: 'border-orange-700/50 hover:border-orange-500 text-orange-400' },
  { label: 'Screeners', type: 'screener', color: 'border-teal-700/50 hover:border-teal-500 text-teal-400' },
  { label: 'Scripts', type: 'script', color: 'border-lime-700/50 hover:border-lime-500 text-lime-400' },
  { label: 'Copy Trading', type: 'copy-trading', color: 'border-violet-700/50 hover:border-violet-500 text-violet-400' },
  { label: 'Courses', type: 'course', color: 'border-yellow-700/50 hover:border-yellow-500 text-yellow-400' },
];

// ── Asset classes ──────────────────────────────────────────────
const ASSETS = [
  { label: 'Crypto', emoji: '🪙', asset: 'crypto', color: 'from-amber-900/20 to-amber-900/5 border-amber-800/40 hover:border-amber-600/60' },
  { label: 'Forex', emoji: '💱', asset: 'forex', color: 'from-blue-900/20 to-blue-900/5 border-blue-800/40 hover:border-blue-600/60' },
  { label: 'Stocks', emoji: '📈', asset: 'stocks', color: 'from-green-900/20 to-green-900/5 border-green-800/40 hover:border-green-600/60' },
  { label: 'Indices', emoji: '📊', asset: 'indices', color: 'from-purple-900/20 to-purple-900/5 border-purple-800/40 hover:border-purple-600/60' },
  { label: 'Gold', emoji: '🥇', asset: 'gold', color: 'from-yellow-900/20 to-yellow-900/5 border-yellow-800/40 hover:border-yellow-600/60' },
  { label: 'Oil', emoji: '🛢️', asset: 'oil', color: 'from-stone-900/20 to-stone-900/5 border-stone-700/40 hover:border-stone-500/60' },
];

// ── Trust features ─────────────────────────────────────────────
const TRUST_FEATURES = [
  {
    icon: CheckBadgeIcon,
    title: 'Verified Reviews',
    desc: 'Every review is authenticated against real purchase records. No fake testimonials, ever.',
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-800/30',
  },
  {
    icon: DocumentChartBarIcon,
    title: 'Backtest Audits',
    desc: 'We audit submitted backtests for curve-fitting, look-ahead bias, and data manipulation.',
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
    border: 'border-blue-800/30',
  },
  {
    icon: ExclamationTriangleIcon,
    title: 'Scam Detection',
    desc: 'AI-powered red flag analysis flags misleading claims, fake win-rates, and known scam patterns.',
    color: 'text-red-400',
    bg: 'bg-red-500/10',
    border: 'border-red-800/30',
  },
  {
    icon: GlobeAltIcon,
    title: 'Cross-Platform Discovery',
    desc: 'Search across TradingView, MT4/5, cTrader, NinjaTrader and more — all in one place.',
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    border: 'border-amber-800/30',
  },
];

// ── Animated grid hero background ─────────────────────────────
function AnimatedGrid() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      <svg
        className="absolute inset-0 w-full h-full opacity-[0.07]"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#F59E0B" strokeWidth="0.5" />
          </pattern>
          <radialGradient id="fade" cx="50%" cy="50%" r="60%">
            <stop offset="0%" stopColor="#0A0A0A" stopOpacity="0" />
            <stop offset="100%" stopColor="#0A0A0A" stopOpacity="1" />
          </radialGradient>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
        <rect width="100%" height="100%" fill="url(#fade)" />
      </svg>
      {/* Amber glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-amber-500/5 rounded-full blur-3xl" />
      {/* Subtle blue accent */}
      <div className="absolute bottom-0 right-1/4 w-[400px] h-[200px] bg-blue-500/5 rounded-full blur-3xl" />
    </div>
  );
}

// ── Hero Search Bar ────────────────────────────────────────────
function HeroSearchBar() {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();
  const { setFilter } = useAppContext();

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setFilter('search', query.trim());
    navigate(`/indicators?search=${encodeURIComponent(query.trim())}`);
  };

  return (
    <form onSubmit={handleSubmit} className="relative w-full max-w-2xl mx-auto">
      <div className="relative flex items-center group">
        <MagnifyingGlassIcon className="absolute left-5 w-5 h-5 text-gray-400 pointer-events-none z-10 group-focus-within:text-amber-400 transition-colors" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search indicators, EAs, bots, strategies..."
          className="w-full h-14 pl-14 pr-36 bg-[#111111] border border-[#2A2A2A] focus:border-amber-500/70 focus:ring-2 focus:ring-amber-500/20 outline-none rounded-xl text-white text-base placeholder-gray-500 transition-all duration-200 shadow-2xl"
        />
        <button
          type="submit"
          className="absolute right-2 h-10 px-5 bg-amber-500 hover:bg-amber-600 text-black font-semibold rounded-lg text-sm transition-colors duration-200 flex items-center gap-2"
        >
          <MagnifyingGlassIcon className="w-4 h-4" />
          Search
        </button>
      </div>
      <div className="flex items-center gap-3 mt-3 justify-center flex-wrap">
        {['RSI Divergence', 'Scalping EA', 'MACD Bot', 'Supply & Demand'].map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => { setQuery(q); }}
            className="text-xs text-gray-500 hover:text-amber-400 bg-[#1A1A1A] hover:bg-amber-500/10 border border-[#2A2A2A] hover:border-amber-500/30 rounded-full px-3 py-1 transition-all duration-200"
          >
            {q}
          </button>
        ))}
      </div>
    </form>
  );
}

// ── Rank Badge ─────────────────────────────────────────────────
function RankBadge({ rank }) {
  const colors = {
    1: 'bg-amber-500 text-black border-amber-400',
    2: 'bg-gray-300 text-black border-gray-200',
    3: 'bg-amber-700 text-white border-amber-600',
  };
  return (
    <div className={`w-8 h-8 rounded-full border-2 flex items-center justify-center font-bold text-sm flex-shrink-0 ${colors[rank] || 'bg-[#1F2937] text-gray-400 border-[#374151]'}`}>
      {rank}
    </div>
  );
}

// ── Skeleton loaders ───────────────────────────────────────────
function StatSkeleton() {
  return (
    <div className="bg-[#111111] border border-[#1F2937] rounded-xl p-4 animate-pulse">
      <div className="flex items-start justify-between">
        <div>
          <div className="h-3 w-24 bg-[#1F2937] rounded mb-2" />
          <div className="h-7 w-16 bg-[#1F2937] rounded" />
        </div>
        <div className="w-9 h-9 rounded-lg bg-[#1F2937]" />
      </div>
    </div>
  );
}

function BlogCardSkeleton() {
  return (
    <div className="bg-[#111111] border border-[#1F2937] rounded-xl overflow-hidden animate-pulse">
      <div className="h-44 bg-[#1A1A1A]" />
      <div className="p-4 space-y-2">
        <div className="h-4 bg-[#1F2937] rounded w-4/5" />
        <div className="h-3 bg-[#1A1A1A] rounded w-full" />
        <div className="h-3 bg-[#1A1A1A] rounded w-3/4" />
        <div className="h-3 bg-[#1A1A1A] rounded w-1/3 mt-3" />
      </div>
    </div>
  );
}

// ── Broker Card ────────────────────────────────────────────────
function BrokerCard({ broker }) {
  return (
    <div className="bg-[#111111] border border-[#1F2937] hover:border-[#374151] rounded-xl p-5 flex flex-col gap-4 transition-all duration-200 group">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#1F2937] to-[#111111] border border-[#2A2A2A] flex items-center justify-center font-bold text-amber-400 text-sm flex-shrink-0 group-hover:border-amber-500/30 transition-colors">
          {broker.logoUrl ? (
            <img src={broker.logoUrl} alt={broker.name} className="w-8 h-8 object-contain rounded" onError={(e) => { e.target.style.display='none'; }} />
          ) : (
            (broker.name || 'BR').slice(0, 2).toUpperCase()
          )}
        </div>
        <div className="min-w-0">
          <p className="text-white font-semibold text-sm truncate">{broker.name || 'Premier Broker'}</p>
          <div className="flex items-center gap-1.5 mt-0.5">
            {(broker.isRegulated || broker.regulated) && (
              <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-800/40 rounded px-1.5 py-0.5">
                <ShieldCheckIcon className="w-2.5 h-2.5" />
                Regulated
              </span>
            )}
            {broker.regulatoryBody && (
              <span className="text-[10px] text-gray-500">{broker.regulatoryBody}</span>
            )}
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-[#0D0D0D] rounded-lg p-2.5 text-center">
          <p className="text-[10px] text-gray-500 mb-0.5">CPA / Lead</p>
          <p className="text-amber-400 font-bold text-sm">{broker.cpaValue ? `$${broker.cpaValue}` : broker.cpa || '$250'}</p>
        </div>
        <div className="bg-[#0D0D0D] rounded-lg p-2.5 text-center">
          <p className="text-[10px] text-gray-500 mb-0.5">Min Deposit</p>
          <p className="text-white font-bold text-sm">{broker.minDeposit ? `$${broker.minDeposit}` : '$10'}</p>
        </div>
      </div>

      {/* Platforms */}
      {broker.platforms?.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {broker.platforms.slice(0, 3).map((p) => (
            <span key={p} className="text-[10px] bg-blue-900/30 text-blue-400 border border-blue-800/40 rounded px-1.5 py-0.5">{p}</span>
          ))}
        </div>
      )}

      <a
        href={broker.affiliateUrl || broker.website || '#'}
        target="_blank"
        rel="noopener noreferrer sponsored"
        className="w-full btn-primary py-2.5 text-sm rounded-lg mt-auto"
      >
        Get Bonus →
      </a>
    </div>
  );
}

// ── Blog Post Card ─────────────────────────────────────────────
function BlogCard({ post }) {
  const date = post.publishedAt || post.createdAt;
  const formatted = date ? new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '';
  return (
    <Link to={`/blog/${post.slug}`} className="group bg-[#111111] border border-[#1F2937] hover:border-[#374151] rounded-xl overflow-hidden flex flex-col transition-all duration-200">
      <div className="h-44 bg-gradient-to-br from-[#1A1A1A] to-[#0D0D0D] relative overflow-hidden">
        {post.coverImage || post.cover ? (
          <img
            src={post.coverImage || post.cover}
            alt={post.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            onError={(e) => { e.target.style.display = 'none'; }}
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <BookOpenIcon className="w-10 h-10 text-[#2A2A2A]" />
          </div>
        )}
        {post.category && (
          <span className="absolute top-3 left-3 text-[10px] font-medium bg-amber-500 text-black px-2 py-0.5 rounded-full">
            {post.category}
          </span>
        )}
      </div>
      <div className="p-4 flex flex-col gap-2 flex-1">
        <h3 className="text-white font-semibold text-sm leading-snug group-hover:text-amber-400 transition-colors line-clamp-2">
          {post.title}
        </h3>
        {post.excerpt && (
          <p className="text-gray-500 text-xs leading-relaxed line-clamp-2">{post.excerpt}</p>
        )}
        <div className="flex items-center gap-3 mt-auto pt-2 text-[11px] text-gray-500">
          {post.readTime && (
            <span className="flex items-center gap-1">
              <ClockIcon className="w-3 h-3" />
              {post.readTime} min read
            </span>
          )}
          {formatted && <span>{formatted}</span>}
        </div>
      </div>
    </Link>
  );
}

// ── Category Card ──────────────────────────────────────────────
const CATEGORY_COLORS = [
  'border-blue-700/40 hover:border-blue-500/60',
  'border-purple-700/40 hover:border-purple-500/60',
  'border-teal-700/40 hover:border-teal-500/60',
  'border-amber-700/40 hover:border-amber-500/60',
  'border-pink-700/40 hover:border-pink-500/60',
  'border-green-700/40 hover:border-green-500/60',
  'border-orange-700/40 hover:border-orange-500/60',
  'border-cyan-700/40 hover:border-cyan-500/60',
];

const CATEGORY_ICON_COLORS = ['text-blue-400','text-purple-400','text-teal-400','text-amber-400','text-pink-400','text-green-400','text-orange-400','text-cyan-400'];

function CategoryCard({ category, index }) {
  const border = CATEGORY_COLORS[index % CATEGORY_COLORS.length];
  const iconColor = CATEGORY_ICON_COLORS[index % CATEGORY_ICON_COLORS.length];
  return (
    <Link
      to={`/categories/${category.slug}`}
      className={`group bg-[#111111] border ${border} rounded-xl p-4 flex items-center gap-3 transition-all duration-200 hover:bg-[#141414]`}
    >
      <span className={`text-2xl flex-shrink-0 ${iconColor}`}>
        {category.icon || category.emoji || '📁'}
      </span>
      <div className="min-w-0">
        <p className="text-white text-sm font-medium truncate group-hover:text-amber-400 transition-colors">
          {category.name}
        </p>
        <p className="text-gray-500 text-xs mt-0.5">
          {formatNumber(category.count || category.toolCount || 0)} tools
        </p>
      </div>
      <ArrowRightIcon className="w-3.5 h-3.5 text-gray-600 group-hover:text-amber-400 ml-auto flex-shrink-0 transition-colors" />
    </Link>
  );
}

// ── Fallback data for when API is unavailable ──────────────────
const FALLBACK_STATS = {
  totalIndicators: 4200,
  platformCount: 12,
  reviewCount: 28500,
  avgTrustScore: 78,
};

const FALLBACK_BROKERS = [
  { _id: '1', name: 'IC Markets', isRegulated: true, regulatoryBody: 'ASIC / CySEC', cpaValue: 600, minDeposit: 200, platforms: ['MT4', 'MT5', 'cTrader'], affiliateUrl: '#' },
  { _id: '2', name: 'Pepperstone', isRegulated: true, regulatoryBody: 'FCA / ASIC', cpaValue: 500, minDeposit: 0, platforms: ['MT4', 'MT5', 'TradingView'], affiliateUrl: '#' },
  { _id: '3', name: 'XM Global', isRegulated: true, regulatoryBody: 'CySEC / IFSC', cpaValue: 400, minDeposit: 5, platforms: ['MT4', 'MT5'], affiliateUrl: '#' },
];

const FALLBACK_BLOG = [
  { _id: '1', slug: 'best-rsi-indicators-2024', title: 'The 7 Best RSI Indicators for TradingView in 2024', excerpt: 'We tested dozens of RSI variants — here are the ones that actually improve your entries.', readTime: 8, category: 'Indicators', publishedAt: new Date().toISOString() },
  { _id: '2', slug: 'ea-vs-manual-trading', title: 'Expert Advisors vs Manual Trading: Which Wins Long-Term?', excerpt: 'A data-driven comparison across 3 years of live trading to settle the debate once and for all.', readTime: 12, category: 'EAs', publishedAt: new Date().toISOString() },
  { _id: '3', slug: 'backtest-audit-guide', title: 'How to Spot a Fake Backtest in Under 60 Seconds', excerpt: "Most published backtests are curve-fitted or cherry-picked. Here's how to tell.", readTime: 6, category: 'Education', publishedAt: new Date().toISOString() },
];

const FALLBACK_CATEGORIES = [
  { slug: 'momentum', name: 'Momentum', icon: '🚀', count: 340 },
  { slug: 'trend-following', name: 'Trend Following', icon: '📈', count: 520 },
  { slug: 'mean-reversion', name: 'Mean Reversion', icon: '🔄', count: 210 },
  { slug: 'volume', name: 'Volume Analysis', icon: '📊', count: 180 },
  { slug: 'oscillators', name: 'Oscillators', icon: '〰️', count: 290 },
  { slug: 'support-resistance', name: 'Support & Resistance', icon: '🔲', count: 445 },
  { slug: 'volatility', name: 'Volatility', icon: '⚡', count: 160 },
  { slug: 'price-action', name: 'Price Action', icon: '🕯️', count: 380 },
];

// ══════════════════════════════════════════════════════════════
// HOME PAGE
// ══════════════════════════════════════════════════════════════
export default function Home() {
  const [trending, setTrending] = useState([]);
  const [featured, setFeatured] = useState([]);
  const [newest, setNewest] = useState([]);
  const [brokers, setBrokers] = useState([]);
  const [blogPosts, setBlogPosts] = useState([]);
  const [localStats, setLocalStats] = useState(null);
  const [localCategories, setLocalCategories] = useState([]);

  // FIX 1: stats aur categories variables ko yahan se hata diya
  const [loading, setLoading] = useState({
    newest: true,
    brokers: true,
    blog: true,
    stats: true,
    categories: true,
  });

  // SEO: title + meta description + ItemList JSON-LD for rich results.
  // Note: this only fires after hydration. The crawlable-without-JS title,
  // description, and OG tags live server-side in app/layout.jsx metadata —
  // this just keeps things in sync for client-side navigation (SPA route
  // changes don't re-run the server layout).
  useEffect(() => {
    document.title = 'FalconSpido — Best Trading Indicators, EAs, Bots & Strategies 2026';

    let meta = document.querySelector('meta[name="description"]');
    if (!meta) {
      meta = document.createElement('meta');
      meta.setAttribute('name', 'description');
      document.head.appendChild(meta);
    }
    meta.setAttribute(
      'content',
      'Discover and compare trading indicators, EAs, bots, signals and strategies across TradingView, MT4, MT5, cTrader and more — ranked by verified TrustScore and backtest audits.'
    );

    let canonical = document.querySelector('link[rel="canonical"]');
    if (!canonical) {
      canonical = document.createElement('link');
      canonical.setAttribute('rel', 'canonical');
      document.head.appendChild(canonical);
    }
    canonical.setAttribute('href', 'https://falconspido.com/');

    const scriptId = 'home-itemlist-jsonld';
    let script = document.getElementById(scriptId);
    if (!script) {
      script = document.createElement('script');
      script.id = scriptId;
      script.type = 'application/ld+json';
      document.head.appendChild(script);
    }
    script.textContent = JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'ItemList',
      name: 'Trading Tool Categories on FalconSpido',
      itemListElement: LISTING_TYPES.map((t, i) => ({
        '@type': 'ListItem',
        position: i + 1,
        name: t.label,
        url: `https://falconspido.com/type/${t.type}`,
      })),
    });

    return () => {
      script?.remove();
    };
  }, []);

  useEffect(() => {
    // Newest
    getNewest()
      .then((r) => setNewest((r?.data || r || []).slice(0, 4)))
      .catch(() => {})
      .finally(() => setLoading((p) => ({ ...p, newest: false })));

    // Brokers
    getFeaturedBrokers()
      .then((r) => {
        const data = r?.data || r || [];
        setBrokers(data.length ? data.slice(0, 3) : FALLBACK_BROKERS);
      })
      .catch(() => setBrokers(FALLBACK_BROKERS))
      .finally(() => setLoading((p) => ({ ...p, brokers: false })));

    // Blog
    getBlogPosts({ limit: 3, sort: 'newest' })
      .then((r) => {
        const data = r?.data || r || [];
        setBlogPosts(data.length ? data : FALLBACK_BLOG);
      })
      .catch(() => setBlogPosts(FALLBACK_BLOG))
      .finally(() => setLoading((p) => ({ ...p, blog: false })));

    // FIX 2: if condition hata kar direct API call kiya
    getStats()
      .then((r) => {
        const data = r?.data || r;
        setLocalStats(data || FALLBACK_STATS);
      })
      .catch(() => setLocalStats(FALLBACK_STATS))
      .finally(() => setLoading((p) => ({ ...p, stats: false })));

    // FIX 3: if condition hata kar direct API call kiya
    getCategories()
      .then((r) => {
        const data = r?.data || r || [];
        setLocalCategories(data.length ? data : FALLBACK_CATEGORIES);
      })
      .catch(() => setLocalCategories(FALLBACK_CATEGORIES))
      .finally(() => setLoading((p) => ({ ...p, categories: false })));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const displayStats = localStats || FALLBACK_STATS;
  const displayCategories = localCategories.length ? localCategories : FALLBACK_CATEGORIES;

  return (
    <div className="min-h-screen bg-[#0A0A0A]">

      {/* ══ 1. HERO ══════════════════════════════════════════════════ */}
      <section className="relative min-h-[520px] flex flex-col items-center justify-center px-4 pt-16 pb-12 text-center overflow-hidden border-b border-[#1A1A1A]">
        <AnimatedGrid />

        <div className="relative z-10 w-full max-w-4xl mx-auto">
          {/* Pill badge */}
          <div className="inline-flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 rounded-full px-4 py-1.5 text-amber-400 text-xs font-semibold mb-6 backdrop-blur">
            <FireIcon className="w-3.5 h-3.5" />
            The #1 Trading Tools Directory — {formatNumber(displayStats?.totalIndicators || 4200)}+ Tools Listed
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-5xl lg:text-[3.5rem] font-extrabold text-white leading-[1.1] tracking-tight mb-5">
            Discover the World's Best{' '}
            <span className="text-amber-400">Trading Indicators</span>,{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-orange-400">EAs, Bots</span>{' '}
            &amp; Strategies
          </h1>

          {/* Sub-headline */}
          <p className="text-gray-400 text-base sm:text-lg max-w-2xl mx-auto mb-8 leading-relaxed">
            <span className="text-gray-300">Verified reviews</span>
            <span className="mx-2 text-[#374151]">·</span>
            <span className="text-gray-300">Cross-platform</span>
            <span className="mx-2 text-[#374151]">·</span>
            <span className="text-gray-300">Backtest audits</span>
            <span className="mx-2 text-[#374151]">·</span>
            <span className="text-gray-300">Scam detection</span>
          </p>

          {/* Search bar */}
          <HeroSearchBar />

          {/* Platform strip */}
          <div className="mt-10">
            <p className="text-gray-600 text-xs font-medium mb-4 uppercase tracking-widest">Works with</p>
            <div className="flex items-center justify-center flex-wrap gap-3">
              {PLATFORMS.map((p) => (
                <Link
                  key={p.name}
                  to={`/platforms/${p.name.toLowerCase().replace(/\s+/g, '-')}`}
                  className="flex items-center gap-2 px-3 py-1.5 bg-[#111111] border border-[#1F2937] hover:border-[#374151] rounded-lg transition-all duration-200 group"
                  title={p.name}
                >
                  <div
                    className="w-5 h-5 rounded flex items-center justify-center text-[9px] font-bold text-white flex-shrink-0"
                    style={{ backgroundColor: p.color + '33', border: `1px solid ${p.color}55`, color: p.color }}
                  >
                    {p.abbr.slice(0, 2)}
                  </div>
                  <span className="text-gray-400 text-xs group-hover:text-white transition-colors hidden sm:inline">{p.name}</span>
                  <span className="text-gray-400 text-xs group-hover:text-white transition-colors sm:hidden">{p.abbr}</span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ══ 2. STATS BAR ══════════════════════════════════════════════ */}
      <section className="border-b border-[#1A1A1A] bg-[#0D0D0D]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {loading.stats && !displayStats ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => <StatSkeleton key={i} />)}
            </div>
          ) : displayStats ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <StatCard
                icon={ChartBarIcon}
                label="Total Tools"
                value={formatNumber(displayStats.totalIndicators || displayStats.totalTools || 4200)}
              />
              <StatCard
                icon={GlobeAltIcon}
                label="Platforms Covered"
                value={formatNumber(displayStats.platformCount || displayStats.platforms || 12)}
              />
              <StatCard
                icon={StarIcon}
                label="Verified Reviews"
                value={formatNumber(displayStats.reviewCount || displayStats.reviews || 28500)}
              />
              <StatCard
                icon={ShieldCheckIcon}
                label="Avg Trust Score"
                value={`${displayStats.avgTrustScore || displayStats.trustScore || 78}%`}
              />
            </div>
          ) : null}
        </div>
      </section>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

        {/* ══ 3. FEATURED TOOLS ═══════════════════════════════════════ */}
        <section className="py-12 border-b border-[#1A1A1A]">
          <SectionHeader
            title="⭐ Featured Tools"
            subtitle="Editor picks — handpicked for quality, documentation, and real-world results"
            viewAllLink="/indicators?sort=featured"
            viewAllLabel="View All Featured"
          />
          {loading.featured ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
            </div>
          ) : featured?.length ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {featured.slice(0, 4).map((ind) => (
                <IndicatorCard key={ind._id} indicator={ind} />
              ))}
            </div>
          ) : (
            <div className="text-center py-10 text-gray-600 text-sm">Featured tools loading...</div>
          )}
        </section>

        {/* ══ 4. TRENDING THIS WEEK ════════════════════════════════════ */}
        <section className="py-12 border-b border-[#1A1A1A]">
          <SectionHeader
            title="🔥 Trending This Week"
            subtitle="Most viewed and wishlisted by the community in the last 7 days"
            viewAllLink="/trending"
            viewAllLabel="View All Trending"
          />
          {loading.trending ? (
            <div className="space-y-3">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-20 bg-[#111111] border border-[#1F2937] rounded-xl animate-pulse" />
              ))}
            </div>
          ) : trending?.length ? (
            <div className="space-y-3">
              {trending.slice(0, 6).map((ind, i) => (
                <Link
                  key={ind._id}
                  to={`/indicators/${ind.slug}`}
                  className="group flex items-center gap-4 bg-[#111111] border border-[#1F2937] hover:border-[#374151] hover:bg-[#141414] rounded-xl p-4 transition-all duration-200"
                >
                  <RankBadge rank={i + 1} />
                  <div className="w-12 h-12 rounded-lg overflow-hidden bg-[#1A1A1A] flex-shrink-0">
                    {ind.imageUrl ? (
                      <img src={ind.imageUrl} alt={ind.name} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-gray-600">
                        <ChartBarIcon className="w-5 h-5" />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-semibold text-sm group-hover:text-amber-400 transition-colors truncate">{ind.name}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      {ind.platforms?.slice(0, 2).map((p) => (
                        <span key={p} className="text-[10px] text-gray-500">{p}</span>
                      ))}
                      {ind.listingType && (
                        <span className="text-[10px] text-gray-600">· {ind.listingType}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-4 flex-shrink-0 text-right">
                    {(ind.averageRating || ind.rating) > 0 && (
                      <div className="hidden sm:block">
                        <div className="flex items-center gap-1 justify-end">
                          <StarIcon className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                          <span className="text-amber-400 text-sm font-semibold">{(ind.averageRating || ind.rating || 0).toFixed(1)}</span>
                        </div>
                        <p className="text-gray-600 text-[10px]">{formatNumber(ind.reviewCount || 0)} reviews</p>
                      </div>
                    )}
                    {ind.views > 0 && (
                      <div className="hidden md:block">
                        <p className="text-white text-sm font-semibold">{formatNumber(ind.views)}</p>
                        <p className="text-gray-600 text-[10px]">views</p>
                      </div>
                    )}
                    <ArrowRightIcon className="w-4 h-4 text-gray-600 group-hover:text-amber-400 transition-colors" />
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-10 text-gray-600 text-sm">Trending data loading...</div>
          )}
        </section>

        {/* ══ 5. NEWEST ARRIVALS ═══════════════════════════════════════ */}
        <section className="py-12 border-b border-[#1A1A1A]">
          <SectionHeader
            title="⚡ Newest Arrivals"
            subtitle="Freshly submitted tools — be the first to review them"
            viewAllLink="/new"
            viewAllLabel="View All New"
          />
          {loading.newest ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
            </div>
          ) : newest?.length ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {newest.slice(0, 4).map((ind) => (
                <IndicatorCard key={ind._id} indicator={ind} />
              ))}
            </div>
          ) : (
            <div className="text-center py-10 text-gray-600 text-sm">New arrivals loading...</div>
          )}
        </section>

        {/* ══ 6. BROWSE BY CATEGORY ════════════════════════════════════ */}
        <section className="py-12 border-b border-[#1A1A1A]">
          <SectionHeader
            title="Browse by Category"
            subtitle="Find tools organized by strategy type and analysis method"
            viewAllLink="/categories"
            viewAllLabel="All Categories"
          />
          {loading.categories && !displayCategories.length ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="h-16 bg-[#111111] border border-[#1F2937] rounded-xl animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {displayCategories.slice(0, 8).map((cat, i) => (
                <CategoryCard key={cat._id || cat.slug} category={cat} index={i} />
              ))}
            </div>
          )}
        </section>

        {/* ══ 7. BROWSE BY LISTING TYPE ════════════════════════════════ */}
        <section className="py-12 border-b border-[#1A1A1A]">
          <SectionHeader
            title="Browse by Type"
            subtitle="Whatever you trade with — we have it covered"
          />
          <div className="flex flex-wrap gap-2">
            {LISTING_TYPES.map(({ label, type, color }) => (
              <Link
                key={type}
                to={`/type/${type}`}
                className={`inline-flex items-center gap-2 px-4 py-2.5 bg-[#111111] border ${color} rounded-full text-sm font-medium transition-all duration-200 hover:bg-[#141414]`}
              >
                {label}
                <ArrowRightIcon className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 -translate-x-1 group-hover:translate-x-0 transition-all" />
              </Link>
            ))}
          </div>
        </section>

        {/* ══ 8. BROWSE BY ASSET ═══════════════════════════════════════ */}
        <section className="py-12 border-b border-[#1A1A1A]">
          <SectionHeader
            title="Browse by Asset Class"
            subtitle="Filter tools designed for your specific market"
          />
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {ASSETS.map(({ label, emoji, asset, color }) => (
              <Link
                key={asset}
                to={`/assets/${asset}`}
                className={`group flex flex-col items-center gap-3 py-6 px-3 bg-gradient-to-b ${color} border rounded-xl text-center transition-all duration-200 hover:scale-[1.02]`}
              >
                <span className="text-3xl group-hover:scale-110 transition-transform duration-200">{emoji}</span>
                <span className="text-white text-sm font-semibold">{label}</span>
              </Link>
            ))}
          </div>
        </section>

        {/* ══ 9. FEATURED BROKERS ══════════════════════════════════════ */}
        <section className="py-12 border-b border-[#1A1A1A]">
          <div className="flex items-end justify-between mb-6">
            <div>
              <div className="inline-flex items-center gap-2 text-xs text-gray-600 bg-[#1A1A1A] border border-[#2A2A2A] rounded-full px-3 py-1 mb-2">
                <span>Sponsored</span>
              </div>
              <h2 className="text-2xl font-bold text-white">Featured Brokers</h2>
              <p className="text-sm text-gray-400 mt-1">Regulated brokers trusted by our community — earn exclusive bonuses</p>
            </div>
            <Link to="/brokers" className="text-amber-400 hover:text-amber-300 text-sm font-medium transition-colors whitespace-nowrap">
              View All →
            </Link>
          </div>
          {loading.brokers ? (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-52 bg-[#111111] border border-[#1F2937] rounded-xl animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {brokers.map((broker) => (
                <BrokerCard key={broker._id} broker={broker} />
              ))}
            </div>
          )}
        </section>

        {/* ══ 10. LATEST FROM BLOG ══════════════════════════════════════ */}
        <section className="py-12 border-b border-[#1A1A1A]">
          <SectionHeader
            title="Latest from the Blog"
            subtitle="Expert analysis, indicator reviews, and trading education"
            viewAllLink="/blog"
            viewAllLabel="Visit Blog"
          />
          {loading.blog ? (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[...Array(3)].map((_, i) => <BlogCardSkeleton key={i} />)}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {blogPosts.slice(0, 3).map((post) => (
                <BlogCard key={post._id || post.slug} post={post} />
              ))}
            </div>
          )}
        </section>

        {/* ══ 11. WHY INDICATORHUB ══════════════════════════════════════ */}
        <section className="py-12 border-b border-[#1A1A1A]">
          <div className="text-center mb-10">
            <h2 className="text-2xl sm:text-3xl font-bold text-white mb-3">Why IndicatorHub?</h2>
            <p className="text-gray-400 max-w-xl mx-auto text-sm">
              The trading tools market is full of hype, fake reviews, and manipulated backtests.
              We built IndicatorHub to fix that.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {TRUST_FEATURES.map(({ icon: Icon, title, desc, color, bg, border }) => (
              <div key={title} className={`bg-[#111111] border ${border} rounded-xl p-5 flex flex-col gap-3`}>
                <div className={`w-10 h-10 rounded-xl ${bg} flex items-center justify-center flex-shrink-0`}>
                  <Icon className={`w-5 h-5 ${color}`} />
                </div>
                <div>
                  <h3 className="text-white font-semibold text-sm mb-1.5">{title}</h3>
                  <p className="text-gray-500 text-xs leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ══ 12. SUBMIT CTA ════════════════════════════════════════════ */}
        <section className="py-12">
          <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-amber-600 via-amber-500 to-orange-500 p-px">
            <div className="relative bg-[#0E0C08] rounded-2xl px-6 sm:px-12 py-12 text-center overflow-hidden">
              {/* Background glow */}
              <div className="absolute inset-0 bg-gradient-to-br from-amber-500/10 to-orange-500/5 pointer-events-none" />
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-64 h-32 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />

              <div className="relative z-10">
                <div className="inline-flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 rounded-full px-4 py-1.5 text-amber-400 text-xs font-semibold mb-5">
                  <SparklesIcon className="w-3.5 h-3.5" />
                  Free to List · No Commission
                </div>
                <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-white mb-4 leading-tight">
                  List Your Indicator —{' '}
                  <span className="text-amber-400">Get Seen by 20M+ Traders</span>
                </h2>
                <p className="text-gray-400 text-sm sm:text-base max-w-xl mx-auto mb-8">
                  Submit your indicator, EA, bot, or signal service for free. Reach a massive audience of
                  active traders across every major platform. Zero upfront cost.
                </p>
                <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                  <Link
                    to="/submit"
                    className="inline-flex items-center gap-2.5 px-8 py-3.5 bg-amber-500 hover:bg-amber-400 text-black font-bold rounded-xl text-base transition-all duration-200 shadow-lg shadow-amber-500/20 hover:shadow-amber-500/40 hover:scale-105"
                  >
                    <ArrowTrendingUpIcon className="w-5 h-5" />
                    Submit Your Tool — It's Free
                  </Link>
                  <Link
                    to="/indicators"
                    className="inline-flex items-center gap-2 px-6 py-3.5 border border-[#374151] hover:border-[#4B5563] text-gray-300 hover:text-white font-medium rounded-xl text-base transition-all duration-200"
                  >
                    Browse Tools First
                  </Link>
                </div>
                <p className="text-gray-600 text-xs mt-5">
                  Already listed? <Link to="/submit" className="text-amber-500 hover:underline">Manage your listing →</Link>
                </p>
              </div>
            </div>
          </div>
        </section>

      </div>{/* end max-w-7xl */}
    </div>
  );
}









// 'use client'
// import React, { useEffect, useState } from 'react';
// import { Link, useNavigate } from 'react-router-dom';
// import {
//   FireIcon,
//   ShieldCheckIcon,
//   ChartBarIcon,
//   MagnifyingGlassIcon,
//   ArrowRightIcon,
//   StarIcon,
//   CheckBadgeIcon,
//   ExclamationTriangleIcon,
//   GlobeAltIcon,
//   DocumentChartBarIcon,
//   ArrowTrendingUpIcon,
//   SparklesIcon,
//   ClockIcon,
//   BookOpenIcon,
// } from '@heroicons/react/24/outline';
// import { useAppContext, value } from '../context/AppContext';

// import IndicatorCard from '../components/indicators/IndicatorCard';
// import SkeletonCard from '../components/ui/SkeletonCard';
// import StatCard from '../components/ui/StatCard';
// import SectionHeader from '../components/ui/SectionHeader';
// import {
//   getNewest,
//   getFeatured,
//   getTrending,
//   getFeaturedBrokers,
//   getBlogPosts,
//   getCategories,
//   getStats,
// } from '../utils/api';
// import { formatNumber } from '../utils/helpers';

// // ── Platform strip data ────────────────────────────────────────
// const PLATFORMS = [
//   { name: 'TradingView', color: '#2962FF', abbr: 'TV' },
//   { name: 'MetaTrader 4', color: '#8B5CF6', abbr: 'MT4' },
//   { name: 'MetaTrader 5', color: '#7C3AED', abbr: 'MT5' },
//   { name: 'cTrader', color: '#0EA5E9', abbr: 'cT' },
//   { name: 'NinjaTrader', color: '#F97316', abbr: 'NT' },
//   { name: 'ThinkOrSwim', color: '#06B6D4', abbr: 'ToS' },
//   { name: 'Binance', color: '#F59E0B', abbr: 'BNB' },
//   { name: 'Interactive Brokers', color: '#EF4444', abbr: 'IB' },
// ];

// // ── Listing types ──────────────────────────────────────────────
// const LISTING_TYPES = [
//   { label: 'Indicators', type: 'indicator', color: 'border-blue-700/50 hover:border-blue-500 text-blue-400' },
//   { label: 'Expert Advisors', type: 'ea', color: 'border-purple-700/50 hover:border-purple-500 text-purple-400' },
//   { label: 'Bots', type: 'bot', color: 'border-cyan-700/50 hover:border-cyan-500 text-cyan-400' },
//   { label: 'Signals', type: 'signal', color: 'border-pink-700/50 hover:border-pink-500 text-pink-400' },
//   { label: 'Strategies', type: 'strategy', color: 'border-orange-700/50 hover:border-orange-500 text-orange-400' },
//   { label: 'Screeners', type: 'screener', color: 'border-teal-700/50 hover:border-teal-500 text-teal-400' },
//   { label: 'Scripts', type: 'script', color: 'border-lime-700/50 hover:border-lime-500 text-lime-400' },
//   { label: 'Copy Trading', type: 'copy-trading', color: 'border-violet-700/50 hover:border-violet-500 text-violet-400' },
//   { label: 'Courses', type: 'course', color: 'border-yellow-700/50 hover:border-yellow-500 text-yellow-400' },
// ];

// // ── Asset classes ──────────────────────────────────────────────
// const ASSETS = [
//   { label: 'Crypto', emoji: '🪙', asset: 'crypto', color: 'from-amber-900/20 to-amber-900/5 border-amber-800/40 hover:border-amber-600/60' },
//   { label: 'Forex', emoji: '💱', asset: 'forex', color: 'from-blue-900/20 to-blue-900/5 border-blue-800/40 hover:border-blue-600/60' },
//   { label: 'Stocks', emoji: '📈', asset: 'stocks', color: 'from-green-900/20 to-green-900/5 border-green-800/40 hover:border-green-600/60' },
//   { label: 'Indices', emoji: '📊', asset: 'indices', color: 'from-purple-900/20 to-purple-900/5 border-purple-800/40 hover:border-purple-600/60' },
//   { label: 'Gold', emoji: '🥇', asset: 'gold', color: 'from-yellow-900/20 to-yellow-900/5 border-yellow-800/40 hover:border-yellow-600/60' },
//   { label: 'Oil', emoji: '🛢️', asset: 'oil', color: 'from-stone-900/20 to-stone-900/5 border-stone-700/40 hover:border-stone-500/60' },
// ];

// // ── Trust features ─────────────────────────────────────────────
// const TRUST_FEATURES = [
//   {
//     icon: CheckBadgeIcon,
//     title: 'Verified Reviews',
//     desc: 'Every review is authenticated against real purchase records. No fake testimonials, ever.',
//     color: 'text-emerald-400',
//     bg: 'bg-emerald-500/10',
//     border: 'border-emerald-800/30',
//   },
//   {
//     icon: DocumentChartBarIcon,
//     title: 'Backtest Audits',
//     desc: 'We audit submitted backtests for curve-fitting, look-ahead bias, and data manipulation.',
//     color: 'text-blue-400',
//     bg: 'bg-blue-500/10',
//     border: 'border-blue-800/30',
//   },
//   {
//     icon: ExclamationTriangleIcon,
//     title: 'Scam Detection',
//     desc: 'AI-powered red flag analysis flags misleading claims, fake win-rates, and known scam patterns.',
//     color: 'text-red-400',
//     bg: 'bg-red-500/10',
//     border: 'border-red-800/30',
//   },
//   {
//     icon: GlobeAltIcon,
//     title: 'Cross-Platform Discovery',
//     desc: 'Search across TradingView, MT4/5, cTrader, NinjaTrader and more — all in one place.',
//     color: 'text-amber-400',
//     bg: 'bg-amber-500/10',
//     border: 'border-amber-800/30',
//   },
// ];

// // ── Animated grid hero background ─────────────────────────────
// function AnimatedGrid() {
//   return (
//     <div className="absolute inset-0 overflow-hidden pointer-events-none">
//       <svg
//         className="absolute inset-0 w-full h-full opacity-[0.07]"
//         xmlns="http://www.w3.org/2000/svg"
//       >
//         <defs>
//           <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
//             <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#F59E0B" strokeWidth="0.5" />
//           </pattern>
//           <radialGradient id="fade" cx="50%" cy="50%" r="60%">
//             <stop offset="0%" stopColor="#0A0A0A" stopOpacity="0" />
//             <stop offset="100%" stopColor="#0A0A0A" stopOpacity="1" />
//           </radialGradient>
//         </defs>
//         <rect width="100%" height="100%" fill="url(#grid)" />
//         <rect width="100%" height="100%" fill="url(#fade)" />
//       </svg>
//       {/* Amber glow */}
//       <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-amber-500/5 rounded-full blur-3xl" />
//       {/* Subtle blue accent */}
//       <div className="absolute bottom-0 right-1/4 w-[400px] h-[200px] bg-blue-500/5 rounded-full blur-3xl" />
//     </div>
//   );
// }

// // ── Hero Search Bar ────────────────────────────────────────────
// function HeroSearchBar() {
//   const [query, setQuery] = useState('');
//   const navigate = useNavigate();
//   const { dispatch } = useAppContext();

//   const handleSubmit = (e) => {
//     e.preventDefault();
//     if (!query.trim()) return;
//     dispatch({ type: ACTIONS.SET_FILTER, payload: { search: query.trim() } });
//     navigate(`/indicators?search=${encodeURIComponent(query.trim())}`);
//   };

//   return (
//     <form onSubmit={handleSubmit} className="relative w-full max-w-2xl mx-auto">
//       <div className="relative flex items-center group">
//         <MagnifyingGlassIcon className="absolute left-5 w-5 h-5 text-gray-400 pointer-events-none z-10 group-focus-within:text-amber-400 transition-colors" />
//         <input
//           type="text"
//           value={query}
//           onChange={(e) => setQuery(e.target.value)}
//           placeholder="Search indicators, EAs, bots, strategies..."
//           className="w-full h-14 pl-14 pr-36 bg-[#111111] border border-[#2A2A2A] focus:border-amber-500/70 focus:ring-2 focus:ring-amber-500/20 outline-none rounded-xl text-white text-base placeholder-gray-500 transition-all duration-200 shadow-2xl"
//         />
//         <button
//           type="submit"
//           className="absolute right-2 h-10 px-5 bg-amber-500 hover:bg-amber-600 text-black font-semibold rounded-lg text-sm transition-colors duration-200 flex items-center gap-2"
//         >
//           <MagnifyingGlassIcon className="w-4 h-4" />
//           Search
//         </button>
//       </div>
//       <div className="flex items-center gap-3 mt-3 justify-center flex-wrap">
//         {['RSI Divergence', 'Scalping EA', 'MACD Bot', 'Supply & Demand'].map((q) => (
//           <button
//             key={q}
//             type="button"
//             onClick={() => { setQuery(q); }}
//             className="text-xs text-gray-500 hover:text-amber-400 bg-[#1A1A1A] hover:bg-amber-500/10 border border-[#2A2A2A] hover:border-amber-500/30 rounded-full px-3 py-1 transition-all duration-200"
//           >
//             {q}
//           </button>
//         ))}
//       </div>
//     </form>
//   );
// }

// // ── Rank Badge ─────────────────────────────────────────────────
// function RankBadge({ rank }) {
//   const colors = {
//     1: 'bg-amber-500 text-black border-amber-400',
//     2: 'bg-gray-300 text-black border-gray-200',
//     3: 'bg-amber-700 text-white border-amber-600',
//   };
//   return (
//     <div className={`w-8 h-8 rounded-full border-2 flex items-center justify-center font-bold text-sm flex-shrink-0 ${colors[rank] || 'bg-[#1F2937] text-gray-400 border-[#374151]'}`}>
//       {rank}
//     </div>
//   );
// }

// // ── Skeleton loaders ───────────────────────────────────────────
// function StatSkeleton() {
//   return (
//     <div className="bg-[#111111] border border-[#1F2937] rounded-xl p-4 animate-pulse">
//       <div className="flex items-start justify-between">
//         <div>
//           <div className="h-3 w-24 bg-[#1F2937] rounded mb-2" />
//           <div className="h-7 w-16 bg-[#1F2937] rounded" />
//         </div>
//         <div className="w-9 h-9 rounded-lg bg-[#1F2937]" />
//       </div>
//     </div>
//   );
// }

// function BlogCardSkeleton() {
//   return (
//     <div className="bg-[#111111] border border-[#1F2937] rounded-xl overflow-hidden animate-pulse">
//       <div className="h-44 bg-[#1A1A1A]" />
//       <div className="p-4 space-y-2">
//         <div className="h-4 bg-[#1F2937] rounded w-4/5" />
//         <div className="h-3 bg-[#1A1A1A] rounded w-full" />
//         <div className="h-3 bg-[#1A1A1A] rounded w-3/4" />
//         <div className="h-3 bg-[#1A1A1A] rounded w-1/3 mt-3" />
//       </div>
//     </div>
//   );
// }

// // ── Broker Card ────────────────────────────────────────────────
// function BrokerCard({ broker }) {
//   return (
//     <div className="bg-[#111111] border border-[#1F2937] hover:border-[#374151] rounded-xl p-5 flex flex-col gap-4 transition-all duration-200 group">
//       {/* Header */}
//       <div className="flex items-center gap-3">
//         <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#1F2937] to-[#111111] border border-[#2A2A2A] flex items-center justify-center font-bold text-amber-400 text-sm flex-shrink-0 group-hover:border-amber-500/30 transition-colors">
//           {broker.logoUrl ? (
//             <img src={broker.logoUrl} alt={broker.name} className="w-8 h-8 object-contain rounded" onError={(e) => { e.target.style.display='none'; }} />
//           ) : (
//             (broker.name || 'BR').slice(0, 2).toUpperCase()
//           )}
//         </div>
//         <div className="min-w-0">
//           <p className="text-white font-semibold text-sm truncate">{broker.name || 'Premier Broker'}</p>
//           <div className="flex items-center gap-1.5 mt-0.5">
//             {(broker.isRegulated || broker.regulated) && (
//               <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-800/40 rounded px-1.5 py-0.5">
//                 <ShieldCheckIcon className="w-2.5 h-2.5" />
//                 Regulated
//               </span>
//             )}
//             {broker.regulatoryBody && (
//               <span className="text-[10px] text-gray-500">{broker.regulatoryBody}</span>
//             )}
//           </div>
//         </div>
//       </div>

//       {/* Stats */}
//       <div className="grid grid-cols-2 gap-3">
//         <div className="bg-[#0D0D0D] rounded-lg p-2.5 text-center">
//           <p className="text-[10px] text-gray-500 mb-0.5">CPA / Lead</p>
//           <p className="text-amber-400 font-bold text-sm">{broker.cpaValue ? `$${broker.cpaValue}` : broker.cpa || '$250'}</p>
//         </div>
//         <div className="bg-[#0D0D0D] rounded-lg p-2.5 text-center">
//           <p className="text-[10px] text-gray-500 mb-0.5">Min Deposit</p>
//           <p className="text-white font-bold text-sm">{broker.minDeposit ? `$${broker.minDeposit}` : '$10'}</p>
//         </div>
//       </div>

//       {/* Platforms */}
//       {broker.platforms?.length > 0 && (
//         <div className="flex flex-wrap gap-1">
//           {broker.platforms.slice(0, 3).map((p) => (
//             <span key={p} className="text-[10px] bg-blue-900/30 text-blue-400 border border-blue-800/40 rounded px-1.5 py-0.5">{p}</span>
//           ))}
//         </div>
//       )}

//       <a
//         href={broker.affiliateUrl || broker.website || '#'}
//         target="_blank"
//         rel="noopener noreferrer sponsored"
//         className="w-full btn-primary py-2.5 text-sm rounded-lg mt-auto"
//       >
//         Get Bonus →
//       </a>
//     </div>
//   );
// }

// // ── Blog Post Card ─────────────────────────────────────────────
// function BlogCard({ post }) {
//   const date = post.publishedAt || post.createdAt;
//   const formatted = date ? new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '';
//   return (
//     <Link to={`/blog/${post.slug}`} className="group bg-[#111111] border border-[#1F2937] hover:border-[#374151] rounded-xl overflow-hidden flex flex-col transition-all duration-200">
//       <div className="h-44 bg-gradient-to-br from-[#1A1A1A] to-[#0D0D0D] relative overflow-hidden">
//         {post.coverImage || post.cover ? (
//           <img
//             src={post.coverImage || post.cover}
//             alt={post.title}
//             className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
//             onError={(e) => { e.target.style.display = 'none'; }}
//           />
//         ) : (
//           <div className="absolute inset-0 flex items-center justify-center">
//             <BookOpenIcon className="w-10 h-10 text-[#2A2A2A]" />
//           </div>
//         )}
//         {post.category && (
//           <span className="absolute top-3 left-3 text-[10px] font-medium bg-amber-500 text-black px-2 py-0.5 rounded-full">
//             {post.category}
//           </span>
//         )}
//       </div>
//       <div className="p-4 flex flex-col gap-2 flex-1">
//         <h3 className="text-white font-semibold text-sm leading-snug group-hover:text-amber-400 transition-colors line-clamp-2">
//           {post.title}
//         </h3>
//         {post.excerpt && (
//           <p className="text-gray-500 text-xs leading-relaxed line-clamp-2">{post.excerpt}</p>
//         )}
//         <div className="flex items-center gap-3 mt-auto pt-2 text-[11px] text-gray-500">
//           {post.readTime && (
//             <span className="flex items-center gap-1">
//               <ClockIcon className="w-3 h-3" />
//               {post.readTime} min read
//             </span>
//           )}
//           {formatted && <span>{formatted}</span>}
//         </div>
//       </div>
//     </Link>
//   );
// }

// // ── Category Card ──────────────────────────────────────────────
// const CATEGORY_COLORS = [
//   'border-blue-700/40 hover:border-blue-500/60',
//   'border-purple-700/40 hover:border-purple-500/60',
//   'border-teal-700/40 hover:border-teal-500/60',
//   'border-amber-700/40 hover:border-amber-500/60',
//   'border-pink-700/40 hover:border-pink-500/60',
//   'border-green-700/40 hover:border-green-500/60',
//   'border-orange-700/40 hover:border-orange-500/60',
//   'border-cyan-700/40 hover:border-cyan-500/60',
// ];

// const CATEGORY_ICON_COLORS = ['text-blue-400','text-purple-400','text-teal-400','text-amber-400','text-pink-400','text-green-400','text-orange-400','text-cyan-400'];

// function CategoryCard({ category, index }) {
//   const border = CATEGORY_COLORS[index % CATEGORY_COLORS.length];
//   const iconColor = CATEGORY_ICON_COLORS[index % CATEGORY_ICON_COLORS.length];
//   return (
//     <Link
//       to={`/categories/${category.slug}`}
//       className={`group bg-[#111111] border ${border} rounded-xl p-4 flex items-center gap-3 transition-all duration-200 hover:bg-[#141414]`}
//     >
//       <span className={`text-2xl flex-shrink-0 ${iconColor}`}>
//         {category.icon || category.emoji || '📁'}
//       </span>
//       <div className="min-w-0">
//         <p className="text-white text-sm font-medium truncate group-hover:text-amber-400 transition-colors">
//           {category.name}
//         </p>
//         <p className="text-gray-500 text-xs mt-0.5">
//           {formatNumber(category.count || category.toolCount || 0)} tools
//         </p>
//       </div>
//       <ArrowRightIcon className="w-3.5 h-3.5 text-gray-600 group-hover:text-amber-400 ml-auto flex-shrink-0 transition-colors" />
//     </Link>
//   );
// }

// // ── Fallback data for when API is unavailable ──────────────────
// const FALLBACK_STATS = {
//   totalIndicators: 4200,
//   platformCount: 12,
//   reviewCount: 28500,
//   avgTrustScore: 78,
// };

// const FALLBACK_BROKERS = [
//   { _id: '1', name: 'IC Markets', isRegulated: true, regulatoryBody: 'ASIC / CySEC', cpaValue: 600, minDeposit: 200, platforms: ['MT4', 'MT5', 'cTrader'], affiliateUrl: '#' },
//   { _id: '2', name: 'Pepperstone', isRegulated: true, regulatoryBody: 'FCA / ASIC', cpaValue: 500, minDeposit: 0, platforms: ['MT4', 'MT5', 'TradingView'], affiliateUrl: '#' },
//   { _id: '3', name: 'XM Global', isRegulated: true, regulatoryBody: 'CySEC / IFSC', cpaValue: 400, minDeposit: 5, platforms: ['MT4', 'MT5'], affiliateUrl: '#' },
// ];

// const FALLBACK_BLOG = [
//   { _id: '1', slug: 'best-rsi-indicators-2024', title: 'The 7 Best RSI Indicators for TradingView in 2024', excerpt: 'We tested dozens of RSI variants — here are the ones that actually improve your entries.', readTime: 8, category: 'Indicators', publishedAt: new Date().toISOString() },
//   { _id: '2', slug: 'ea-vs-manual-trading', title: 'Expert Advisors vs Manual Trading: Which Wins Long-Term?', excerpt: 'A data-driven comparison across 3 years of live trading to settle the debate once and for all.', readTime: 12, category: 'EAs', publishedAt: new Date().toISOString() },
//   { _id: '3', slug: 'backtest-audit-guide', title: 'How to Spot a Fake Backtest in Under 60 Seconds', excerpt: "Most published backtests are curve-fitted or cherry-picked. Here's how to tell.", readTime: 6, category: 'Education', publishedAt: new Date().toISOString() },
// ];

// const FALLBACK_CATEGORIES = [
//   { slug: 'momentum', name: 'Momentum', icon: '🚀', count: 340 },
//   { slug: 'trend-following', name: 'Trend Following', icon: '📈', count: 520 },
//   { slug: 'mean-reversion', name: 'Mean Reversion', icon: '🔄', count: 210 },
//   { slug: 'volume', name: 'Volume Analysis', icon: '📊', count: 180 },
//   { slug: 'oscillators', name: 'Oscillators', icon: '〰️', count: 290 },
//   { slug: 'support-resistance', name: 'Support & Resistance', icon: '🔲', count: 445 },
//   { slug: 'volatility', name: 'Volatility', icon: '⚡', count: 160 },
//   { slug: 'price-action', name: 'Price Action', icon: '🕯️', count: 380 },
// ];

// // ══════════════════════════════════════════════════════════════
// // HOME PAGE
// // ══════════════════════════════════════════════════════════════
// export default function Home() {
//   const { filters, dispatch } = useAppContext(); 

//   const [trending, setTrending] = useState([]);
//   const [featured, setFeatured] = useState([]);
//   const [newest, setNewest] = useState([]);
//   const [brokers, setBrokers] = useState([]);
//   const [blogPosts, setBlogPosts] = useState([]);
//   const [localStats, setLocalStats] = useState(null);
//   const [localCategories, setLocalCategories] = useState([]);

//   // FIX 1: stats aur categories variables ko yahan se hata diya
//   const [loading, setLoading] = useState({
//     newest: true,
//     brokers: true,
//     blog: true,
//     stats: true,
//     categories: true,
//   });

//   useEffect(() => {
//     // Newest
//     getNewest()
//       .then((r) => setNewest((r?.data || r || []).slice(0, 4)))
//       .catch(() => {})
//       .finally(() => setLoading((p) => ({ ...p, newest: false })));

//     // Brokers
//     getFeaturedBrokers()
//       .then((r) => {
//         const data = r?.data || r || [];
//         setBrokers(data.length ? data.slice(0, 3) : FALLBACK_BROKERS);
//       })
//       .catch(() => setBrokers(FALLBACK_BROKERS))
//       .finally(() => setLoading((p) => ({ ...p, brokers: false })));

//     // Blog
//     getBlogPosts({ limit: 3, sort: 'newest' })
//       .then((r) => {
//         const data = r?.data || r || [];
//         setBlogPosts(data.length ? data : FALLBACK_BLOG);
//       })
//       .catch(() => setBlogPosts(FALLBACK_BLOG))
//       .finally(() => setLoading((p) => ({ ...p, blog: false })));

//     // FIX 2: if condition hata kar direct API call kiya
//     getStats()
//       .then((r) => {
//         const data = r?.data || r;
//         setLocalStats(data || FALLBACK_STATS);
//       })
//       .catch(() => setLocalStats(FALLBACK_STATS))
//       .finally(() => setLoading((p) => ({ ...p, stats: false })));

//     // FIX 3: if condition hata kar direct API call kiya
//     getCategories()
//       .then((r) => {
//         const data = r?.data || r || [];
//         setLocalCategories(data.length ? data : FALLBACK_CATEGORIES);
//       })
//       .catch(() => setLocalCategories(FALLBACK_CATEGORIES))
//       .finally(() => setLoading((p) => ({ ...p, categories: false })));
//   }, []); // eslint-disable-line react-hooks/exhaustive-deps

//   const displayStats = localStats || FALLBACK_STATS;
//   const displayCategories = localCategories.length ? localCategories : FALLBACK_CATEGORIES;

//   return (
//     <div className="min-h-screen bg-[#0A0A0A]">

//       {/* ══ 1. HERO ══════════════════════════════════════════════════ */}
//       <section className="relative min-h-[520px] flex flex-col items-center justify-center px-4 pt-16 pb-12 text-center overflow-hidden border-b border-[#1A1A1A]">
//         <AnimatedGrid />

//         <div className="relative z-10 w-full max-w-4xl mx-auto">
//           {/* Pill badge */}
//           <div className="inline-flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 rounded-full px-4 py-1.5 text-amber-400 text-xs font-semibold mb-6 backdrop-blur">
//             <FireIcon className="w-3.5 h-3.5" />
//             The #1 Trading Tools Directory — {formatNumber(displayStats?.totalIndicators || 4200)}+ Tools Listed
//           </div>

//           {/* Headline */}
//           <h1 className="text-4xl sm:text-5xl lg:text-[3.5rem] font-extrabold text-white leading-[1.1] tracking-tight mb-5">
//             Discover the World's Best{' '}
//             <span className="text-amber-400">Trading Indicators</span>,{' '}
//             <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-orange-400">EAs, Bots</span>{' '}
//             &amp; Strategies
//           </h1>

//           {/* Sub-headline */}
//           <p className="text-gray-400 text-base sm:text-lg max-w-2xl mx-auto mb-8 leading-relaxed">
//             <span className="text-gray-300">Verified reviews</span>
//             <span className="mx-2 text-[#374151]">·</span>
//             <span className="text-gray-300">Cross-platform</span>
//             <span className="mx-2 text-[#374151]">·</span>
//             <span className="text-gray-300">Backtest audits</span>
//             <span className="mx-2 text-[#374151]">·</span>
//             <span className="text-gray-300">Scam detection</span>
//           </p>

//           {/* Search bar */}
//           <HeroSearchBar />

//           {/* Platform strip */}
//           <div className="mt-10">
//             <p className="text-gray-600 text-xs font-medium mb-4 uppercase tracking-widest">Works with</p>
//             <div className="flex items-center justify-center flex-wrap gap-3">
//               {PLATFORMS.map((p) => (
//                 <Link
//                   key={p.name}
//                   to={`/platforms/${p.name.toLowerCase().replace(/\s+/g, '-')}`}
//                   className="flex items-center gap-2 px-3 py-1.5 bg-[#111111] border border-[#1F2937] hover:border-[#374151] rounded-lg transition-all duration-200 group"
//                   title={p.name}
//                 >
//                   <div
//                     className="w-5 h-5 rounded flex items-center justify-center text-[9px] font-bold text-white flex-shrink-0"
//                     style={{ backgroundColor: p.color + '33', border: `1px solid ${p.color}55`, color: p.color }}
//                   >
//                     {p.abbr.slice(0, 2)}
//                   </div>
//                   <span className="text-gray-400 text-xs group-hover:text-white transition-colors hidden sm:inline">{p.name}</span>
//                   <span className="text-gray-400 text-xs group-hover:text-white transition-colors sm:hidden">{p.abbr}</span>
//                 </Link>
//               ))}
//             </div>
//           </div>
//         </div>
//       </section>

//       {/* ══ 2. STATS BAR ══════════════════════════════════════════════ */}
//       <section className="border-b border-[#1A1A1A] bg-[#0D0D0D]">
//         <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
//           {loading.stats && !displayStats ? (
//             <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
//               {[...Array(4)].map((_, i) => <StatSkeleton key={i} />)}
//             </div>
//           ) : displayStats ? (
//             <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
//               <StatCard
//                 icon={ChartBarIcon}
//                 label="Total Tools"
//                 value={formatNumber(displayStats.totalIndicators || displayStats.totalTools || 4200)}
//               />
//               <StatCard
//                 icon={GlobeAltIcon}
//                 label="Platforms Covered"
//                 value={formatNumber(displayStats.platformCount || displayStats.platforms || 12)}
//               />
//               <StatCard
//                 icon={StarIcon}
//                 label="Verified Reviews"
//                 value={formatNumber(displayStats.reviewCount || displayStats.reviews || 28500)}
//               />
//               <StatCard
//                 icon={ShieldCheckIcon}
//                 label="Avg Trust Score"
//                 value={`${displayStats.avgTrustScore || displayStats.trustScore || 78}%`}
//               />
//             </div>
//           ) : null}
//         </div>
//       </section>

//       <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

//         {/* ══ 3. FEATURED TOOLS ═══════════════════════════════════════ */}
//         <section className="py-12 border-b border-[#1A1A1A]">
//           <SectionHeader
//             title="⭐ Featured Tools"
//             subtitle="Editor picks — handpicked for quality, documentation, and real-world results"
//             viewAllLink="/indicators?sort=featured"
//             viewAllLabel="View All Featured"
//           />
//           {loading.featured ? (
//             <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
//               {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
//             </div>
//           ) : featured?.length ? (
//             <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
//               {featured.slice(0, 4).map((ind) => (
//                 <IndicatorCard key={ind._id} indicator={ind} />
//               ))}
//             </div>
//           ) : (
//             <div className="text-center py-10 text-gray-600 text-sm">Featured tools loading...</div>
//           )}
//         </section>

//         {/* ══ 4. TRENDING THIS WEEK ════════════════════════════════════ */}
//         <section className="py-12 border-b border-[#1A1A1A]">
//           <SectionHeader
//             title="🔥 Trending This Week"
//             subtitle="Most viewed and wishlisted by the community in the last 7 days"
//             viewAllLink="/trending"
//             viewAllLabel="View All Trending"
//           />
//           {loading.trending ? (
//             <div className="space-y-3">
//               {[...Array(4)].map((_, i) => (
//                 <div key={i} className="h-20 bg-[#111111] border border-[#1F2937] rounded-xl animate-pulse" />
//               ))}
//             </div>
//           ) : trending?.length ? (
//             <div className="space-y-3">
//               {trending.slice(0, 6).map((ind, i) => (
//                 <Link
//                   key={ind._id}
//                   to={`/indicators/${ind.slug}`}
//                   className="group flex items-center gap-4 bg-[#111111] border border-[#1F2937] hover:border-[#374151] hover:bg-[#141414] rounded-xl p-4 transition-all duration-200"
//                 >
//                   <RankBadge rank={i + 1} />
//                   <div className="w-12 h-12 rounded-lg overflow-hidden bg-[#1A1A1A] flex-shrink-0">
//                     {ind.imageUrl ? (
//                       <img src={ind.imageUrl} alt={ind.name} className="w-full h-full object-cover" />
//                     ) : (
//                       <div className="w-full h-full flex items-center justify-center text-gray-600">
//                         <ChartBarIcon className="w-5 h-5" />
//                       </div>
//                     )}
//                   </div>
//                   <div className="flex-1 min-w-0">
//                     <p className="text-white font-semibold text-sm group-hover:text-amber-400 transition-colors truncate">{ind.name}</p>
//                     <div className="flex items-center gap-2 mt-0.5">
//                       {ind.platforms?.slice(0, 2).map((p) => (
//                         <span key={p} className="text-[10px] text-gray-500">{p}</span>
//                       ))}
//                       {ind.listingType && (
//                         <span className="text-[10px] text-gray-600">· {ind.listingType}</span>
//                       )}
//                     </div>
//                   </div>
//                   <div className="flex items-center gap-4 flex-shrink-0 text-right">
//                     {(ind.averageRating || ind.rating) > 0 && (
//                       <div className="hidden sm:block">
//                         <div className="flex items-center gap-1 justify-end">
//                           <StarIcon className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
//                           <span className="text-amber-400 text-sm font-semibold">{(ind.averageRating || ind.rating || 0).toFixed(1)}</span>
//                         </div>
//                         <p className="text-gray-600 text-[10px]">{formatNumber(ind.reviewCount || 0)} reviews</p>
//                       </div>
//                     )}
//                     {ind.views > 0 && (
//                       <div className="hidden md:block">
//                         <p className="text-white text-sm font-semibold">{formatNumber(ind.views)}</p>
//                         <p className="text-gray-600 text-[10px]">views</p>
//                       </div>
//                     )}
//                     <ArrowRightIcon className="w-4 h-4 text-gray-600 group-hover:text-amber-400 transition-colors" />
//                   </div>
//                 </Link>
//               ))}
//             </div>
//           ) : (
//             <div className="text-center py-10 text-gray-600 text-sm">Trending data loading...</div>
//           )}
//         </section>

//         {/* ══ 5. NEWEST ARRIVALS ═══════════════════════════════════════ */}
//         <section className="py-12 border-b border-[#1A1A1A]">
//           <SectionHeader
//             title="⚡ Newest Arrivals"
//             subtitle="Freshly submitted tools — be the first to review them"
//             viewAllLink="/new"
//             viewAllLabel="View All New"
//           />
//           {loading.newest ? (
//             <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
//               {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
//             </div>
//           ) : newest?.length ? (
//             <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
//               {newest.slice(0, 4).map((ind) => (
//                 <IndicatorCard key={ind._id} indicator={ind} />
//               ))}
//             </div>
//           ) : (
//             <div className="text-center py-10 text-gray-600 text-sm">New arrivals loading...</div>
//           )}
//         </section>

//         {/* ══ 6. BROWSE BY CATEGORY ════════════════════════════════════ */}
//         <section className="py-12 border-b border-[#1A1A1A]">
//           <SectionHeader
//             title="Browse by Category"
//             subtitle="Find tools organized by strategy type and analysis method"
//             viewAllLink="/categories"
//             viewAllLabel="All Categories"
//           />
//           {loading.categories && !displayCategories.length ? (
//             <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
//               {[...Array(8)].map((_, i) => (
//                 <div key={i} className="h-16 bg-[#111111] border border-[#1F2937] rounded-xl animate-pulse" />
//               ))}
//             </div>
//           ) : (
//             <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
//               {displayCategories.slice(0, 8).map((cat, i) => (
//                 <CategoryCard key={cat._id || cat.slug} category={cat} index={i} />
//               ))}
//             </div>
//           )}
//         </section>

//         {/* ══ 7. BROWSE BY LISTING TYPE ════════════════════════════════ */}
//         <section className="py-12 border-b border-[#1A1A1A]">
//           <SectionHeader
//             title="Browse by Type"
//             subtitle="Whatever you trade with — we have it covered"
//           />
//           <div className="flex flex-wrap gap-2">
//             {LISTING_TYPES.map(({ label, type, color }) => (
//               <Link
//                 key={type}
//                 to={`/type/${type}`}
//                 className={`inline-flex items-center gap-2 px-4 py-2.5 bg-[#111111] border ${color} rounded-full text-sm font-medium transition-all duration-200 hover:bg-[#141414]`}
//               >
//                 {label}
//                 <ArrowRightIcon className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 -translate-x-1 group-hover:translate-x-0 transition-all" />
//               </Link>
//             ))}
//           </div>
//         </section>

//         {/* ══ 8. BROWSE BY ASSET ═══════════════════════════════════════ */}
//         <section className="py-12 border-b border-[#1A1A1A]">
//           <SectionHeader
//             title="Browse by Asset Class"
//             subtitle="Filter tools designed for your specific market"
//           />
//           <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
//             {ASSETS.map(({ label, emoji, asset, color }) => (
//               <Link
//                 key={asset}
//                 to={`/assets/${asset}`}
//                 className={`group flex flex-col items-center gap-3 py-6 px-3 bg-gradient-to-b ${color} border rounded-xl text-center transition-all duration-200 hover:scale-[1.02]`}
//               >
//                 <span className="text-3xl group-hover:scale-110 transition-transform duration-200">{emoji}</span>
//                 <span className="text-white text-sm font-semibold">{label}</span>
//               </Link>
//             ))}
//           </div>
//         </section>

//         {/* ══ 9. FEATURED BROKERS ══════════════════════════════════════ */}
//         <section className="py-12 border-b border-[#1A1A1A]">
//           <div className="flex items-end justify-between mb-6">
//             <div>
//               <div className="inline-flex items-center gap-2 text-xs text-gray-600 bg-[#1A1A1A] border border-[#2A2A2A] rounded-full px-3 py-1 mb-2">
//                 <span>Sponsored</span>
//               </div>
//               <h2 className="text-2xl font-bold text-white">Featured Brokers</h2>
//               <p className="text-sm text-gray-400 mt-1">Regulated brokers trusted by our community — earn exclusive bonuses</p>
//             </div>
//             <Link to="/brokers" className="text-amber-400 hover:text-amber-300 text-sm font-medium transition-colors whitespace-nowrap">
//               View All →
//             </Link>
//           </div>
//           {loading.brokers ? (
//             <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
//               {[...Array(3)].map((_, i) => (
//                 <div key={i} className="h-52 bg-[#111111] border border-[#1F2937] rounded-xl animate-pulse" />
//               ))}
//             </div>
//           ) : (
//             <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
//               {brokers.map((broker) => (
//                 <BrokerCard key={broker._id} broker={broker} />
//               ))}
//             </div>
//           )}
//         </section>

//         {/* ══ 10. LATEST FROM BLOG ══════════════════════════════════════ */}
//         <section className="py-12 border-b border-[#1A1A1A]">
//           <SectionHeader
//             title="Latest from the Blog"
//             subtitle="Expert analysis, indicator reviews, and trading education"
//             viewAllLink="/blog"
//             viewAllLabel="Visit Blog"
//           />
//           {loading.blog ? (
//             <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
//               {[...Array(3)].map((_, i) => <BlogCardSkeleton key={i} />)}
//             </div>
//           ) : (
//             <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
//               {blogPosts.slice(0, 3).map((post) => (
//                 <BlogCard key={post._id || post.slug} post={post} />
//               ))}
//             </div>
//           )}
//         </section>

//         {/* ══ 11. WHY INDICATORHUB ══════════════════════════════════════ */}
//         <section className="py-12 border-b border-[#1A1A1A]">
//           <div className="text-center mb-10">
//             <h2 className="text-2xl sm:text-3xl font-bold text-white mb-3">Why IndicatorHub?</h2>
//             <p className="text-gray-400 max-w-xl mx-auto text-sm">
//               The trading tools market is full of hype, fake reviews, and manipulated backtests.
//               We built IndicatorHub to fix that.
//             </p>
//           </div>
//           <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
//             {TRUST_FEATURES.map(({ icon: Icon, title, desc, color, bg, border }) => (
//               <div key={title} className={`bg-[#111111] border ${border} rounded-xl p-5 flex flex-col gap-3`}>
//                 <div className={`w-10 h-10 rounded-xl ${bg} flex items-center justify-center flex-shrink-0`}>
//                   <Icon className={`w-5 h-5 ${color}`} />
//                 </div>
//                 <div>
//                   <h3 className="text-white font-semibold text-sm mb-1.5">{title}</h3>
//                   <p className="text-gray-500 text-xs leading-relaxed">{desc}</p>
//                 </div>
//               </div>
//             ))}
//           </div>
//         </section>

//         {/* ══ 12. SUBMIT CTA ════════════════════════════════════════════ */}
//         <section className="py-12">
//           <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-amber-600 via-amber-500 to-orange-500 p-px">
//             <div className="relative bg-[#0E0C08] rounded-2xl px-6 sm:px-12 py-12 text-center overflow-hidden">
//               {/* Background glow */}
//               <div className="absolute inset-0 bg-gradient-to-br from-amber-500/10 to-orange-500/5 pointer-events-none" />
//               <div className="absolute top-0 left-1/2 -translate-x-1/2 w-64 h-32 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />

//               <div className="relative z-10">
//                 <div className="inline-flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 rounded-full px-4 py-1.5 text-amber-400 text-xs font-semibold mb-5">
//                   <SparklesIcon className="w-3.5 h-3.5" />
//                   Free to List · No Commission
//                 </div>
//                 <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-white mb-4 leading-tight">
//                   List Your Indicator —{' '}
//                   <span className="text-amber-400">Get Seen by 20M+ Traders</span>
//                 </h2>
//                 <p className="text-gray-400 text-sm sm:text-base max-w-xl mx-auto mb-8">
//                   Submit your indicator, EA, bot, or signal service for free. Reach a massive audience of
//                   active traders across every major platform. Zero upfront cost.
//                 </p>
//                 <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
//                   <Link
//                     to="/submit"
//                     className="inline-flex items-center gap-2.5 px-8 py-3.5 bg-amber-500 hover:bg-amber-400 text-black font-bold rounded-xl text-base transition-all duration-200 shadow-lg shadow-amber-500/20 hover:shadow-amber-500/40 hover:scale-105"
//                   >
//                     <ArrowTrendingUpIcon className="w-5 h-5" />
//                     Submit Your Tool — It's Free
//                   </Link>
//                   <Link
//                     to="/indicators"
//                     className="inline-flex items-center gap-2 px-6 py-3.5 border border-[#374151] hover:border-[#4B5563] text-gray-300 hover:text-white font-medium rounded-xl text-base transition-all duration-200"
//                   >
//                     Browse Tools First
//                   </Link>
//                 </div>
//                 <p className="text-gray-600 text-xs mt-5">
//                   Already listed? <Link to="/submit" className="text-amber-500 hover:underline">Manage your listing →</Link>
//                 </p>
//               </div>
//             </div>
//           </div>
//         </section>

//       </div>{/* end max-w-7xl */}
//     </div>
//   );
// }
