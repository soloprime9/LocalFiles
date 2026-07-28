'use client'
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { QuestionMarkCircleIcon, ChevronDownIcon } from '@heroicons/react/24/outline';

const FAQS = [
  {
    q: 'What is FalconSpido?',
    a: "FalconSpido is a cross-platform directory for trading indicators, expert advisors (EAs), bots, signals, strategies, screeners, scripts, copy-trading services, and courses. We help traders compare tools across TradingView, MetaTrader 4/5, cTrader, NinjaTrader, 3Commas, Pionex and more — using a transparent TrustScore instead of marketing claims.",
  },
  {
    q: 'Is FalconSpido free to use?',
    a: 'Yes. Browsing, searching, comparing tools, reading reviews, and using the AI Finder are all free. Some listed indicators and EAs are paid products sold by their creators — FalconSpido itself does not charge to browse the directory.',
  },
  {
    q: 'How is TrustScore calculated?',
    a: "TrustScore combines five factors: average user rating, creator verification status, backtest audit outcome (Verified, Suspicious, or Unaudited), total review count, and any open scam flags. A high rating alone can't offset an unresolved scam flag or an unaudited backtest claim. Full methodology is on our Editorial Policy page.",
  },
  {
    q: 'What does "Verified" backtest mean — is it a guarantee of profit?',
    a: 'No. "Verified" means the creator supplied backtest evidence (trade logs, broker statements, or exported reports) that our review process checked for obvious red flags like curve-fitting or missing out-of-sample data. It is not an independent guarantee of future performance. Trading carries risk, and past results — backtested or live — never guarantee future results.',
  },
  {
    q: 'Are the reviews on FalconSpido real?',
    a: "Reviews are submitted by site visitors. We moderate for spam and abuse, but we don't independently verify every review against a purchase record unless it's labeled 'Verified Purchase.' We never remove a negative review just because a listing's creator disputes it.",
  },
  {
    q: 'How do I report a scam or misleading listing?',
    a: "Open the listing's detail page and use the 'Report' button to flag it with a reason — that routes directly to our review queue. You can also email trust@falconspido.com with the listing URL.",
  },
  {
    q: 'Does FalconSpido make money from affiliate links?',
    a: 'Yes, some listings include affiliate links (for example, to TradingView or broker sign-ups), and we may earn a commission at no extra cost to you. This is always disclosed and never affects TrustScore, search ranking, or which listings we feature. See our Disclaimer for details.',
  },
  {
    q: 'How do I list my own indicator, EA, or bot?',
    a: "Use the Submit Listing page to send your tool's details, platform, pricing, and a link. Submissions are manually reviewed before publishing — we may ask for backtest evidence to assign an audit status.",
  },
  {
    q: 'What platforms does FalconSpido cover?',
    a: 'TradingView, MetaTrader 4, MetaTrader 5, cTrader, NinjaTrader, ThinkOrSwim, 3Commas, Pionex, Cryptohopper, and Interactive Brokers, with more being added as listings are submitted.',
  },
  {
    q: 'Can I compare multiple tools side by side?',
    a: "Yes. Click the compare icon on any listing card to add it to your comparison (up to 3 tools at once), then visit the Compare page for a side-by-side breakdown of price, rating, win rate, platforms, and TrustScore.",
  },
  {
    q: "What is the AI Finder?",
    a: 'A short guided quiz (platform, asset class, trading style, tool type, and budget) that filters the directory down to tools matching your answers. It is a filtering shortcut, not personalized financial advice.',
  },
  {
    q: 'Is anything on FalconSpido financial advice?',
    a: 'No. FalconSpido is a discovery and comparison directory only. Nothing on this site is financial, investment, or trading advice. Always do your own research and consult a licensed financial advisor before trading. See our full Disclaimer.',
  },
];

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

    const scriptId = 'faq-jsonld';
    let script = document.getElementById(scriptId);
    if (!script) {
      script = document.createElement('script');
      script.id = scriptId;
      script.type = 'application/ld+json';
      document.head.appendChild(script);
    }
    script.textContent = JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: FAQS.map((item) => ({
        '@type': 'Question',
        name: item.q,
        acceptedAnswer: {
          '@type': 'Answer',
          text: item.a,
        },
      })),
    });

    return () => {
      script?.remove();
    };
  }, [title, description]);
}

function FaqItem({ q, a, open, onToggle }) {
  return (
    <div className="border-b border-[#1F2937] last:border-b-0">
      <button
        type="button"
        onClick={onToggle}
        className="w-full flex items-center justify-between gap-4 py-4 text-left"
        aria-expanded={open}
      >
        <span className="text-white font-medium text-sm sm:text-base">{q}</span>
        <ChevronDownIcon
          className={`w-4 h-4 text-gray-500 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>
      {open && <p className="text-gray-400 text-sm leading-relaxed pb-4 pr-6">{a}</p>}
    </div>
  );
}

export default function FAQ() {
  useSeo(
    'Frequently Asked Questions — FalconSpido',
    'Answers to common questions about FalconSpido: how TrustScore works, backtest verification, affiliate disclosure, submitting a listing, and more.'
  );
  const [openIndex, setOpenIndex] = useState(0);

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
      <div className="flex items-center gap-3 mb-2">
        <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center shrink-0">
          <QuestionMarkCircleIcon className="w-5 h-5 text-amber-400" />
        </div>
        <h1 className="text-2xl font-bold text-white">Frequently Asked Questions</h1>
      </div>
      <p className="text-gray-500 text-sm mb-8">
        Can't find what you're looking for? <Link to="/contact" className="text-amber-400 hover:underline">Contact us</Link>.
      </p>

      <div className="card px-5 sm:px-6">
        {FAQS.map((item, i) => (
          <FaqItem
            key={item.q}
            q={item.q}
            a={item.a}
            open={openIndex === i}
            onToggle={() => setOpenIndex(openIndex === i ? -1 : i)}
          />
        ))}
      </div>
    </div>
  );
}
