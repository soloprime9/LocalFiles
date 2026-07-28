import React from 'react';
import { FileText, AlertTriangle, Scale, ShieldAlert } from 'lucide-react';

export const TermsOfService = () => {
  return (
    <div className="max-w-4xl mx-auto px-4 py-16 space-y-12">
      <div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight sm:text-4xl">
          Terms of Service
        </h1>
        <p className="text-xs font-mono text-slate-500 mt-2 uppercase tracking-wider">
          Effective Date: June 18, 2026 | Node Version 10.4
        </p>
      </div>

      <div className="glass-panel p-8 rounded-2xl border border-white/5 space-y-8 text-xs text-slate-300 leading-relaxed font-sans">
        
        {/* Risk Warning */}
        <div className="bg-amber-500/5 border border-amber-500/20 p-5 rounded-xl space-y-2">
          <h3 className="text-sm font-bold text-amber-500 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            <span>CRITICAL TRADING RISK WARNING</span>
          </h3>
          <p className="text-slate-400">
            Financial market speculation (Forex, Crypto, Futures, Indexes, Commodities) carries a high level of risk and may not be suitable for all investors. The tools, scripts, expert advisors, calendars, and strategies listed in this directory are for educational, informational, and quantitative research purposes only. FalconSpido does not provide direct trading advisories, financial advice, or guaranteed systems. Past performance is never indicative of future backtest records.
          </p>
        </div>

        {/* Section 1 */}
        <section className="space-y-3">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <FileText className="h-4 w-4 text-amber-500" />
            <span>1. Platform Intent</span>
          </h2>
          <p>
            FalconSpido governs a research index database. By crawling or using any indicator detail page in our system, you agree that you are solely responsible for testing systems in simulated / demo environments (paper trading) before executing any dynamic positions in live brokerage servers.
          </p>
        </section>

        {/* Section 2 */}
        <section className="space-y-3 border-t border-white/5 pt-6">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-rose-450" />
            <span>2. Submitter Directives</span>
          </h2>
          <p>
            When submitting Pine Scripts or signal portals to our submitter module:
          </p>
          <ul className="list-disc pl-5 space-y-1 text-slate-400">
            <li>You guarantee that the indicator url is a functional strategy reference with valid documentation.</li>
            <li>You authorize FalconSpido to run an automated crawling parse, leveraging Google grounded AI models to structure descriptions, benefits, pros, cons, and configuration catalogs.</li>
            <li>You understand that administrative approval is strictly mandatory before any page goes online, or is pinged to Google search index consoles.</li>
            <li>We reserve absolute right to scrub, review, or reject listings that promote scam signals, false percentage guarantees, or malware files.</li>
          </ul>
        </section>

        {/* Section 3 */}
        <section className="space-y-3 border-t border-white/5 pt-6">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Scale className="h-4 w-4 text-teal-400" />
            <span>3. Limitation of Liabilities</span>
          </h2>
          <p>
            In no case shall FalconSpido, its operators, or developers be liable for direct or indirect financial losses, margins calls, software failures, API latency, web disruptions, or erroneous DCA grid calculation estimates generated via our risk calculator models. All calculators use mathematical approximations and must be cross-verified.
          </p>
        </section>

      </div>
    </div>
  );
};

export default TermsOfService;
