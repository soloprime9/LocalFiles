'use client'
import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ShieldCheckIcon, EnvelopeIcon, ScaleIcon, LockClosedIcon, DocumentTextIcon } from '@heroicons/react/24/outline';

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

function LegalShell({ icon: Icon, title, updated, children }) {
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

export function AboutUs() {
  useSeo(
    'About Us — FalconSpido',
    'FalconSpido is an independent, cross-platform directory for trading indicators, EAs, bots, signals and strategies — built to help traders compare tools transparently.'
  );
  return (
    <LegalShell icon={ShieldCheckIcon} title="About FalconSpido">
      <p>
        FalconSpido is an independent discovery hub for trading indicators, expert advisors (EAs),
        bots, signals, strategies, screeners, scripts, copy-trading services, and courses — spanning
        platforms like TradingView, MetaTrader 4/5, cTrader, NinjaTrader, 3Commas, and Pionex.
      </p>
      <h2>Our Mission</h2>
      <p>
        Trading tool marketplaces are full of inflated claims and unverifiable backtests. We built
        FalconSpido to give traders a single place to compare tools side by side using a transparent
        TrustScore — combining user ratings, verified status, backtest audit outcomes, review volume,
        and scam reports — so you can make an informed decision before spending money or risking capital.
      </p>
      <h2>How Listings Are Evaluated</h2>
      <p>
        Every listing on FalconSpido is categorized by platform, asset class, strategy type, and
        difficulty, and is eligible for community reviews and scam flagging. Backtest claims are
        labeled Verified, Suspicious, or Unaudited based on the evidence the creator provides — we do
        not treat unverified backtests as proof of performance.
      </p>
      <h2>Independence</h2>
      <p>
        FalconSpido is editorially independent. Some listings include affiliate links, which are
        always disclosed — see our{' '}
        <Link to="/disclaimer">Affiliate Disclaimer</Link>. Affiliate relationships never influence
        TrustScore calculations or search rankings.
      </p>
      <h2>Get in Touch</h2>
      <p>
        Questions, corrections, or want to list a tool? Visit our{' '}
        <Link to="/contact">Contact page</Link> or{' '}
        <Link to="/submit">submit your tool</Link> directly.
      </p>
    </LegalShell>
  );
}

export function Contact() {
  useSeo(
    'Contact Us — FalconSpido',
    'Get in touch with the FalconSpido team for listing corrections, partnership inquiries, scam reports, or general questions.'
  );
  return (
    <LegalShell icon={EnvelopeIcon} title="Contact Us">
      <p>
        We read every message. For the fastest response, pick the category below that matches your
        request.
      </p>
      <h2>General Inquiries</h2>
      <p>
        Email us at{' '}
        <a href="mailto:support@falconspido.com">support@falconspido.com</a> for questions about the
        site, partnerships, or press.
      </p>
      <h2>Report a Scam or Inaccuracy</h2>
      <p>
        Found a listing with misleading claims or a fake backtest? Use the "Report" button on the
        listing's detail page so it routes directly to our review queue, or email{' '}
        <a href="mailto:trust@falconspido.com">trust@falconspido.com</a>.
      </p>
      <h2>Submit or Update a Listing</h2>
      <p>
        Tool creators can <Link to="/submit">submit a new listing</Link> directly. For corrections to
        an existing listing, email{' '}
        <a href="mailto:listings@falconspido.com">listings@falconspido.com</a> with the listing URL.
      </p>
      <h2>Response Time</h2>
      <p>We typically respond within 2–3 business days.</p>
    </LegalShell>
  );
}

export function Disclaimer() {
  useSeo(
    'Affiliate & Trading Risk Disclaimer — FalconSpido',
    'FalconSpido affiliate disclosure and trading risk disclaimer. Trading indicators, EAs, and signals carry financial risk; past performance does not guarantee future results.'
  );
  return (
    <LegalShell icon={DocumentTextIcon} title="Disclaimer" updated="June 2026">
      <h2>Not Financial Advice</h2>
      <p>
        FalconSpido is a discovery and comparison directory. Nothing on this site constitutes
        financial, investment, or trading advice. Listings, ratings, and TrustScores reflect
        community input and our review process — they are not a recommendation to buy, use, or trade
        with any specific tool, broker, or signal provider.
      </p>
      <h2>Trading Risk</h2>
      <p>
        Trading forex, crypto, stocks, indices, commodities, and derivatives carries a high level of
        risk and may not be suitable for all investors. Past performance — including backtested
        results — does not guarantee future results. You could lose some or all of your invested
        capital. Only trade with money you can afford to lose, and consult a licensed financial
        advisor before making investment decisions.
      </p>
      <h2>Backtest & Performance Claims</h2>
      <p>
        Backtest results shown on listings are supplied by tool creators and labeled Verified,
        Suspicious, or Unaudited based on the evidence available to us at review time. A "Verified"
        label reflects that supporting evidence was reviewed — it is not an independent guarantee of
        future performance, and backtests are inherently susceptible to curve-fitting and look-ahead
        bias even when reviewed in good faith.
      </p>
      <h2>Affiliate Disclosure</h2>
      <p>
        FalconSpido participates in affiliate programs, including TradingView's affiliate program and
        broker referral programs. Some links on this site are affiliate links, meaning we may earn a
        commission if you sign up or make a purchase through them, at no additional cost to you.
        Affiliate relationships do not affect TrustScores, search rankings, or editorial content.
      </p>
      <h2>User-Submitted Content</h2>
      <p>
        Reviews, ratings, and scam reports are submitted by users and reflect their individual
        experiences. FalconSpido does not independently verify every claim made in a user review.
      </p>
    </LegalShell>
  );
}

export function PrivacyPolicy() {
  useSeo(
    'Privacy Policy — FalconSpido',
    'How FalconSpido collects, uses, and protects your personal data, including cookies, analytics, and third-party affiliate tracking.'
  );
  return (
    <LegalShell icon={LockClosedIcon} title="Privacy Policy" updated="June 2026">
      <h2>Information We Collect</h2>
      <p>
        We collect information you provide directly — such as when you submit a listing, write a
        review, or contact us — including name, email, and message content. We also collect usage
        data automatically, such as pages visited, device/browser type, and approximate location via
        IP address, to understand site usage and improve performance.
      </p>
      <h2>Cookies & Tracking</h2>
      <p>
        FalconSpido uses cookies and similar technologies for essential site functionality (such as
        remembering your compare list), analytics, and affiliate link attribution. You can control
        cookies through your browser settings; disabling them may limit some site features.
      </p>
      <h2>How We Use Your Information</h2>
      <p>
        We use collected information to operate and improve the site, respond to inquiries, moderate
        submitted reviews and listings, detect fraud or scam reports, and — where you've consented —
        send updates about the site.
      </p>
      <h2>Third-Party Services</h2>
      <p>
        We may use third-party analytics and affiliate tracking providers (for example, to attribute
        broker or TradingView referrals). These providers process data under their own privacy
        policies.
      </p>
      <h2>Data Retention & Security</h2>
      <p>
        We retain user-submitted data as long as necessary to operate the site and comply with legal
        obligations, and apply reasonable technical safeguards to protect it. No method of
        transmission or storage is 100% secure.
      </p>
      <h2>Your Rights</h2>
      <p>
        Depending on your jurisdiction, you may have the right to request access to, correction of, or
        deletion of your personal data. Contact{' '}
        <a href="mailto:privacy@falconspido.com">privacy@falconspido.com</a> to make a request.
      </p>
      <h2>Children's Privacy</h2>
      <p>FalconSpido is not directed at children under 16 and does not knowingly collect their data.</p>
      <h2>Changes to This Policy</h2>
      <p>
        We may update this policy from time to time. Material changes will be reflected by updating
        the "Last updated" date above.
      </p>
    </LegalShell>
  );
}

export function Terms() {
  useSeo(
    'Terms of Service — FalconSpido',
    'The terms governing your use of FalconSpido, including listing submissions, reviews, affiliate links, and limitation of liability.'
  );
  return (
    <LegalShell icon={ScaleIcon} title="Terms of Service" updated="June 2026">
      <h2>Acceptance of Terms</h2>
      <p>
        By accessing or using FalconSpido, you agree to these Terms of Service. If you do not agree,
        please discontinue use of the site.
      </p>
      <h2>Use of the Site</h2>
      <p>
        FalconSpido grants you a limited, non-exclusive, non-transferable license to access and use
        the site for personal, non-commercial research into trading tools. You agree not to scrape,
        republish, or resell listing data in bulk without permission.
      </p>
      <h2>User Submissions</h2>
      <p>
        By submitting a listing, review, or scam report, you confirm the information is accurate to
        the best of your knowledge and grant FalconSpido a license to display, edit for clarity, and
        moderate that content. We reserve the right to reject, edit, or remove any submission at our
        discretion, including for suspected fraud, spam, or policy violations.
      </p>
      <h2>No Warranty</h2>
      <p>
        Listings, ratings, and TrustScores are provided "as is" without warranty of any kind. We do
        not guarantee the accuracy, completeness, or performance of any third-party indicator, EA,
        bot, signal service, or broker listed on the site.
      </p>
      <h2>Limitation of Liability</h2>
      <p>
        To the maximum extent permitted by law, FalconSpido and its operators are not liable for any
        trading losses, damages, or claims arising from your use of, or reliance on, content found on
        this site, including listings accessed via affiliate links.
      </p>
      <h2>Third-Party Links</h2>
      <p>
        FalconSpido links to third-party platforms, brokers, and tool creators. We do not control and
        are not responsible for the content, products, or practices of those third parties.
      </p>
      <h2>Changes to These Terms</h2>
      <p>
        We may revise these terms at any time. Continued use of the site after changes are posted
        constitutes acceptance of the revised terms.
      </p>
      <h2>Contact</h2>
      <p>
        Questions about these terms? Email{' '}
        <a href="mailto:support@falconspido.com">support@falconspido.com</a>.
      </p>
    </LegalShell>
  );
}
