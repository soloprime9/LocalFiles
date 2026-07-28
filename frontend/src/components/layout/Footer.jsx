import React from 'react';
import { Link } from 'react-router-dom';
import { BarChart4, Mail, Shield, AlertTriangle, ExternalLink } from 'lucide-react';

export const Footer = () => {
  return (
    <footer className="bg-[#050508] border-t border-white/5 pt-16 pb-8 text-xs text-slate-400">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-10">
          
          {/* Brand/Legal */}
          <div className="lg:col-span-2 space-y-4">
            <Link to="/" className="flex items-center space-x-2 group">
              <div className="h-8 w-8 rounded-lg bg-amber-500 flex items-center justify-center">
                <BarChart4 className="h-4.5 w-4.5 text-black" />
              </div>
              <span className="text-lg font-bold tracking-tight text-white">
                Falcon<span className="text-amber-500">Spido</span>
              </span>
            </Link>
            <p className="text-[#94a3b8] leading-relaxed max-w-sm">
              The premium, cross-platform technical directory, automated review aggregator, and mathematical strategy hub for modern retail quants and traders. Discover elite indicators, expert advisors (EAs), signals, and scripts.
            </p>
            <div className="flex items-center space-x-2 text-slate-500 mt-2">
              <Mail className="h-4 w-4 text-amber-500" />
              <span>support@falconspido.com</span>
            </div>
          </div>

          {/* Directory Links */}
          <div>
            <h3 className="text-white font-semibold text-sm mb-4">Discover Modules</h3>
            <ul className="space-y-2.5">
              <li>
                <Link to="/indicators" className="hover:text-amber-400 hover:underline transition-all">
                  Browse Indicators & EAs
                </Link>
              </li>
              <li>
                <Link to="/screener" className="hover:text-amber-400 hover:underline transition-all">
                  Technical Scanner
                </Link>
              </li>
              <li>
                <Link to="/news" className="hover:text-amber-400 hover:underline transition-all">
                  Macro Sentiment Feed
                </Link>
              </li>
              <li>
                <Link to="/macro-calendar" className="hover:text-amber-400 hover:underline transition-all">
                  Volatility Releases
                </Link>
              </li>
              <li>
                <Link to="/calculators" className="hover:text-amber-400 hover:underline transition-all">
                  Risk Size Optimizers
                </Link>
              </li>
            </ul>
          </div>

          {/* High-value categories */}
          <div>
            <h3 className="text-white font-semibold text-sm mb-4">Listing Types</h3>
            <ul className="space-y-2.5">
              <li><Link to="/indicators?type=Indicator" className="hover:text-amber-400 transition-all">Technical Indicators</Link></li>
              <li><Link to="/indicators?type=EA" className="hover:text-amber-400 transition-all">Expert Advisors (EAs)</Link></li>
              <li><Link to="/indicators?type=Bot" className="hover:text-amber-400 transition-all">Automated Bots</Link></li>
              <li><Link to="/indicators?type=Signal" className="hover:text-amber-400 transition-all">Verified Copy Signals</Link></li>
              <li><Link to="/indicators?type=Screener" className="hover:text-amber-400 transition-all">Market Screeners</Link></li>
            </ul>
          </div>

          {/* Regulatory Partners */}
          <div>
            <h3 className="text-white font-semibold text-sm mb-4">Resources</h3>
            <ul className="space-y-2.5">
              <li><Link to="/brokers" className="hover:text-amber-400 transition-all">Regulated Brokers</Link></li>
              <li><Link to="/compare" className="hover:text-amber-400 transition-all">Comparison Sandbox</Link></li>
              <li><Link to="/submit" className="hover:text-amber-400 transition-all">List Your Tool</Link></li>
              <li>
                <a 
                  href="https://tradingview.com" 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="flex items-center space-x-1 hover:text-amber-400 transition-all"
                >
                  <span>TradingView Plat</span>
                  <ExternalLink className="h-3 w-3" />
                </a>
              </li>
            </ul>
          </div>

        </div>

        {/* High-Risk Financial Disclaimer - Vital for Google SEO Quality Raters (YMYL - Your Money Your Life guidelines) */}
        <div className="mt-12 pt-8 border-t border-white/5 space-y-4">
          <div className="bg-[#101017] p-4 rounded-lg border border-red-500/10 flex items-start space-x-3">
            <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="text-slate-200 font-semibold text-xs flex items-center space-x-1">
                <span>HIGH CONTRACVOLATILITY FINANCIAL LEVERAGE DISCLAIMER</span>
              </span>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Trading foreign exchange (Forex), indices, cryptocurrencies, stocks, derivatives, contract contracts, option variables, futures, and commodities on leverage involves extreme hazard levels and is not suitable for all users. System performance records shown via audits correspond to simulated backtest guidelines. Past results are in absolute terms no dynamic indicators of future profitability. falconspido.com does not operate as a financial advisory bureau. All shared settings, presets, review ratings, or indicator setups exist under academic and quantitative study guidance. By accessing this network, you agree fully to our Terms of Mitigation and standard execution disclaimers. Code parameters audited on falconspido.com are compiled purely for community exploration metrics.
              </p>
            </div>
          </div>

          <div className="flex flex-col md:flex-row items-center justify-between text-[11px] text-slate-500 gap-4">
            <div className="flex items-center space-x-1">
              <Shield className="h-3.5 w-3.5 text-amber-500" />
              <span>© 2026 falconspido.com. All technical indices registered with copyright protection.</span>
            </div>
            <div className="flex space-x-3 sm:space-x-4">
              <Link to="/about" className="hover:text-slate-300">About Us</Link>
              <span>•</span>
              <Link to="/terms" className="hover:text-slate-300">Terms of Use</Link>
              <span>•</span>
              <Link to="/privacy" className="hover:text-slate-300">Privacy Policy</Link>
              <span>•</span>
              <Link to="/contact" className="hover:text-slate-300">Contact Desk</Link>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};
