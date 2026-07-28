import { Link } from 'react-router-dom';
import { BarChart3 } from 'lucide-react';

const COLUMNS = [
  {
    title: 'Discover',
    links: [
      { label: 'Trending', to: '/trending' },
      { label: 'New', to: '/new' },
      { label: 'Top Rated', to: '/top-rated' },
      { label: 'Free Tools', to: '/free' },
      { label: 'AI Finder', to: '/ai-finder' },
    ],
  },
  {
    title: 'Categories',
    links: [
      { label: 'Indicators', to: '/listing-type/indicator' },
      { label: 'EAs', to: '/listing-type/ea' },
      { label: 'Bots', to: '/listing-type/bot' },
      { label: 'Signals', to: '/signals' },
      { label: 'Strategies', to: '/strategies' },
      { label: 'Screeners', to: '/listing-type/screener' },
    ],
  },
  {
    title: 'Platforms',
    links: [
      { label: 'TradingView', to: '/platforms/tradingview' },
      { label: 'MetaTrader 4', to: '/platforms/mt4' },
      { label: 'MetaTrader 5', to: '/platforms/mt5' },
      { label: 'cTrader', to: '/platforms/ctrader' },
      { label: 'NinjaTrader', to: '/platforms/ninjatrader' },
    ],
  },
  {
    title: 'Resources',
    links: [
      { label: 'Submit Indicator', to: '/submit' },
      { label: 'Blog', to: '/blog' },
      { label: 'Compare', to: '/compare' },
      { label: 'Brokers', to: '/brokers' },
    ],
  },
];

const SOCIALS = [
  { label: 'Twitter / X', href: 'https://twitter.com' },
  { label: 'Telegram', href: 'https://telegram.org' },
  { label: 'Discord', href: 'https://discord.com' },
];

export default function Footer() {
  return (
    <footer className="bg-[#0A0A0A] border-t border-[#1F2937] mt-auto">
      <div className="max-w-7xl mx-auto px-4 py-12">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-8">
          <div className="col-span-2 sm:col-span-3 lg:col-span-1">
            <Link to="/" className="flex items-center gap-2 mb-3">
              <BarChart3 className="w-6 h-6 text-amber-500" />
              <span className="text-white font-bold text-lg">IndicatorHub</span>
            </Link>
            <p className="text-sm text-gray-500 leading-relaxed max-w-xs">
              The world's most trusted trading tool directory.
            </p>
          </div>

          {COLUMNS.map((col) => (
            <div key={col.title}>
              <h4 className="text-white text-sm font-semibold mb-3">{col.title}</h4>
              <ul className="space-y-2">
                {col.links.map((link) => (
                  <li key={link.label}>
                    <Link to={link.to} className="text-sm text-gray-500 hover:text-amber-400 transition-colors">
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="border-t border-[#1F2937] mt-10 pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-center sm:text-left">
            <p className="text-sm text-gray-500">© 2026 IndicatorHub</p>
            <p className="text-xs text-gray-600 mt-1 max-w-md">
              Not financial advice. Past results don't guarantee future performance. Always trade responsibly.
            </p>
          </div>

          <div className="flex items-center gap-4">
            {SOCIALS.map((s) => (
              <a
                key={s.label}
                href={s.href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-gray-500 hover:text-amber-400 transition-colors"
              >
                {s.label}
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
