import React from 'react';
import { BarChart4, Send, Fingerprint, Search, Cpu, Heart } from 'lucide-react';
import { Link } from 'react-router-dom';

export const AboutUs = () => {
  return (
    <div className="max-w-4xl mx-auto px-4 py-16 space-y-12">
      {/* Hero */}
      <div className="text-center space-y-4">
        <div className="inline-flex h-12 w-12 rounded-xl bg-amber-500/10 items-center justify-center border border-amber-500/20 mb-2">
          <BarChart4 className="h-6 w-6 text-amber-500" />
        </div>
        <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-5xl">
          About FalconSpido
        </h1>
        <p className="text-sm font-mono text-amber-500 uppercase tracking-widest">
          QUANT DIRECTORY & SEARCH INDEX ENGINE
        </p>
        <p className="max-w-2xl mx-auto text-base text-slate-400 leading-relaxed pt-2">
          FalconSpido is a premium, automated web indexing directory and technical audit platform designed exclusively for quantitative trading scripts, expert advisors (EAs), custom MT4/5 indicators, Pine Script strategies, and trading room signals.
        </p>
      </div>

      {/* Grid Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-panel p-6 rounded-xl border border-white/5 space-y-3">
          <div className="h-10 w-10 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-lg flex items-center justify-center">
            <Cpu className="h-5 w-5" />
          </div>
          <h3 className="text-base font-bold text-white">Quantitative Focus</h3>
          <p className="text-xs text-slate-400 leading-relaxed font-sans">
            We meticulously categorize algorithmic trading systems, overlay indicators, oscillators, and advanced DCA calculators.
          </p>
        </div>

        <div className="glass-panel p-6 rounded-xl border border-white/5 space-y-3">
          <div className="h-10 w-10 bg-amber-500/10 border border-amber-500/20 text-amber-500 rounded-lg flex items-center justify-center">
            <Search className="h-5 w-5" />
          </div>
          <h3 className="text-base font-bold text-white">AI Search Grounding</h3>
          <p className="text-xs text-slate-400 leading-relaxed font-sans">
            Using Google Search grounded models, FalconSpido crawls target strategy URLs, indexing professional structural summaries, pros, cons, and performance stats without spamming.
          </p>
        </div>

        <div className="glass-panel p-6 rounded-xl border border-white/5 space-y-3">
          <div className="h-10 w-10 bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 rounded-lg flex items-center justify-center">
            <Fingerprint className="h-5 w-5" />
          </div>
          <h3 className="text-base font-bold text-white">Trust & Compliance</h3>
          <p className="text-xs text-slate-400 leading-relaxed font-sans">
            We require verified moderator approvals for every directory entry, sending clean, non-spam structural updates to the Google Search Console (GSC) Indexer.
          </p>
        </div>
      </div>

      {/* Mission */}
      <div className="bg-[#11111a] border border-white/5 p-8 rounded-xl space-y-4">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <Heart className="h-5 w-5 text-rose-500" />
          <span>Our Vision for Modern Algorithmic Discovery</span>
        </h2>
        <p className="text-xs text-slate-400 leading-relaxed">
          In 2026, search engine results are flooded with generic, low-density, or unhelpful AI-generated spam. This "thin content" makes finding authentic, original Pine Scripts or trading setups highly challenging. 
        </p>
        <p className="text-xs text-slate-400 leading-relaxed">
          FalconSpido bridges this divide by operating a **Strict Structural Quality Rule**. Our directory only hosts listings with highly informational math breakdowns, direct comparison nodes, and true backtest reviews. Each page is designed purposefully so that both professional quant traders and Google search engines find extreme educational value.
        </p>
      </div>

      {/* Call to action */}
      <div className="text-center py-6">
        <p className="text-xs text-slate-500 font-mono mb-4">Have an indicator or automated screener to submit?</p>
        <div className="flex justify-center gap-4">
          <Link to="/submit" className="bg-amber-500 hover:bg-amber-400 text-black px-5 py-2 rounded-lg text-xs font-semibold shadow-md transition-all">
            Submit Tool URL
          </Link>
          <Link to="/contact" className="bg-[#141421] hover:bg-[#11111a] border border-white/10 text-slate-300 px-5 py-2 rounded-lg text-xs font-semibold transition-all">
            Contact Developers
          </Link>
        </div>
      </div>
    </div>
  );
};

export default AboutUs;
