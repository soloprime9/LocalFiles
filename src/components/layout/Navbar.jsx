import React, { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { useApp } from '../../context/AppContext';
import { 
  TrendingUp, 
  Search, 
  BarChart4, 
  Calendar, 
  ShieldAlert, 
  Activity, 
  Calculator, 
  PlusCircle, 
  Menu, 
  X, 
  Layers, 
  ArrowLeftRight,
  Globe,
  Cpu,
  User
} from 'lucide-react';

export const Navbar = () => {
  const { compareList } = useApp();
  const { isAuthenticated, user } = useSelector((state) => state.auth);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [searchVal, setSearchVal] = useState('');
  const navigate = useNavigate();

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (searchVal.trim()) {
      navigate(`/indicators?search=${encodeURIComponent(searchVal.trim())}`);
      setShowSearch(false);
    }
  };

  return (
    <nav className="glass-panel sticky top-0 z-50 border-b border-white/5 bg-[#07070b]/90 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link to="/" className="flex items-center space-x-2 flex-shrink-0 group">
              <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-amber-500 to-amber-300 flex items-center justify-center shadow-lg shadow-amber-500/20 group-hover:scale-105 transition-transform duration-200">
                <BarChart4 className="h-5 w-5 text-black" />
              </div>
              <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-100 to-amber-400 bg-clip-text text-transparent">
                Falcon<span className="text-amber-500">Spido</span>
              </span>
            </Link>
          </div>

          {/* Desktop Navigation Links */}
          <div className="hidden lg:flex items-center space-x-4 xl:space-x-5 text-sm font-medium">
            <NavLink 
              to="/indicators" 
              className={({ isActive }) => `flex items-center space-x-1 transition-colors ${isActive ? 'text-amber-400' : 'text-slate-300 hover:text-white'}`}
            >
              <Layers className="h-4 w-4 text-amber-500/80" />
              <span>Browse Tools</span>
            </NavLink>

            <NavLink 
              to="/screener" 
              className={({ isActive }) => `flex items-center space-x-1 transition-colors ${isActive ? 'text-amber-400' : 'text-slate-300 hover:text-white'}`}
            >
              <Activity className="h-4 w-4 text-emerald-400" />
              <span>Screener</span>
            </NavLink>

            <NavLink 
              to="/strategy" 
              className={({ isActive }) => `flex items-center space-x-1 transition-colors ${isActive ? 'text-amber-400' : 'text-slate-300 hover:text-white'}`}
            >
              <Cpu className="h-4 w-4 text-cyan-400" />
              <span>Strategies</span>
            </NavLink>

            <NavLink 
              to="/markets" 
              className={({ isActive }) => `flex items-center space-x-1 transition-colors ${isActive ? 'text-amber-400' : 'text-slate-300 hover:text-white'}`}
            >
              <Globe className="h-4 w-4 text-indigo-400" />
              <span>Markets</span>
            </NavLink>

            <NavLink 
              to="/news" 
              className={({ isActive }) => `flex items-center space-x-1 transition-colors ${isActive ? 'text-amber-400' : 'text-slate-300 hover:text-white'}`}
            >
              <ShieldAlert className="h-4 w-4 text-rose-400" />
              <span>News</span>
            </NavLink>

            <NavLink 
              to="/macro-calendar" 
              className={({ isActive }) => `flex items-center space-x-1 transition-colors ${isActive ? 'text-amber-400' : 'text-slate-300 hover:text-white'}`}
            >
              <Calendar className="h-4 w-4 text-amber-500" />
              <span>Macro</span>
            </NavLink>

            <NavLink 
              to="/calculators" 
              className={({ isActive }) => `flex items-center space-x-1 transition-colors ${isActive ? 'text-amber-400' : 'text-slate-300 hover:text-white'}`}
            >
              <Calculator className="h-4 w-4 text-teal-400" />
              <span>Risk</span>
            </NavLink>

            <NavLink 
              to="/brokers" 
              className={({ isActive }) => `flex items-center space-x-1 transition-colors ${isActive ? 'text-amber-400' : 'text-slate-300 hover:text-white'}`}
            >
              <TrendingUp className="h-4 w-4 text-yellow-400" />
              <span>Brokers</span>
            </NavLink>
          </div>

          {/* Desktop Right Sidebars */}
          <div className="hidden lg:flex items-center space-x-4">
            {/* Nav Search Box */}
            <form onSubmit={handleSearchSubmit} className="relative max-w-xs">
              <input
                type="text"
                placeholder="Search indicators, EAs, keys..."
                value={searchVal}
                onChange={(e) => setSearchVal(e.target.value)}
                className="w-48 xl:w-64 bg-[#11111a] border border-white/5 rounded-lg py-1.5 pl-9 pr-3 text-xs text-slate-300 placeholder-slate-500 focus:outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 transition-all"
              />
              <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
            </form>

            {/* Compare items */}
            <Link 
              to="/compare" 
              className="flex items-center space-x-1.5 bg-[#141421] border border-white/10 hover:border-amber-500/30 text-xs px-2.5 py-1.5 rounded-lg text-slate-300 hover:text-white transition-all relative"
            >
              <ArrowLeftRight className="h-3.5 w-3.5 text-amber-400" />
              <span>Compare</span>
              {compareList.length > 0 && (
                <span className="absolute -top-1.5 -right-1.5 h-4 w-4 rounded-full bg-amber-500 text-[10px] font-bold text-black flex items-center justify-center">
                  {compareList.length}
                </span>
              )}
            </Link>

            <Link 
              to="/submit" 
              className="flex items-center space-x-1 bg-[#141421] border border-white/10 hover:border-amber-500/25 text-slate-300 hover:text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150"
            >
              <PlusCircle className="h-3.5 w-3.5 text-amber-400" />
              <span>Submit Listing</span>
            </Link>

            {isAuthenticated ? (
              <Link
                to="/profile"
                className="flex items-center space-x-1 bg-amber-500 hover:bg-amber-400 text-black px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-md shadow-amber-500/10 transition-all duration-150 animate-fade-in"
              >
                <User className="h-3.5 w-3.5" />
                <span>{user?.name || 'Profile'}</span>
              </Link>
            ) : (
              <Link
                to="/login"
                className="flex items-center space-x-1 bg-amber-500 hover:bg-amber-400 text-black px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-md shadow-amber-500/10 transition-all duration-150"
              >
                <User className="h-3.5 w-3.5" />
                <span>Sign In</span>
              </Link>
            )}
          </div>

          {/* Mobile buttons */}
          <div className="flex items-center lg:hidden space-x-2">
            <button 
              onClick={() => setShowSearch(!showSearch)}
              className="p-2 text-slate-400 hover:text-white focus:outline-none"
            >
              <Search className="h-5 w-5" />
            </button>

            {compareList.length > 0 && (
              <Link to="/compare" className="p-2 text-amber-500 hover:text-amber-400 relative">
                <ArrowLeftRight className="h-5 w-5" />
                <span className="absolute top-1 right-1 h-4.5 w-4.5 rounded-full bg-amber-500 text-[9px] font-bold text-black flex items-center justify-center">
                  {compareList.length}
                </span>
              </Link>
            )}

            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 text-slate-400 hover:text-white focus:outline-none"
            >
              {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Expanded Search for mobile */}
      {showSearch && (
        <div className="lg:hidden bg-[#0d0d15] border-b border-white/10 p-3">
          <form onSubmit={handleSearchSubmit} className="relative">
            <input
              type="text"
              placeholder="Search strategy scripts, indicators..."
              value={searchVal}
              onChange={(e) => setSearchVal(e.target.value)}
              className="w-full bg-[#11111a] border border-white/10 rounded-lg py-2 pl-10 pr-4 text-sm text-slate-300 placeholder-slate-500 focus:outline-none focus:border-amber-500"
              autoFocus
            />
            <Search className="absolute left-3.5 top-3 h-4 w-4 text-slate-500" />
          </form>
        </div>
      )}

      {/* Mobile nav drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden bg-[#0a0a0f] border-b border-white/10 px-4 py-4 space-y-3 font-medium text-sm">
          <Link 
            to="/indicators" 
            onClick={() => setMobileMenuOpen(false)}
            className="block text-slate-300 hover:text-white py-2 border-b border-white/5"
          >
            Browse Indicators
          </Link>
          <Link 
            to="/screener" 
            onClick={() => setMobileMenuOpen(false)}
            className="block text-slate-300 hover:text-white py-2 border-b border-white/5"
          >
            Interactive Screener
          </Link>
          <Link 
            to="/strategy" 
            onClick={() => setMobileMenuOpen(false)}
            className="block text-slate-300 hover:text-white py-2 border-b border-white/5"
          >
            Quantum Strategies
          </Link>
          <Link 
            to="/markets" 
            onClick={() => setMobileMenuOpen(false)}
            className="block text-slate-300 hover:text-white py-2 border-b border-white/5"
          >
            Real-Time Markets
          </Link>
          <Link 
            to="/news" 
            onClick={() => setMobileMenuOpen(false)}
            className="block text-slate-300 hover:text-white py-2 border-b border-white/5"
          >
            Global Market News
          </Link>
          <Link 
            to="/macro-calendar" 
            onClick={() => setMobileMenuOpen(false)}
            className="block text-slate-300 hover:text-white py-2 border-b border-white/5"
          >
            Macroeconomic Calendar
          </Link>
          <Link 
            to="/calculators" 
            onClick={() => setMobileMenuOpen(false)}
            className="block text-slate-300 hover:text-white py-2 border-b border-white/5"
          >
            Risk Calculators
          </Link>
          <Link 
            to="/brokers" 
            onClick={() => setMobileMenuOpen(false)}
            className="block text-slate-300 hover:text-white py-2 border-b border-white/5"
          >
            Regulated Broker Partners
          </Link>

          <Link 
            to="/submit" 
            onClick={() => setMobileMenuOpen(false)}
            className="flex items-center justify-center space-x-2 bg-[#141421] border border-white/10 hover:border-amber-500/25 text-slate-300 py-2.5 rounded-lg font-semibold transition-all mb-2"
          >
            <PlusCircle className="h-4 w-4 text-amber-400" />
            <span>Submit a Listing</span>
          </Link>

          {isAuthenticated ? (
            <Link 
              to="/profile" 
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center justify-center space-x-2 bg-amber-500 hover:bg-amber-400 text-black py-2.5 rounded-lg font-semibold shadow-md shadow-amber-500/10 transition-all font-sans"
            >
              <User className="h-4 w-4" />
              <span>{user?.name || 'My Profile'}</span>
            </Link>
          ) : (
            <Link 
              to="/login" 
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center justify-center space-x-2 bg-amber-500 hover:bg-amber-400 text-black py-2.5 rounded-lg font-semibold shadow-md shadow-amber-500/10 transition-all font-sans"
            >
              <User className="h-4 w-4" />
              <span>Operator Sign In</span>
            </Link>
          )}
        </div>
      )}
    </nav>
  );
};
