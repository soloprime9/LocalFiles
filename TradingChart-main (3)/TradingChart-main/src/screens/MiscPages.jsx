'use client';
import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import IndicatorCard from '../components/common/IndicatorCard';
import { SkeletonCard, EmptyState } from '../components/common/UI';
import {
  getByStrategy,
  getByAsset,
  getByListingType,
  getSignals,
  getBrokers,
  getBlogPosts,
  getBlogPost,
} from '../utils/api';
import { getAssetEmoji, timeAgo, formatNumber } from '../utils/helpers';
import {
  ExclamationCircleIcon,
  ChevronRightIcon,
  SignalIcon,
  BuildingLibraryIcon,
} from '@heroicons/react/24/outline';

// ─── Strategies ───────────────────────────────────────────────
const STRATEGY_TYPES = [
  { slug: 'trend-following', label: 'Trend Following', emoji: '📈' },
  { slug: 'mean-reversion', label: 'Mean Reversion', emoji: '🔄' },
  { slug: 'breakout', label: 'Breakout', emoji: '💥' },
  { slug: 'scalping', label: 'Scalping', emoji: '⚡' },
  { slug: 'swing', label: 'Swing Trading', emoji: '🌊' },
  { slug: 'momentum', label: 'Momentum', emoji: '🚀' },
  { slug: 'arbitrage', label: 'Arbitrage', emoji: '⚖️' },
  { slug: 'price-action', label: 'Price Action', emoji: '🕯️' },
];

export function Strategies() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="mb-8">
        <h1 className="section-title">Trading Strategies</h1>
        <p className="section-subtitle">Browse tools by strategy type</p>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        {STRATEGY_TYPES.map(({ slug, label, emoji }) => (
          <Link
            key={slug}
            to={`/strategies/${slug}`}
            className="card card-hover p-5 flex items-center gap-3 group"
          >
            <span className="text-2xl">{emoji}</span>
            <span className="text-white text-sm font-medium group-hover:text-amber-400 transition-colors">
              {label}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}

export function StrategyPage() {
  const { type } = useParams();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const strategy = STRATEGY_TYPES.find((s) => s.slug === type);

  useEffect(() => {
    setLoading(true);
    getByStrategy(type)
      .then((r) => {
        const data = r?.data || r;
        setItems(Array.isArray(data) ? data : []);
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [type]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="mb-8">
        <h1 className="section-title">
          {strategy?.emoji} {strategy?.label || type} Tools
        </h1>
      </div>
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : items.length === 0 ? (
        <EmptyState title="No tools found for this strategy" />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {items.map((ind) => <IndicatorCard key={ind._id} indicator={ind} />)}
        </div>
      )}
    </div>
  );
}

// ─── Asset Page ───────────────────────────────────────────────
export function AssetPage() {
  const { assetClass } = useParams();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getByAsset(assetClass)
      .then((r) => {
        const data = r?.data || r;
        setItems(Array.isArray(data) ? data : []);
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [assetClass]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="mb-8">
        <h1 className="section-title capitalize">
          {getAssetEmoji(assetClass)} {assetClass} Tools
        </h1>
      </div>
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : items.length === 0 ? (
        <EmptyState title="No tools found for this asset class" />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {items.map((ind) => <IndicatorCard key={ind._id} indicator={ind} />)}
        </div>
      )}
    </div>
  );
}

// ─── Listing Type Page ────────────────────────────────────────
export function ListingTypePage() {
  const { listingType } = useParams();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getByListingType(listingType)
      .then((r) => {
        const data = r?.data || r;
        setItems(Array.isArray(data) ? data : []);
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [listingType]);

  const labels = { ea: 'Expert Advisors', bot: 'Trading Bots', signal: 'Signal Services' };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="mb-8">
        <h1 className="section-title capitalize">
          {labels[listingType] || `${listingType}s`}
        </h1>
      </div>
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : items.length === 0 ? (
        <EmptyState title="No tools found for this listing type" />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {items.map((ind) => <IndicatorCard key={ind._id} indicator={ind} />)}
        </div>
      )}
    </div>
  );
}

// ─── Signals ──────────────────────────────────────────────────
export function Signals() {
  const [signals, setSignals] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSignals()
      .then((r) => {
        const data = r?.data || r;
        setSignals(Array.isArray(data) ? data : []);
      })
      .catch(() => setSignals([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="mb-8">
        <h1 className="section-title">📡 Signal Services</h1>
        <p className="section-subtitle">Live trading signals from verified providers</p>
      </div>
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : signals.length === 0 ? (
        <EmptyState title="No signals available" icon={SignalIcon} description="Check back soon for trading signal services." />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {signals.map((s) => (
            <div key={s._id} className="card card-hover p-5">
              <h3 className="text-white font-semibold mb-1">{s.name}</h3>
              <p className="text-gray-500 text-sm mb-3">{s.description}</p>
              <div className="flex items-center justify-between text-xs">
                <span className="text-green-400 font-semibold">{s.winRate}% WR</span>
                <span className="text-amber-400">{s.price ? `$${s.price}/mo` : 'Free'}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Brokers ──────────────────────────────────────────────────
export function Brokers() {
  const [brokers, setBrokers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getBrokers()
      .then((r) => {
        const data = r?.data || r;
        setBrokers(Array.isArray(data) ? data : []);
      })
      .catch(() => setBrokers([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="mb-8">
        <h1 className="section-title">🏦 Brokers</h1>
        <p className="section-subtitle">Trusted broker partners compatible with top tools</p>
      </div>
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card p-5 animate-pulse h-32" />
          ))}
        </div>
      ) : brokers.length === 0 ? (
        <EmptyState title="No brokers listed yet" icon={BuildingLibraryIcon} />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {brokers.map((b) => (
            <div key={b._id} className="card card-hover p-5">
              <h3 className="text-white font-semibold mb-1">{b.name}</h3>
              <p className="text-gray-500 text-sm mb-3">{b.description}</p>
              {b.url && (
                <a
                  href={b.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-amber-400 text-xs hover:underline"
                >
                  Visit Broker →
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Blog ─────────────────────────────────────────────────────
export function Blog() {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getBlogPosts()
      .then((r) => {
        const data = r?.data || r;
        setPosts(Array.isArray(data) ? data : []);
      })
      .catch(() => setPosts([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
      <div className="mb-8">
        <h1 className="section-title">Blog</h1>
        <p className="section-subtitle">Trading insights, guides & news</p>
      </div>
      {loading ? (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="card p-5 animate-pulse h-24" />
          ))}
        </div>
      ) : posts.length === 0 ? (
        <EmptyState title="No posts yet" description="Check back soon for trading guides and news." />
      ) : (
        <div className="space-y-4">
          {posts.map((post) => (
            <Link
              key={post.slug}
              to={`/blog/${post.slug}`}
              className="card card-hover p-5 flex items-start justify-between gap-4 group"
            >
              <div>
                <h2 className="text-white font-semibold group-hover:text-amber-400 transition-colors mb-1">
                  {post.title}
                </h2>
                <p className="text-gray-500 text-sm">{post.excerpt}</p>
                <p className="text-gray-700 text-xs mt-2">{timeAgo(post.createdAt)}</p>
              </div>
              <ChevronRightIcon className="w-5 h-5 text-gray-700 group-hover:text-gray-400 flex-shrink-0 mt-1" />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function BlogPost() {
  const { slug } = useParams();
  const [post, setPost] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getBlogPost(slug)
      .then((r) => setPost(r?.data || r))
      .catch(() => setPost(null))
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-[#1F2937] rounded w-2/3" />
        <div className="h-4 bg-[#1A1A1A] rounded w-1/3" />
        <div className="space-y-2 mt-6">
          {[...Array(10)].map((_, i) => <div key={i} className="h-4 bg-[#1A1A1A] rounded" />)}
        </div>
      </div>
    </div>
  );

  if (!post) return <EmptyState title="Post not found" />;

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
      <Link to="/blog" className="text-gray-500 hover:text-white text-sm flex items-center gap-1 mb-6 transition-colors">
        ← Back to Blog
      </Link>
      <h1 className="text-3xl font-bold text-white mb-3">{post.title}</h1>
      <p className="text-gray-600 text-sm mb-8">{timeAgo(post.createdAt)}</p>
      <div
        className="prose prose-invert prose-sm max-w-none text-gray-300 leading-relaxed"
        dangerSetInnerHTML={{ __html: post.content || post.body || '' }}
      />
    </div>
  );
}

// ─── NotFound ─────────────────────────────────────────────────
export function NotFound() {
  return (
    <div className="max-w-xl mx-auto px-4 py-32 text-center">
      <ExclamationCircleIcon className="w-16 h-16 text-gray-700 mx-auto mb-4" />
      <h1 className="text-4xl font-extrabold text-white mb-3">404</h1>
      <p className="text-gray-500 text-sm mb-6">This page doesn't exist or has been moved.</p>
      <Link to="/" className="btn-primary">Go Home</Link>
    </div>
  );
}










// 'use client'
// import React, { useEffect, useState } from 'react';
// import { Link, useParams } from 'react-router-dom';
// import IndicatorCard from '../components/common/IndicatorCard';
// import { SkeletonCard, EmptyState } from '../components/common/UI';
// import {
//   getByStrategy, getByAsset, getByListingType,
//   getSignals, getBrokers, getBlogPosts, getBlogPost
// } from '../utils/api';
// import { getAssetEmoji, timeAgo, formatNumber } from '../utils/helpers';
// import {
//   ExclamationCircleIcon,
//   ChevronRightIcon,
//   SignalIcon,
//   BuildingLibraryIcon,
// } from '@heroicons/react/24/outline';

// // ─── Strategies ───────────────────────────────────────────────
// const STRATEGY_TYPES = [
//   { slug: 'trend-following', label: 'Trend Following', emoji: '📈' },
//   { slug: 'mean-reversion', label: 'Mean Reversion', emoji: '🔄' },
//   { slug: 'breakout', label: 'Breakout', emoji: '💥' },
//   { slug: 'scalping', label: 'Scalping', emoji: '⚡' },
//   { slug: 'swing', label: 'Swing Trading', emoji: '🌊' },
//   { slug: 'momentum', label: 'Momentum', emoji: '🚀' },
//   { slug: 'arbitrage', label: 'Arbitrage', emoji: '⚖️' },
//   { slug: 'price-action', label: 'Price Action', emoji: '🕯️' },
// ];

// export function Strategies() {
//   return (
//     <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
//       <div className="mb-8">
//         <h1 className="section-title">Trading Strategies</h1>
//         <p className="section-subtitle">Browse tools by strategy type</p>
//       </div>
//       <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
//         {STRATEGY_TYPES.map(({ slug, label, emoji }) => (
//           <Link
//             key={slug}
//             to={`/strategies/${slug}`}
//             className="card card-hover p-5 flex items-center gap-3 group"
//           >
//             <span className="text-2xl">{emoji}</span>
//             <span className="text-white text-sm font-medium group-hover:text-amber-400 transition-colors">
//               {label}
//             </span>
//           </Link>
//         ))}
//       </div>
//     </div>
//   );
// }

// export function StrategyPage() {
//   const { type } = useParams();
//   const [items, setItems] = useState([]);
//   const [loading, setLoading] = useState(true);
//   const strategy = STRATEGY_TYPES.find((s) => s.slug === type);

//   useEffect(() => {
//     getByStrategy(type)
//       .then((r) => setItems(r?.data || r || []))
//       .catch(() => {})
//       .finally(() => setLoading(false));
//   }, [type]);

//   return (
//     <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
//       <div className="mb-8">
//         <h1 className="section-title">
//           {strategy?.emoji} {strategy?.label || type} Tools
//         </h1>
//       </div>
//       {loading ? (
//         <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
//           {[...Array(8)].map((_, i) => <SkeletonCard key={i} />)}
//         </div>
//       ) : items.length === 0 ? (
//         <EmptyState title="No tools found for this strategy" />
//       ) : (
//         <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
//           {items.map((ind) => <IndicatorCard key={ind._id} indicator={ind} />)}
//         </div>
//       )}
//     </div>
//   );
// }

// // ─── Asset Page ───────────────────────────────────────────────
// export function AssetPage() {
//   const { assetClass } = useParams();
//   const [items, setItems] = useState([]);
//   const [loading, setLoading] = useState(true);

//   useEffect(() => {
//     getByAsset(assetClass)
//       .then((r) => setItems(r?.data || r || []))
//       .catch(() => {})
//       .finally(() => setLoading(false));
//   }, [assetClass]);

//   return (
//     <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
//       <div className="mb-8">
//         <h1 className="section-title capitalize">
//           {getAssetEmoji(assetClass)} {assetClass} Tools
//         </h1>
//       </div>
//       {loading ? (
//         <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
//           {[...Array(8)].map((_, i) => <SkeletonCard key={i} />)}
//         </div>
//       ) : items.length === 0 ? (
//         <EmptyState title="No tools found for this asset class" />
//       ) : (
//         <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
//           {items.map((ind) => <IndicatorCard key={ind._id} indicator={ind} />)}
//         </div>
//       )}
//     </div>
//   );
// }

// // ─── Listing Type Page ────────────────────────────────────────
// export function ListingTypePage() {
//   const { listingType } = useParams();
//   const [items, setItems] = useState([]);
//   const [loading, setLoading] = useState(true);

//   useEffect(() => {
//     getByListingType(listingType)
//       .then((r) => setItems(r?.data || r || []))
//       .catch(() => {})
//       .finally(() => setLoading(false));
//   }, [listingType]);

//   const labels = { ea: 'Expert Advisors', bot: 'Trading Bots', signal: 'Signal Services' };

//   return (
//     <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
//       <div className="mb-8">
//         <h1 className="section-title capitalize">
//           {labels[listingType] || `${listingType}s`}
//         </h1>
//       </div>
//       {loading ? (
//         <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
//           {[...Array(8)].map((_, i) => <SkeletonCard key={i} />)}
//         </div>
//       ) : (
//         <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
//           {items.map((ind) => <IndicatorCard key={ind._id} indicator={ind} />)}
//         </div>
//       )}
//     </div>
//   );
// }

// // ─── Signals ──────────────────────────────────────────────────
// export function Signals() {
//   const [signals, setSignals] = useState([]);
//   const [loading, setLoading] = useState(true);

//   useEffect(() => {
//     getSignals()
//       .then((r) => setSignals(r?.data || r || []))
//       .catch(() => {})
//       .finally(() => setLoading(false));
//   }, []);

//   return (
//     <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
//       <div className="mb-8">
//         <h1 className="section-title">📡 Signal Services</h1>
//         <p className="section-subtitle">Live trading signals from verified providers</p>
//       </div>
//       {loading ? (
//         <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
//           {[...Array(6)].map((_, i) => <SkeletonCard key={i} />)}
//         </div>
//       ) : signals.length === 0 ? (
//         <EmptyState title="No signals available" icon={SignalIcon} description="Check back soon for trading signal services." />
//       ) : (
//         <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
//           {signals.map((s) => (
//             <div key={s._id} className="card card-hover p-5">
//               <h3 className="text-white font-semibold mb-1">{s.name}</h3>
//               <p className="text-gray-500 text-sm mb-3">{s.description}</p>
//               <div className="flex items-center justify-between text-xs">
//                 <span className="text-green-400 font-semibold">{s.winRate}% WR</span>
//                 <span className="text-amber-400">{s.price ? `$${s.price}/mo` : 'Free'}</span>
//               </div>
//             </div>
//           ))}
//         </div>
//       )}
//     </div>
//   );
// }

// // ─── Brokers ──────────────────────────────────────────────────
// export function Brokers() {
//   const [brokers, setBrokers] = useState([]);
//   const [loading, setLoading] = useState(true);

//   useEffect(() => {
//     getBrokers()
//       .then((r) => setBrokers(r?.data || r || []))
//       .catch(() => {})
//       .finally(() => setLoading(false));
//   }, []);

//   return (
//     <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
//       <div className="mb-8">
//         <h1 className="section-title">🏦 Brokers</h1>
//         <p className="section-subtitle">Trusted broker partners compatible with top tools</p>
//       </div>
//       {loading ? (
//         <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
//           {[...Array(6)].map((_, i) => (
//             <div key={i} className="card p-5 animate-pulse h-32" />
//           ))}
//         </div>
//       ) : brokers.length === 0 ? (
//         <EmptyState title="No brokers listed yet" icon={BuildingLibraryIcon} />
//       ) : (
//         <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
//           {brokers.map((b) => (
//             <div key={b._id} className="card card-hover p-5">
//               <h3 className="text-white font-semibold mb-1">{b.name}</h3>
//               <p className="text-gray-500 text-sm mb-3">{b.description}</p>
//               {b.url && (
//                 <a
//                   href={b.url}
//                   target="_blank"
//                   rel="noopener noreferrer"
//                   className="text-amber-400 text-xs hover:underline"
//                 >
//                   Visit Broker →
//                 </a>
//               )}
//             </div>
//           ))}
//         </div>
//       )}
//     </div>
//   );
// }

// // ─── Blog ─────────────────────────────────────────────────────
// export function Blog() {
//   const [posts, setPosts] = useState([]);
//   const [loading, setLoading] = useState(true);

//   useEffect(() => {
//     getBlogPosts()
//       .then((r) => setPosts(r?.data || r || []))
//       .catch(() => {})
//       .finally(() => setLoading(false));
//   }, []);

//   return (
//     <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
//       <div className="mb-8">
//         <h1 className="section-title">Blog</h1>
//         <p className="section-subtitle">Trading insights, guides & news</p>
//       </div>
//       {loading ? (
//         <div className="space-y-4">
//           {[...Array(5)].map((_, i) => (
//             <div key={i} className="card p-5 animate-pulse h-24" />
//           ))}
//         </div>
//       ) : posts.length === 0 ? (
//         <EmptyState title="No posts yet" description="Check back soon for trading guides and news." />
//       ) : (
//         <div className="space-y-4">
//           {posts.map((post) => (
//             <Link
//               key={post.slug}
//               to={`/blog/${post.slug}`}
//               className="card card-hover p-5 flex items-start justify-between gap-4 group"
//             >
//               <div>
//                 <h2 className="text-white font-semibold group-hover:text-amber-400 transition-colors mb-1">
//                   {post.title}
//                 </h2>
//                 <p className="text-gray-500 text-sm">{post.excerpt}</p>
//                 <p className="text-gray-700 text-xs mt-2">{timeAgo(post.createdAt)}</p>
//               </div>
//               <ChevronRightIcon className="w-5 h-5 text-gray-700 group-hover:text-gray-400 flex-shrink-0 mt-1" />
//             </Link>
//           ))}
//         </div>
//       )}
//     </div>
//   );
// }

// export function BlogPost() {
//   const { slug } = useParams();
//   const [post, setPost] = useState(null);
//   const [loading, setLoading] = useState(true);

//   useEffect(() => {
//     getBlogPost(slug)
//       .then((r) => setPost(r?.data || r))
//       .catch(() => {})
//       .finally(() => setLoading(false));
//   }, [slug]);

//   if (loading) return (
//     <div className="max-w-3xl mx-auto px-4 py-10">
//       <div className="animate-pulse space-y-4">
//         <div className="h-8 bg-[#1F2937] rounded w-2/3" />
//         <div className="h-4 bg-[#1A1A1A] rounded w-1/3" />
//         <div className="space-y-2 mt-6">
//           {[...Array(10)].map((_, i) => <div key={i} className="h-4 bg-[#1A1A1A] rounded" />)}
//         </div>
//       </div>
//     </div>
//   );

//   if (!post) return <EmptyState title="Post not found" />;

//   return (
//     <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
//       <Link to="/blog" className="text-gray-500 hover:text-white text-sm flex items-center gap-1 mb-6 transition-colors">
//         ← Back to Blog
//       </Link>
//       <h1 className="text-3xl font-bold text-white mb-3">{post.title}</h1>
//       <p className="text-gray-600 text-sm mb-8">{timeAgo(post.createdAt)}</p>
//       <div
//         className="prose prose-invert prose-sm max-w-none text-gray-300 leading-relaxed"
//         dangerouslySetInnerHTML={{ __html: post.content || post.body || '' }}
//       />
//     </div>
//   );
// }

// // ─── NotFound ─────────────────────────────────────────────────
// export function NotFound() {
//   return (
//     <div className="max-w-xl mx-auto px-4 py-32 text-center">
//       <ExclamationCircleIcon className="w-16 h-16 text-gray-700 mx-auto mb-4" />
//       <h1 className="text-4xl font-extrabold text-white mb-3">404</h1>
//       <p className="text-gray-500 text-sm mb-6">This page doesn't exist or has been moved.</p>
//       <Link to="/" className="btn-primary">Go Home</Link>
//     </div>
//   );
// }
