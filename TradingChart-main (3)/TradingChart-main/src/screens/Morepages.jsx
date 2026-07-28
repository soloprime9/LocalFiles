'use client' 
import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  AcademicCapIcon,
  MapIcon,
  CheckBadgeIcon,
  DocumentChartBarIcon,
  StarIcon,
  ShieldExclamationIcon,
} from '@heroicons/react/24/outline';

function useSeo(title, description) {
  useEffect(() => {
    document.title = title;
    let meta = document.querySelector('meta[name="description"]');
    if (!meta) {
      meta = document.createElement('meta');
      meta.setAttribute('name', 'description');
      document.head.appendChild(meta);
    }
    meta.setAttribute('content', description);
  }, [title, description]);
}

function PageShell({ icon: Icon, title, updated, children }) {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
      <div className="flex items-center gap-3 mb-2">
        <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center shrink-0">
          <Icon className="w-5 h-5 text-amber-400" />
        </div>
        <h1 className="text-2xl font-bold text-white">{title}</h1>
      </div>
      {updated && <p className="text-gray-600 text-xs mb-8">Last updated: {updated}</p>}
      <div className="prose prose-invert prose-sm sm:prose-base max-w-none text-gray-300 space-y-5 [&_h2]:text-white [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:mt-8 [&_h2]:mb-2 [&_a]:text-amber-400 [&_a]:no-underline hover:[&_a]:underline">
        {children}
      </div>
    </div>
  );
}

export function EditorialPolicy() {
  useSeo(
    'Editorial Policy & TrustScore Methodology — FalconSpido',
    'How FalconSpido evaluates trading indicators, EAs, bots and signals: TrustScore methodology, backtest audit process, review moderation, and AI-assisted content disclosure.'
  );
  return (
    <PageShell icon={AcademicCapIcon} title="Editorial Policy & How We Review" updated="June 2026">
      <p>
        This page explains exactly how FalconSpido evaluates listings, so you can judge for yourself
        how much weight to give our TrustScore, ratings, and labels — rather than taking them on
        faith.
      </p>

      <h2>TrustScore Methodology</h2>
      <p>
        TrustScore is calculated from five inputs: average user rating, creator verification status,
        backtest audit outcome, total review count, and any open scam flags. No single input can push
        a listing's score above what an unresolved scam flag or an unaudited backtest claim caps it
        at — a high rating alone cannot offset those.
      </p>

      <h2 className="flex items-center gap-2">
        <DocumentChartBarIcon className="w-4 h-4 text-blue-400 inline" /> Backtest Audit Statuses
      </h2>
      <p>Every listing's performance claim is labeled one of three ways:</p>
      <p>
        <strong className="text-emerald-400">Verified</strong> — the creator provided backtest
        evidence (trade logs, broker statements, or platform-exported reports) that our review
        process checked for basic red flags like obvious curve-fitting or missing out-of-sample data.
      </p>
      <p>
        <strong className="text-amber-400">Suspicious</strong> — evidence was provided but showed
        signs of curve-fitting, look-ahead bias, or inconsistency with the listing's stated rules.
      </p>
      <p>
        <strong className="text-gray-400">Unaudited</strong> — no backtest evidence was provided, or
        it hasn't been reviewed yet. We do not treat the absence of a red flag as proof of
        performance.
      </p>
      <p>
        A "Verified" label means evidence was reviewed — it is not an independent guarantee of future
        results. See our <Link to="/disclaimer">Disclaimer</Link> for the full trading-risk notice.
      </p>

      <h2 className="flex items-center gap-2">
        <StarIcon className="w-4 h-4 text-amber-400 inline" /> Reviews
      </h2>
      <p>
        Reviews are submitted by site visitors and are not independently verified against purchase
        records unless explicitly labeled "Verified Purchase." We moderate for spam, off-topic
        content, and personal attacks, but we do not remove negative reviews simply because a
        listing's creator disputes them.
      </p>

      <h2 className="flex items-center gap-2">
        <ShieldExclamationIcon className="w-4 h-4 text-red-400 inline" /> Scam Flags
      </h2>
      <p>
        Any user can flag a listing as a suspected scam with a written reason. Flags are reviewed
        manually; we do not auto-delist on a single flag, but repeated or well-substantiated flags
        affect TrustScore and may result in removal.
      </p>

      <h2 className="flex items-center gap-2">
        <CheckBadgeIcon className="w-4 h-4 text-blue-400 inline" /> AI-Assisted Content
      </h2>
      <p>
        Some listing descriptions and pros/cons summaries are drafted with AI assistance from
        structured data the creator or our team supplied (platforms, pricing, audit status, review
        counts). AI is not permitted to invent performance numbers, win rates, or claims that aren't
        traceable to a structured field. Listings using AI-assisted summaries are labeled as such.
        All AI-assisted copy is reviewed by a person before publishing.
      </p>

      <h2>Affiliate Relationships &amp; Editorial Independence</h2>
      <p>
        FalconSpido earns commissions through some affiliate links (see our{' '}
        <Link to="/disclaimer">Disclaimer</Link>). Affiliate status has no input into the TrustScore
        formula above and does not influence search ranking, sort order, or review moderation
        decisions.
      </p>

      <h2>Corrections</h2>
      <p>
        Spotted an error in a listing or audit label? Email{' '}
        <a href="mailto:trust@falconspido.com">trust@falconspido.com</a> with the listing URL and
        we'll review it.
      </p>
    </PageShell>
  );
}

const SITEMAP_SECTIONS = [
  {
    title: 'Discover',
    links: [
      { label: 'Home', to: '/' },
      { label: 'Browse All Tools', to: '/indicators' },
      { label: 'Trending', to: '/trending' },
      { label: 'New Arrivals', to: '/new' },
      { label: 'Top Rated', to: '/top-rated' },
      { label: 'Free Tools', to: '/free' },
      { label: 'AI Finder', to: '/ai-finder' },
      { label: 'Compare Tools', to: '/compare' },
    ],
  },
  {
    title: 'Browse By',
    links: [
      { label: 'Categories', to: '/categories' },
      { label: 'Platforms', to: '/platforms' },
      { label: 'Strategies', to: '/strategies' },
      { label: 'Signals', to: '/signals' },
      { label: 'Brokers', to: '/brokers' },
    ],
  },
  {
    title: 'Resources',
    links: [
      { label: 'Blog', to: '/blog' },
      { label: 'Submit a Listing', to: '/submit' },
    ],
  },
  {
    title: 'Company',
    links: [
      { label: 'About Us', to: '/about' },
      { label: 'Contact', to: '/contact' },
      { label: 'Editorial Policy', to: '/editorial-policy' },
    ],
  },
  {
    title: 'Legal',
    links: [
      { label: 'Terms of Service', to: '/terms' },
      { label: 'Privacy Policy', to: '/privacy-policy' },
      { label: 'Affiliate Disclaimer', to: '/disclaimer' },
    ],
  },
];

export function HtmlSitemap() {
  useSeo(
    'Sitemap — FalconSpido',
    'A full directory of every page on FalconSpido, including tool categories, platforms, strategies, and company pages.'
  );
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-12">
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center shrink-0">
          <MapIcon className="w-5 h-5 text-amber-400" />
        </div>
        <h1 className="text-2xl font-bold text-white">Sitemap</h1>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
        {SITEMAP_SECTIONS.map((section) => (
          <div key={section.title}>
            <h2 className="text-white font-semibold text-sm mb-3">{section.title}</h2>
            <ul className="space-y-2">
              {section.links.map((link) => (
                <li key={link.to}>
                  <Link to={link.to} className="text-gray-400 hover:text-amber-400 text-sm transition-colors">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
