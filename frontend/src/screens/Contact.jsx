import React, { useState } from 'react';
import { Mail, Send, CheckCircle2, MessageSquare, Globe, AlertCircle } from 'lucide-react';

export const Contact = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [subject, setSubject] = useState('listing-claim');
  const [message, setMessage] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg('');

    if (!name || !email || !message) {
      setErrorMsg('Please complete all contact inquiries fields.');
      setLoading(false);
      return;
    }

    // Simulate contact form submission
    setTimeout(() => {
      setLoading(false);
      setSubmitted(true);
      setName('');
      setEmail('');
      setMessage('');
    }, 1000);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-16 grid grid-cols-1 md:grid-cols-3 gap-8">
      {/* Sidebar Details */}
      <div className="space-y-6 md:col-span-1">
        <div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Contact Us
          </h1>
          <p className="text-slate-400 text-xs mt-2 leading-relaxed">
            Reach out to our operator network regarding indicator claims, sitemap reports, database updates, or partnership queries.
          </p>
        </div>

        <div className="space-y-4">
          <div className="flex items-start space-x-3 bg-[#11111a] border border-white/5 p-4 rounded-xl">
            <Globe className="h-5 w-5 text-amber-500 mt-0.5 flex-shrink-0" />
            <div>
              <h4 className="text-white text-xs font-bold uppercase font-mono">Our Directive</h4>
              <p className="text-[11px] text-slate-400 mt-1">
                To keep FalconSpido's listings spam-free and fully optimized for Google Search standards.
              </p>
            </div>
          </div>

          <div className="flex items-start space-x-3 bg-[#11111a] border border-white/5 p-4 rounded-xl">
            <MessageSquare className="h-5 w-5 text-amber-500 mt-0.5 flex-shrink-0" />
            <div>
              <h4 className="text-white text-xs font-bold uppercase font-mono">Fast Response</h4>
              <p className="text-[11px] text-slate-400 mt-1">
                Moderator nodes review claims within 24-48 hours. Claimed listings can customize their descriptions directly.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Form */}
      <div className="glass-panel p-8 rounded-2xl border border-white/5 md:col-span-2 relative overflow-hidden">
        {/* Glow Element */}
        <div className="absolute -bottom-32 -right-32 w-64 h-64 bg-amber-500/5 rounded-full blur-3xl pointer-events-none"></div>

        {submitted ? (
          <div className="min-h-[300px] flex flex-col items-center justify-center text-center space-y-4">
            <div className="h-12 w-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <CheckCircle2 className="h-6 w-6 text-emerald-400" />
            </div>
            <h2 className="text-xl font-bold text-white">Message Transmitted</h2>
            <p className="text-xs text-slate-400 max-w-sm leading-relaxed">
              Your inquiry has been stored securely in FalconSpido's MERN communications server. Our developers will review the claims shortly.
            </p>
            <button
              onClick={() => setSubmitted(false)}
              className="text-xs font-semibold text-amber-500 hover:text-amber-400 underline"
            >
              Send another message ->
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
            <h3 className="text-lg font-bold text-white mb-2">operator Gateway</h3>

            {errorMsg && (
              <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 p-3.5 rounded-lg text-xs flex items-center gap-2">
                <AlertCircle className="h-4 w-4" />
                <span>{errorMsg}</span>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1.5 font-mono">
                  Your Name
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Trader"
                  className="w-full bg-[#11111a] border border-white/5 rounded-lg py-2 pl-3 pr-4 text-xs text-slate-300 placeholder-slate-650 focus:outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 transition-all font-sans"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1.5 font-mono">
                  Your Email
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="contact@domain.com"
                  className="w-full bg-[#11111a] border border-white/5 rounded-lg py-2 pl-3 pr-4 text-xs text-slate-300 placeholder-slate-650 focus:outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 transition-all font-sans"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1.5 font-mono">
                Claim/Inquiry Category
              </label>
              <select
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full bg-[#11111a] border border-white/5 rounded-lg py-2 pl-3 pr-4 text-xs text-slate-300 focus:outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 transition-all font-sans"
              >
                <option value="listing-claim">Claim Existing Indicator Listing</option>
                <option value="technical-support">Technical Platform Support</option>
                <option value="abuse-report">Report Scam/Inaccurate Data</option>
                <option value="google-gsc">Google Sitemap or GSC Index Inquiry</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-450 uppercase tracking-widest mb-1.5 font-mono">
                Message Body
              </label>
              <textarea
                required
                rows="5"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Describe your inquiry with references..."
                className="w-full bg-[#11111a] border border-white/5 rounded-lg py-2.5 pl-3 pr-4 text-xs text-slate-300 placeholder-slate-650 focus:outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20 transition-all font-sans"
              ></textarea>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="flex items-center justify-center space-x-1.5 bg-amber-500 hover:bg-amber-400 text-black font-semibold text-xs py-2 px-5 rounded-lg shadow-md hover:shadow-lg transition-all duration-150 disabled:opacity-55 cursor-pointer"
            >
              {loading ? (
                <div className="h-4 w-4 border-2 border-black border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <>
                  <Send className="h-3.5 w-3.5" />
                  <span>Transmit Query</span>
                </>
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default Contact;
