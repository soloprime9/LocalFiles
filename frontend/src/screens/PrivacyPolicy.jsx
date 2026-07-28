import React from 'react';
import { Eye, ShieldCheck, Database, Cookie, Lock } from 'lucide-react';

export const PrivacyPolicy = () => {
  return (
    <div className="max-w-4xl mx-auto px-4 py-16 space-y-12">
      <div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight sm:text-4xl">
          Privacy Policy
        </h1>
        <p className="text-xs font-mono text-slate-500 mt-2 uppercase tracking-wider">
          Effective Date: June 18, 2026 | Node Version 10.4
        </p>
      </div>

      <div className="glass-panel p-8 rounded-2xl border border-white/5 space-y-8 text-xs text-slate-300 leading-relaxed font-sans">
        
        {/* Section 1 */}
        <section className="space-y-3">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Eye className="h-4 w-4 text-amber-500" />
            <span>1. Information We Collect</span>
          </h2>
          <p>
            FalconSpido operates an automated indexing directory for quant resources. To ensure complete transparency under search guidelines, we collect and store:
          </p>
          <ul className="list-disc pl-5 space-y-1 text-slate-400">
            <li>
              <strong>User Submissions:</strong> Standard names, contact emails, target URLs of indicators/scripts, descriptions, and related software category choices.
            </li>
            <li>
              <strong>Active Session Cookies:</strong> Secure JSON Web Tokens (JWT) preserved in <code className="text-amber-500 font-mono">localStorage</code> to track moderation logins and session clearances.
            </li>
            <li>
              <strong>Bookmarks & Favorites:</strong> Local storage cache flags (<code className="text-amber-500 font-mono">fs_favs</code>) which allow you to compare metrics and save indicators without server databases.
            </li>
            <li>
              <strong>System Logs:</strong> IP address details, search query patterns, and time metadata to secure our API gateways from automation spam.
            </li>
          </ul>
        </section>

        {/* Section 2 */}
        <section className="space-y-3 border-t border-white/5 pt-6">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            <span>2. How We Use Your Information</span>
          </h2>
          <p>
            We process the collected parameters purely to maintain high-quality service directories:
          </p>
          <ul className="list-disc pl-5 space-y-1 text-slate-400">
            <li>To compile highly structured AI webpage summaries using Gemini models, saving you from entering indicators manually.</li>
            <li>To screen indicator submissions for fraud, trading scams, or bad links before presenting them to search portals.</li>
            <li>To feed live Search Console (GSC) APIs for submitting verified URL index queues when listing items are approved.</li>
          </ul>
        </section>

        {/* Section 3 */}
        <section className="space-y-3 border-t border-white/5 pt-6">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Cookie className="h-4 w-4 text-yellow-500" />
            <span>3. Cookies and Browser Cache</span>
          </h2>
          <p>
            We only use standard, functional browser storage structures. We DO NOT use invasive advertising tracking trackers or pass your personal search history parameters to third-party ad bidding networks.
          </p>
        </section>

        {/* Section 4 */}
        <section className="space-y-3 border-t border-white/5 pt-6">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Database className="h-4 w-4 text-blue-400" />
            <span>4. Submitting a URL Disclaimer</span>
          </h2>
          <p>
            When submitting a URL (TradingView pine strategy, GitHub repository, public website), you acknowledge that our backend uses Google Search Grounded models to fetch publicly visible texts from that webpage. If you are the owner of that page and wish to have an indicator listing removed, please contact us at our support portal.
          </p>
        </section>

        {/* Section 5 */}
        <section className="space-y-3 border-t border-white/5 pt-6">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Lock className="h-4 w-4 text-rose-400" />
            <span>5. Data Protection Security</span>
          </h2>
          <p>
            FalconSpido uses full industry-standard TLS encryption, secured API endpoints, Express rate limiting, and JWT encryption protocols. We will never sell, trade, or share user emails or submissions with commercial trading systems.
          </p>
        </section>

      </div>
    </div>
  );
};

export default PrivacyPolicy;
