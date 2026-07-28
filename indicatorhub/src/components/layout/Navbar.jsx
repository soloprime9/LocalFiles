import React, { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import {
  MagnifyingGlassIcon,
  Bars3Icon,
  XMarkIcon,
  ChartBarIcon,
  FireIcon,
  SparklesIcon,
  StarIcon,
  GiftIcon,
  ScaleIcon,
  CpuChipIcon,
  PlusCircleIcon,
} from '@heroicons/react/24/outline';
import { useApp, ACTIONS } from '../../context/AppContext';
import clsx from 'clsx';

const navLinks = [
  { to: '/indicators', label: 'Browse', icon: ChartBarIcon },
  { to: '/trending', label: 'Trending', icon: FireIcon },
  { to: '/new', label: 'New', icon: SparklesIcon },
  { to: '/top-rated', label: 'Top Rated', icon: StarIcon },
  { to: '/free', label: 'Free', icon: GiftIcon },
  { to: '/compare', label: 'Compare', icon: ScaleIcon },
  { to: '/ai-finder', label: 'AI Finder', icon: CpuChipIcon },
];

export default function Navbar() {
  const { state, dispatch } = useApp();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchVal, setSearchVal] = useState('');
  const navigate = useNavigate();

  const handleSearch = (e) => {
    e.preventDefault();
    if (!searchVal.trim()) return;
    dispatch({ type: ACTIONS.SET_FILTER, payload: { search: searchVal.trim() } });
    navigate('/indicators');
    setMobileOpen(false);
  };

  const compareCount = state.compareList.length;

  return (
    <nav className="sticky top-0 z-50 bg-[#0A0A0A]/95 backdrop-blur border-b border-[#1F2937]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 flex-shrink-0">
            <div className="w-8 h-8 rounded-lg bg-amber-500 flex items-center justify-center">
              <ChartBarIcon className="w-5 h-5 text-black" />
            </div>
            <span className="text-white font-bold text-lg tracking-tight">
              Indicator<span className="text-amber-400">Hub</span>
            </span>
          </Link>

          {/* Desktop Nav */}
          <div className="hidden lg:flex items-center gap-1">
            {navLinks.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  clsx(
                    'px-3 py-2 rounded-md text-sm font-medium transition-colors duration-150',
                    isActive
                      ? 'text-amber-400 bg-amber-400/10'
                      : 'text-gray-400 hover:text-white hover:bg-white/5'
                  )
                }
              >
                {label}
                {label === 'Compare' && compareCount > 0 && (
                  <span className="ml-1.5 bg-amber-500 text-black text-xs rounded-full w-4 h-4 inline-flex items-center justify-center font-bold">
                    {compareCount}
                  </span>
                )}
              </NavLink>
            ))}
          </div>

          {/* Search + Submit */}
          <div className="hidden md:flex items-center gap-3">
            <form onSubmit={handleSearch} className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                value={searchVal}
                onChange={(e) => setSearchVal(e.target.value)}
                placeholder="Search indicators..."
                className="input-field pl-9 w-52 h-9"
              />
            </form>
            <Link to="/submit" className="btn-primary text-xs px-3 py-2">
              <PlusCircleIcon className="w-4 h-4" />
              Submit
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <button
            className="lg:hidden text-gray-400 hover:text-white"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? (
              <XMarkIcon className="w-6 h-6" />
            ) : (
              <Bars3Icon className="w-6 h-6" />
            )}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div className="lg:hidden border-t border-[#1F2937] bg-[#111111]">
          <div className="px-4 py-3">
            <form onSubmit={handleSearch} className="relative mb-3">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                value={searchVal}
                onChange={(e) => setSearchVal(e.target.value)}
                placeholder="Search indicators..."
                className="input-field pl-9 w-full h-10"
              />
            </form>
            <div className="space-y-1">
              {navLinks.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  onClick={() => setMobileOpen(false)}
                  className={({ isActive }) =>
                    clsx(
                      'flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors',
                      isActive
                        ? 'text-amber-400 bg-amber-400/10'
                        : 'text-gray-400 hover:text-white hover:bg-white/5'
                    )
                  }
                >
                  <Icon className="w-4 h-4" />
                  {label}
                  {label === 'Compare' && compareCount > 0 && (
                    <span className="ml-auto bg-amber-500 text-black text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold">
                      {compareCount}
                    </span>
                  )}
                </NavLink>
              ))}
              <Link
                to="/submit"
                onClick={() => setMobileOpen(false)}
                className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-semibold text-amber-400 hover:bg-amber-400/10 transition-colors"
              >
                <PlusCircleIcon className="w-4 h-4" />
                Submit a Listing
              </Link>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
