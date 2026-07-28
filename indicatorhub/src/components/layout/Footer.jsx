import React from 'react';
import { Link } from 'react-router-dom';
import { ChartBarIcon } from '@heroicons/react/24/outline';

const footerLinks = {
  Discover: [
    { label: 'Browse All', to: '/indicators' },
    { label: 'Trending', to: '/trending' },
    { label: 'New Arrivals', to: '/new' },
    { label: 'Top Rated', to: '/top-rated' },
    { label: 'Free Tools', to: '/free' },
  ],
  Tools: [
    { label: 'AI Finder', to: '/ai-finder' },
    { label: 'Compare', to: '/compare' },
    { label: 'Signals', to: '/signals' },
    { label: 'Brokers', to: '/brokers' },
  ],
  Categories: [
    { label: 'Strategies', to: '/strategies' },
    { label: 'Platforms', to: '/platforms' },
    { label: 'Categories', to: '/categories' },
    { label: 'Submit Listing', to: '/submit' },
  ],
  Resources: [
    { label: 'Blog', to: '/blog' },
  ],
};

export default function Footer() {
  return (
    <footer className="border-t border-[#1F2937] bg-[#0A0A0A] mt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-8">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <Link to="/" className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-amber-500 flex items-center justify-center">
                <ChartBarIcon className="w-5 h-5 text-black" />
              </div>
              <span className="text-white font-bold text-lg">
                Indicator<span className="text-amber-400">Hub</span>
              </span>
            </Link>
            <p className="text-gray-500 text-sm leading-relaxed">
              The #1 directory for trading indicators, EAs, bots & signals.
            </p>
          </div>

          {/* Links */}
          {Object.entries(footerLinks).map(([section, links]) => (
            <div key={section}>
              <h4 className="text-white font-semibold text-sm mb-3">{section}</h4>
              <ul className="space-y-2">
                {links.map(({ label, to }) => (
                  <li key={to}>
                    <Link
                      to={to}
                      className="text-gray-500 hover:text-gray-300 text-sm transition-colors"
                    >
                      {label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="border-t border-[#1F2937] mt-10 pt-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-gray-600 text-xs">
            © {new Date().getFullYear()} IndicatorHub. All rights reserved.
          </p>
          <p className="text-gray-700 text-xs">
            Trading involves risk. Past performance is not indicative of future results.
          </p>
        </div>
      </div>
    </footer>
  );
}
