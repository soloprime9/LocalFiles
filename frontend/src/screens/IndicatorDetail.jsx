import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiService } from '../utils/api';
import { setSeo } from '../utils/seo';
import { StarRating } from '../components/ui/StarRating';
import { Badge } from '../components/ui/Badge';
import { Spinner } from '../components/ui/Spinner';
import { 
  ArrowLeft, 
  CheckCircle, 
  MessageSquare, 
  FileText, 
  Cpu, 
  ShieldAlert, 
  ExternalLink,
  ChevronDown,
  ChevronUp,
  ThumbsUp,
  ThumbsDown,
  Plus,
  AlertTriangle,
  Send,
  HelpCircle
} from 'lucide-react';

export const IndicatorDetail = () => {
  const { slug } = useParams();
  const [indicator, setIndicator] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [presets, setPresets] = useState([]);
  const [backtests, setBacktests] = useState([]);

  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  // FAQ collapse state
  const [faqOpen, setFaqOpen] = useState({});

  // Review Form States
  const [reviewerName, setReviewerName] = useState('');
  const [reviewerType, setReviewerType] = useState('Beginner');
  const [formRating, setFormRating] = useState(5);
  const [formTitle, setFormTitle] = useState('');
  const [formBody, setFormBody] = useState('');
  const [profitableVal, setProfitableVal] = useState(true);
  const [recommendVal, setRecommendVal] = useState(true);
  const [isScamForm, setIsScamForm] = useState(false);
  const [reviewSuccess, setReviewSuccess] = useState('');

  // Preset Form States
  const [newPresetTitle, setNewPresetTitle] = useState('');
  const [newPresetAsset, setNewPresetAsset] = useState('Forex');
  const [newPresetSymbol, setNewPresetSymbol] = useState('EURUSD');
  const [newPresetTimeframe, setNewPresetTimeframe] = useState('H1');
  const [newPresetParamKey, setNewPresetParamKey] = useState('');
  const [newPresetParamVal, setNewPresetParamVal] = useState('');
  const [newPresetWinRate, setNewPresetWinRate] = useState(60);
  const [presetSuccess, setPresetSuccess] = useState('');

  // Backtest Report States
  const [testerName, setTesterName] = useState('');
  const [testerType, setTesterType] = useState('Intermediate');
  const [testTimeframe, setTestTimeframe] = useState('H1');
  const [testSymbol, setTestSymbol] = useState('XAUUSD');
  const [testPeriod, setTestPeriod] = useState('Jan - Dec 2025');
  const [testDataSource, setTestDataSource] = useState('TradingView Strategy Tester');
  const [reportWinRate, setReportWinRate] = useState(65);
  const [reportDrawdown, setReportDrawdown] = useState(15);
  const [reportNetProfit, setReportNetProfit] = useState(48);
  const [reportTrades, setReportTrades] = useState(120);
  const [backtestSuccess, setBacktestSuccess] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      if (!slug) return;
      setIsLoading(true);
      try {
        const indRes = await apiService.getIndicator(slug);
        if (indRes?.success && indRes.data) {
          const fetchedInd = indRes.data;
          setIndicator(fetchedInd);
          setSeo({
  title: `${fetchedInd.name} — Review, Parameters, and Audits | FalconSpido`,
  description: fetchedInd.description || `${fetchedInd.name} reviews, parameters, and trust score on FalconSpido.`,
  path: `/indicators/${fetchedInd.slug}`
});

          // Batch load reviews, presets, and backtests
          const [revRes, presRes, backRes] = await Promise.all([
            apiService.getReviews(fetchedInd._id),
            apiService.getIndicatorPresets(fetchedInd._id),
            apiService.getBacktestReports(fetchedInd._id)
          ]);

          if (revRes?.success) setReviews(revRes.data);
          if (presRes?.success) setPresets(presRes.data);
          if (backRes?.success) setBacktests(backRes.data);
        }
      } catch (err) {
        console.error('Failed to load detail matrices:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, [slug]);

  // Submit dynamic review handler
  const handleReviewSubmit = async (e) => {
    e.preventDefault();
    if (!reviewerName || !formTitle || !formBody || !indicator) return;

    try {
      const res = await apiService.submitReview({
        indicatorId: indicator._id,
        reviewerName,
        reviewerType,
        rating: formRating,
        title: formTitle,
        body: formBody,
        profitableForReviewer: profitableVal,
        wouldRecommend: recommendVal,
        isScam: isScamForm
      });

      if (res?.success) {
        setReviewSuccess('Review catalogued successfully under cryptographic audit protection!');
        // Pre-hydrate review locally
        setReviews(prev => [res.data, ...prev]);
        setReviewerName('');
        setFormTitle('');
        setFormBody('');
      }
    } catch (err) {
      alert(err.message || 'Verification Error during Review execution');
    }
  };

  // Submit Settings Preset Config
  const handlePresetSubmit = async (e) => {
    e.preventDefault();
    if (!newPresetTitle || !indicator) return;

    try {
      const parameters = {};
      if (newPresetParamKey) {
        parameters[newPresetParamKey] = newPresetParamVal || 'Enabled';
      } else {
        parameters['DefaultPeriod'] = '14';
      }

      const res = await apiService.submitPreset({
        indicatorId: indicator._id,
        title: newPresetTitle,
        assetClass: newPresetAsset,
        symbol: newPresetSymbol,
        timeframe: newPresetTimeframe,
        parameters,
        backtestResults: {
          winRate: newPresetWinRate,
          profitFactor: 1.8,
          maxDrawdown: 10,
          totalTrades: 120,
          period: '1 Year'
        },
        author: reviewerName || 'QuantTrader'
      });

      if (res?.success) {
        setPresetSuccess('Settings Config Preset saved successfully!');
        setPresets(prev => [res.data, ...prev]);
        setNewPresetTitle('');
        setNewPresetParamKey('');
        setNewPresetParamVal('');
      }
    } catch (err) {
      alert(err.message || 'Error occurred registering setting preset parameters');
    }
  };

  // Submit Auditor Report
  const handleBacktestSubmit = async (e) => {
    e.preventDefault();
    if (!testerName || !indicator) return;

    try {
      const res = await apiService.submitBacktestReport({
        indicatorId: indicator._id,
        testerName,
        testerType,
        timeframe: testTimeframe,
        marketSymbol: testSymbol,
        testPeriod,
        metrics: {
          netProfitPercent: reportNetProfit,
          maxDrawdownPercent: reportDrawdown,
          profitFactor: 2.1,
          winRatePercent: reportWinRate,
          totalTrades: reportTrades
        },
        dataSource: testDataSource,
        verifiedWithLogs: true
      });

      if (res?.success) {
        setBacktestSuccess('Backtest Auditor Audit processed fully!');
        setBacktests(prev => [res.data, ...prev]);
        setTesterName('');
      }
    } catch (err) {
      alert(err.message || 'Backtest parsing error');
    }
  };

  // Upvote preset rating values
  const handleVotePreset = async (id, direction) => {
    try {
      const res = await apiService.votePreset(id, direction);
      if (res?.success) {
        setPresets(prev => prev.map(p => p._id === id ? res.data : p));
      }
    } catch (err) {
      console.error('Error voting on preset matrix:', err);
    }
  };

  const toggleFaq = (idx) => {
    setFaqOpen(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  if (isLoading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center space-y-4">
        <Spinner size="lg" />
        <p className="text-sm font-mono text-slate-500">De-serializing listing specifications...</p>
      </div>
    );
  }

  if (!indicator) {
    return (
      <div className="max-w-xl mx-auto py-24 text-center">
        <ShieldAlert className="h-12 w-12 text-rose-500 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-white">Listing specifications not found</h2>
        <p className="text-xs text-slate-400 mt-2">The requested indicator slug may have been deprecated or decommissioned under system security guidelines.</p>
        <Link to="/indicators" className="mt-6 inline-block text-amber-500 border border-amber-500/30 font-bold px-4 py-2 rounded-xl text-xs">
          Return to Directory
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      
      {/* Return button */}
      <div>
        <Link to="/indicators" className="inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-400 hover:text-white transition-all">
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Alpha Directory</span>
        </Link>
      </div>

      {/* Main Core Specifications Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Visual presentation card block (2 / 3 cols) */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-[#08080d] border border-white/5 rounded-2xl p-6 space-y-6">
            
            {/* Core Listing Headers & Visual Details */}
            <div className="flex flex-col sm:flex-row items-start justify-between gap-4">
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge variant="amber">{indicator.listingType}</Badge>
                  {indicator.isPremiumListing && <Badge variant="purple">Premium</Badge>}
                  {indicator.isVerified && <Badge variant="green">Staff Verified</Badge>}
                  {indicator.isScamFlagged && <Badge variant="red">Alert: High Discrepancy Scam</Badge>}
                </div>
                <h1 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight">{indicator.name}</h1>
                <p className="text-xs text-slate-400 leading-relaxed max-w-xl">
                  {indicator.description}
                </p>
              </div>

              <div className="text-right sm:text-right flex flex-col items-start sm:items-end">
                <span className="text-2xl font-black font-mono text-amber-400">
                  {indicator.isFree ? 'FREE' : `$${indicator.price}`}
                </span>
                <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">
                  {indicator.pricingModel} Model
                </span>
              </div>
            </div>

            {/* Screenshots container */}
            <div className="relative aspect-video rounded-xl bg-slate-900 border border-white/10 overflow-hidden flex items-center justify-center">
              {indicator.imageUrl ? (
                <img 
                  src={indicator.imageUrl} 
                  alt={indicator.name} 
                  className="object-cover w-full h-full"
                  referrerPolicy="no-referrer"
                />
              ) : (
                <span className="text-xs text-slate-500">Live Indicator Chart Plot - Community Sandbox</span>
              )}
            </div>

            {/* Pros/Cons list */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-white/5">
              <div className="space-y-2 bg-emerald-500/5 p-4 rounded-xl border border-emerald-500/10 text-xs">
                <h4 className="font-bold text-emerald-400 uppercase tracking-widest text-[10px]">Verified Advantages</h4>
                <ul className="space-y-1.5 text-slate-300">
                  {indicator.pros?.map((pro, index) => <li key={index}>✓ {pro}</li>) || (
                    <>
                      <li>✓ Documented win metrics</li>
                      <li>✓ Robust risk sizing configs</li>
                    </>
                  )}
                </ul>
              </div>

              <div className="space-y-2 bg-rose-500/5 p-4 rounded-xl border border-rose-500/10 text-xs">
                <h4 className="font-bold text-rose-400 uppercase tracking-widest text-[10px]">Identified Liabilities</h4>
                <ul className="space-y-1.5 text-slate-300">
                  {indicator.cons?.map((con, index) => <li key={index}>✗ {con}</li>) || (
                    <>
                      <li>✗ Heavy parameters re-painting</li>
                      <li>✗ Broker lag latency traps</li>
                    </>
                  )}
                </ul>
              </div>
            </div>

            {/* Long Description markdown box */}
            {indicator.longDescription && (
              <div className="pt-4 border-t border-white/5 space-y-2">
                <h3 className="text-sm font-extrabold text-white uppercase tracking-wider">Implementation Methodology</h3>
                <p className="text-xs text-slate-400 leading-relaxed whitespace-pre-line">
                  {indicator.longDescription}
                </p>
              </div>
            )}

          </div>

          {/* Sub Navigation workspace tabs */}
          <div className="flex border-b border-white/5 text-xs text-slate-400 font-bold select-none gap-2">
            <button
              onClick={() => setActiveTab('overview')}
              className={`pb-3 px-4 transition-all relative ${activeTab === 'overview' ? 'text-amber-400 font-extrabold border-b-2 border-amber-400' : 'hover:text-white'}`}
            >
              Audits Overviews
            </button>
            <button
              onClick={() => setActiveTab('presets')}
              className={`pb-3 px-4 transition-all relative ${activeTab === 'presets' ? 'text-amber-400 font-extrabold border-b-2 border-amber-400' : 'hover:text-white'}`}
            >
              Community Config Presets ({presets.length})
            </button>
            <button
              onClick={() => setActiveTab('backtests')}
              className={`pb-3 px-4 transition-all relative ${activeTab === 'backtests' ? 'text-amber-400 font-extrabold border-b-2 border-amber-400' : 'hover:text-white'}`}
            >
              Log Auditors Auditor ({backtests.length})
            </button>
            <button
              onClick={() => setActiveTab('reviews')}
              className={`pb-3 px-4 transition-all relative ${activeTab === 'reviews' ? 'text-amber-400 font-extrabold border-b-2 border-amber-400' : 'hover:text-white'}`}
            >
              Reviews ({reviews.length})
            </button>
          </div>

          {/* Tab Render Module */}
          <div className="space-y-6">
            
            {/* Overview & FAQ Sub-Tab */}
            {activeTab === 'overview' && (
              <div className="space-y-6">
                
                {/* Accordion FAQ Component */}
                <div className="bg-[#08080d] border border-white/5 rounded-2xl p-5 space-y-4">
                  <h3 className="text-sm font-extrabold text-white uppercase tracking-wider flex items-center space-x-2">
                    <HelpCircle className="h-4.5 w-4.5 text-amber-500" />
                    <span>Frequently Queried Technical Parameters (FAQs)</span>
                  </h3>

                  <div className="divide-y divide-white/5">
                    {(indicator.faqs && indicator.faqs.length > 0 ? indicator.faqs : [
                      { question: "Does this indicator paint backward charts in real-time?", answer: "No. All algorithms perform forward execution tests strictly without repainting historic signals." },
                      { question: "What is the recommended minimum balance to manage risk effectively?", answer: "We advise setting up at least $500 balance, implementing maximum 1-2% risk lot parameters." }
                    ]).map((faq, index) => (
                      <div key={index} className="py-3">
                        <button
                          onClick={() => toggleFaq(index)}
                          className="w-full text-left flex items-center justify-between text-xs font-bold text-slate-200 hover:text-amber-400 transition-colors"
                        >
                          <span>{faq.question}</span>
                          {faqOpen[index] ? <ChevronUp className="h-4 w-4 text-amber-500" /> : <ChevronDown className="h-4 w-4" />}
                        </button>
                        {faqOpen[index] && (
                          <p className="mt-2 text-xs text-slate-400 leading-relaxed font-normal whitespace-pre-line bg-white/5 p-3 rounded-lg border border-white/5">
                            {faq.answer}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

              </div>
            )}

            {/* Community Presets Sub-Tab */}
            {activeTab === 'presets' && (
              <div className="space-y-6">
                
                {/* Submit Preset parameter form */}
                <form onSubmit={handlePresetSubmit} className="bg-[#0b0b12] border border-amber-500/10 rounded-2xl p-5 space-y-4 relative">
                  <h4 className="text-xs font-extrabold text-white uppercase tracking-wider">Share your optimal Parameter Combination Preset</h4>
                  <p className="text-[10px] text-slate-400 leading-normal">
                    traders can submit, rate, and discover the absolute best parameter configurations for any indicator relative to target markets.
                  </p>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <input
                      type="text"
                      placeholder="Preset Name (e.g., Scalper Pro)"
                      value={newPresetTitle}
                      onChange={(e) => setNewPresetTitle(e.target.value)}
                      className="bg-[#11111a] border border-white/5 py-1.5 px-2.5 text-xs text-slate-200 rounded-lg placeholder-slate-500 focus:outline-none"
                    />
                    <select
                      value={newPresetAsset}
                      onChange={(e) => setNewPresetAsset(e.target.value)}
                      className="bg-[#11111a] border border-white/5 py-1.5 px-2.5 text-xs text-slate-300 rounded-lg focus:outline-none"
                    >
                      <option value="Forex">Forex Markets</option>
                      <option value="Crypto">Crypto Assets</option>
                      <option value="Commodities">Commodities</option>
                    </select>
                    <input
                      type="text"
                      placeholder="Symbol (e.g., BTCUSDT)"
                      value={newPresetSymbol}
                      onChange={(e) => setNewPresetSymbol(e.target.value)}
                      className="bg-[#11111a] border border-white/5 py-1.5 px-2.5 text-xs text-slate-200 rounded-lg placeholder-slate-500 focus:outline-none"
                    />
                    <input
                      type="text"
                      placeholder="Timeframe (e.g., M15)"
                      value={newPresetTimeframe}
                      onChange={(e) => setNewPresetTimeframe(e.target.value)}
                      className="bg-[#11111a] border border-white/5 py-1.5 px-2.5 text-xs text-slate-200 rounded-lg placeholder-slate-500 focus:outline-none"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <input
                      type="text"
                      placeholder="Key parameter (e.g. Length)"
                      value={newPresetParamKey}
                      onChange={(e) => setNewPresetParamKey(e.target.value)}
                      className="bg-[#11111a] border border-white/5 py-1.5 px-2.5 text-xs text-slate-200 rounded-lg placeholder-slate-500 focus:outline-none"
                    />
                    <input
                      type="text"
                      placeholder="Value (e.g. 21)"
                      value={newPresetParamVal}
                      onChange={(e) => setNewPresetParamVal(e.target.value)}
                      className="bg-[#11111a] border border-white/5 py-1.5 px-2.5 text-xs text-slate-200 rounded-lg placeholder-slate-500 focus:outline-none"
                    />
                  </div>

                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center space-x-2">
                      <span className="text-slate-500 font-mono text-[11px]">Backtest Win-Rate:</span>
                      <input 
                        type="number" 
                        value={newPresetWinRate} 
                        onChange={(e) => setNewPresetWinRate(Number(e.target.value))}
                        className="bg-[#11111a] border border-white/5 py-1 w-16 text-center text-slate-200 rounded-lg text-xs"
                      />
                      <span>%</span>
                    </div>

                    <button
                      type="submit"
                      className="bg-amber-500 hover:bg-amber-400 text-black py-1.5 px-4 rounded-lg font-bold"
                    >
                      Publish settings Preset
                    </button>
                  </div>

                  {presetSuccess && <p className="text-emerald-400 font-mono text-[10px]">{presetSuccess}</p>}
                </form>

                {/* Preset List display */}
                <div className="space-y-4">
                  {presets.length === 0 ? (
                    <p className="text-xs text-slate-500 text-center py-6 font-mono">No community presets submitted yet. Be the first to optimize settings!</p>
                  ) : (
                    presets.map((preset) => (
                      <div key={preset._id} className="bg-[#08080d] border border-white/5 rounded-xl p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                        <div className="space-y-1">
                          <h4 className="text-xs font-bold text-white flex items-center space-x-2">
                            <span>{preset.title}</span>
                            {preset.isVerifiedByStaff && <Badge variant="green">Verified Staff Setup</Badge>}
                          </h4>
                          <p className="text-[10px] text-slate-400 font-mono">
                            Symbol: <span className="text-slate-200 font-bold">{preset.symbol} ({preset.timeframe})</span> | Timeframe: {preset.timeframe}
                          </p>
                          <div className="flex flex-wrap gap-1.5 pt-1 text-[10px] font-mono">
                            {Object.entries(preset.parameters || {}).map(([k, v]) => (
                              <span key={k} className="bg-white/5 px-1.5 py-0.5 rounded text-amber-400 border border-white/5">
                                {k}: {v}
                              </span>
                            ))}
                          </div>
                        </div>

                        <div className="flex items-center space-x-4">
                          <div className="text-right font-mono">
                            <span className="text-[10px] text-slate-500 block uppercase">Win Rate</span>
                            <span className="text-xs font-bold text-emerald-400">{preset.backtestResults?.winRate || 62}%</span>
                          </div>

                          <div className="flex items-center space-x-1 border border-white/5 bg-[#10101c]/50 rounded-lg p-1">
                            <button 
                              onClick={() => handleVotePreset(preset._id, 'up')}
                              className="p-1 hover:text-amber-500 text-slate-400 flex items-center space-x-0.5"
                            >
                              <ThumbsUp className="h-3 w-3" />
                              <span className="text-[10px]">{preset.votes?.upvotes || 0}</span>
                            </button>
                            <span className="text-slate-600">/</span>
                            <button 
                              onClick={() => handleVotePreset(preset._id, 'down')}
                              className="p-1 hover:text-rose-500 text-slate-400 flex items-center space-x-0.5"
                            >
                              <ThumbsDown className="h-3 w-3" />
                              <span className="text-[10px]">{preset.votes?.downvotes || 0}</span>
                            </button>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>

              </div>
            )}

            {/* Log Auditor Auditor Sub-Tab */}
            {activeTab === 'backtests' && (
              <div className="space-y-6">
                
                {/* Form to submit backtest audit */}
                <form onSubmit={handleBacktestSubmit} className="bg-[#0b0b12] border border-amber-500/10 rounded-2xl p-5 space-y-4">
                  <h4 className="text-xs font-extrabold text-white uppercase tracking-wider">Quant Auditor: Submit Comparative Backtest Logs</h4>
                  <p className="text-[10px] text-slate-400 leading-normal">
                    Upload your actual win-rates and drawdown metrics from Pine Script strategy alerts or MetaTrader logs. Our pipeline automatically triggers discrepancy audits to flag fake screenshot claims!
                  </p>

                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    <input
                      type="text"
                      placeholder="Your Analyst Name"
                      value={testerName}
                      onChange={(e) => setTesterName(e.target.value)}
                      className="bg-[#11111a] border border-white/5 py-1.5 px-2.5 text-xs text-slate-200 rounded-lg placeholder-slate-500 focus:outline-none"
                    />
                    <select
                      value={testerType}
                      onChange={(e) => setTesterType(e.target.value)}
                      className="bg-[#11111a] border border-white/5 py-1.5 px-2.5 text-xs text-slate-300 rounded-lg focus:outline-none"
                    >
                      <option value="Beginner">Beginner Trader</option>
                      <option value="Intermediate">Intermediate Trader</option>
                      <option value="Pro">Pro Trader</option>
                      <option value="Quantitative Developer">Quantitative Developer</option>
                    </select>
                    <select
                      value={testDataSource}
                      onChange={(e) => setTestDataSource(e.target.value)}
                      className="bg-[#11111a] border border-white/5 py-1.5 px-2.5 text-xs text-slate-300 rounded-lg focus:outline-none"
                    >
                      <option value="TradingView Strategy Tester">TradingView Strategy Tester</option>
                      <option value="MetaTrader Backtest Log">MetaTrader Backtest Log</option>
                      <option value="Custom Python Framework">Custom Python Framework</option>
                      <option value="Manual Simulation">Manual Simulation</option>
                    </select>
                    <input
                      type="text"
                      placeholder="Symbol (Gold, BTC)"
                      value={testSymbol}
                      onChange={(e) => setTestSymbol(e.target.value)}
                      className="bg-[#11111a] border border-white/5 py-1.5 px-2.5 text-xs text-slate-200 rounded-lg placeholder-slate-500 focus:outline-none"
                    />
                    <input
                      type="text"
                      placeholder="Audit Period (e.g. 2025)"
                      value={testPeriod}
                      onChange={(e) => setTestPeriod(e.target.value)}
                      className="bg-[#11111a] border border-white/5 py-1.5 px-2.5 text-xs text-slate-200 rounded-lg placeholder-slate-500 focus:outline-none"
                    />
                    <input
                      type="text"
                      placeholder="TF (M5, H4)"
                      value={testTimeframe}
                      onChange={(e) => setTestTimeframe(e.target.value)}
                      className="bg-[#11111a] border border-white/5 py-1.5 px-2.5 text-xs text-slate-200 rounded-lg placeholder-slate-500 focus:outline-none"
                    />
                  </div>

                  <div className="grid grid-cols-4 gap-3 text-center text-xs">
                    <div>
                      <span className="text-slate-500 block text-[9px] uppercase font-mono">Logged Win-Rate (%)</span>
                      <input 
                        type="number" 
                        value={reportWinRate} 
                        onChange={(e) => setReportWinRate(Number(e.target.value))}
                        className="bg-[#11111a] border border-white/5 py-1 w-full text-center text-slate-200 rounded-lg"
                      />
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[9px] uppercase font-mono">Max Drawdown (%)</span>
                      <input 
                        type="number" 
                        value={reportDrawdown} 
                        onChange={(e) => setReportDrawdown(Number(e.target.value))}
                        className="bg-[#11111a] border border-white/5 py-1 w-full text-center text-slate-200 rounded-lg"
                      />
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[9px] uppercase font-mono">Net Profit (%)</span>
                      <input 
                        type="number" 
                        value={reportNetProfit} 
                        onChange={(e) => setReportNetProfit(Number(e.target.value))}
                        className="bg-[#11111a] border border-white/5 py-1 w-full text-center text-slate-200 rounded-lg"
                      />
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[9px] uppercase font-mono">Total Trades Count</span>
                      <input 
                        type="number" 
                        value={reportTrades} 
                        onChange={(e) => setReportTrades(Number(e.target.value))}
                        className="bg-[#11111a] border border-white/5 py-1 w-full text-center text-slate-200 rounded-lg"
                      />
                    </div>
                  </div>

                  <div className="flex justify-between items-center">
                    <div className="text-[10px] text-amber-500 font-mono">
                      <span>Automated Audits flags win rate lower by &ge;15% or MaxDD higher by &ge;12%.</span>
                    </div>
                    <button
                      type="submit"
                      className="bg-amber-500 hover:bg-amber-400 text-black py-1.5 px-4 rounded-lg font-bold text-xs"
                    >
                      Audit Comparative Logs
                    </button>
                  </div>

                  {backtestSuccess && <p className="text-emerald-400 font-mono text-[10px]">{backtestSuccess}</p>}
                </form>

                {/* Backtests List Auditor details */}
                <div className="space-y-4">
                  {backtests.length === 0 ? (
                    <p className="text-xs text-slate-500 text-center py-6 font-mono">No comparative backtest auditor filings yet. Help protect traders by submitting logs!</p>
                  ) : (
                    backtests.map((rep) => {
                      // Algorithmic Discrepancy Alert Calculations
                      // Acknowledge isScam/Discrepancy flag based on metrics comparison
                      const isDiscrepant = rep.discrepancyFlag || 
                        (indicator.backtestData && (
                          (indicator.backtestData.winRate - rep.metrics.winRatePercent >= 15) ||
                          (rep.metrics.maxDrawdownPercent - indicator.backtestData.maxDrawdown >= 12)
                        ));

                      return (
                        <div key={rep._id} className="bg-[#08080d] border border-white/5 rounded-xl p-4 space-y-3">
                          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-white/5 pb-2">
                            <div>
                              <span className="text-xs font-bold text-white">{rep.testerName || 'Analyst'} Report</span>
                              <p className="text-[10px] text-slate-500 font-mono">Market symbol: {rep.marketSymbol} ({rep.timeframe}) | Log validation: {rep.dataSource}</p>
                            </div>

                            <div>
                              {isDiscrepant ? (
                                <Badge variant="red">Discrepancy Warning Flagged</Badge>
                              ) : (
                                <Badge variant="green">Audited Conforming Logs</Badge>
                              )}
                            </div>
                          </div>

                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs font-mono py-1">
                            <div className="bg-white/5 p-2 rounded-lg">
                              <span className="text-slate-500 text-[10px] block">Net Profit</span>
                              <span className="font-bold text-slate-200">{rep.metrics.netProfitPercent}%</span>
                            </div>
                            <div className="bg-white/5 p-2 rounded-lg">
                              <span className="text-slate-500 text-[10px] block">Drawdown Audited</span>
                              <span className="font-bold text-rose-400">{rep.metrics.maxDrawdownPercent}%</span>
                            </div>
                            <div className="bg-white/5 p-2 rounded-lg">
                              <span className="text-slate-500 text-[10px] block">Win Rate</span>
                              <span className="font-bold text-emerald-400">{rep.metrics.winRatePercent}%</span>
                            </div>
                            <div className="bg-white/5 p-2 rounded-lg">
                              <span className="text-slate-500 text-[10px] block">Total Trades</span>
                              <span className="font-bold text-slate-200">{rep.metrics.totalTrades}</span>
                            </div>
                          </div>

                          {/* Trigger detailed Warning description */}
                          {isDiscrepant && (
                            <div className="bg-rose-500/10 border border-rose-500/20 p-3 rounded-lg flex items-start space-x-2 text-[11px] text-rose-400">
                              <AlertTriangle className="h-4.5 w-4.5 text-rose-500 flex-shrink-0 mt-0.5" />
                              <div className="space-y-0.5">
                                <span className="font-bold block">ALGORITHMIC LOG AUDIT COLLUSION DETECTED:</span>
                                <p className="leading-relaxed">
                                  {rep.discrepancyReason || `This review has triggered our automated consumer integrity warning. The author claimed ${indicator.backtestData?.winRate}% win rate with ${indicator.backtestData?.maxDrawdown}% Max Drawdown. This audit log reports ${rep.metrics.winRatePercent}% win rate, presenting extreme anomalies matching statistical fabrication patterns.`}
                                </p>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })
                  )}
                </div>

              </div>
            )}

            {/* Reviews Sub-Tab */}
            {activeTab === 'reviews' && (
              <div className="space-y-6">
                
                {/* Submit review Form */}
                <form onSubmit={handleReviewSubmit} className="bg-[#0b0b12] border border-amber-500/10 rounded-2xl p-5 space-y-4">
                  <h4 className="text-xs font-extrabold text-white uppercase tracking-wider">Log an Audited community Review</h4>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <input
                      type="text"
                      placeholder="Your Analyst Name"
                      value={reviewerName}
                      onChange={(e) => setReviewerName(e.target.value)}
                      className="bg-[#11111a] border border-white/5 py-1.5 px-3 text-xs text-slate-200 rounded-lg placeholder-slate-500 focus:outline-none"
                    />

                    <select
                      value={reviewerType}
                      onChange={(e) => setReviewerType(e.target.value)}
                      className="bg-[#11111a] border border-white/5 py-1.5 px-3 text-xs text-slate-300 rounded-lg"
                    >
                      <option value="Beginner">Beginner Trader Style</option>
                      <option value="Intermediate">Intermediate Algos</option>
                      <option value="Pro">Professional Quants</option>
                      <option value="Institutional">Institutional Grade</option>
                    </select>
                  </div>

                  <div className="flex items-center space-x-3 text-xs">
                    <span className="text-slate-500">Execution Score:</span>
                    <StarRating rating={formRating} interactive onRatingChange={(val) => setFormRating(val)} size={16} />
                  </div>

                  <input
                    type="text"
                    placeholder="Short summary title (e.g., Profitable scalping model)"
                    value={formTitle}
                    onChange={(e) => setFormTitle(e.target.value)}
                    className="w-full bg-[#11111a] border border-white/5 py-1.5 px-3 text-xs text-slate-200 rounded-lg placeholder-slate-500 focus:outline-none"
                  />

                  <textarea
                    placeholder="Describe your execution variables, trading pairs, and account sizing metrics..."
                    rows={3}
                    value={formBody}
                    onChange={(e) => setFormBody(e.target.value)}
                    className="w-full bg-[#11111a] border border-white/5 py-2 px-3 text-xs text-slate-200 rounded-lg placeholder-slate-500 focus:outline-none resize-none"
                  ></textarea>

                  <div className="flex flex-col sm:flex-row gap-3 text-[11px] text-slate-400 select-none">
                    <label className="flex items-center space-x-1.5 cursor-pointer">
                      <input 
                        type="checkbox" 
                        checked={profitableVal} 
                        onChange={(e) => setProfitableVal(e.target.checked)}
                        className="rounded bg-[#11111a] border-white/10"
                      />
                      <span>Profitable on my account</span>
                    </label>

                    <label className="flex items-center space-x-1.5 cursor-pointer">
                      <input 
                        type="checkbox" 
                        checked={recommendVal} 
                        onChange={(e) => setRecommendVal(e.target.checked)}
                        className="rounded bg-[#11111a] border-white/10"
                      />
                      <span>Would recommend to others</span>
                    </label>

                    <label className="flex items-center space-x-1.5 cursor-pointer text-rose-400 font-semibold ml-auto">
                      <input 
                        type="checkbox" 
                        checked={isScamForm} 
                        onChange={(e) => setIsScamForm(e.target.checked)}
                        className="rounded bg-[#11111a] border-rose-500/30 text-rose-500 focus:ring-rose-500/20"
                      />
                      <span>Flag as Scam operations</span>
                    </label>
                  </div>

                  <div className="flex justify-end pt-2">
                    <button
                      type="submit"
                      className="bg-amber-500 hover:bg-amber-400 text-black py-1.5 px-5 rounded-lg font-bold text-xs flex items-center space-x-1"
                    >
                      <Send className="h-3 w-3" />
                      <span>Submit Cryptographic Review</span>
                    </button>
                  </div>

                  {reviewSuccess && <p className="text-emerald-400 font-mono text-[10px]">{reviewSuccess}</p>}
                </form>

                {/* Review lists items */}
                <div className="space-y-4">
                  {reviews.length === 0 ? (
                    <p className="text-xs text-slate-500 text-center py-6 font-mono">No user reviews archived. Be the first to catalog your feedback!</p>
                  ) : (
                    reviews.map((rev) => (
                      <div key={rev._id} className="bg-[#08080d] border border-white/5 rounded-xl p-4 space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <span className="text-xs font-bold text-white">{rev.reviewerName}</span>
                            <Badge variant="gray">{rev.reviewerType}</Badge>
                            {rev.verified && <Badge variant="green">Verified Audit</Badge>}
                          </div>
                          <span className="text-[10px] text-slate-500 font-mono">
                            {new Date(rev.createdAt).toLocaleDateString()}
                          </span>
                        </div>

                        <div className="flex items-center space-x-2 pt-0.5">
                          <StarRating rating={rev.rating} size={11} />
                          <span className="text-xs font-bold text-slate-200">{rev.title}</span>
                        </div>

                        <p className="text-xs text-slate-400 leading-relaxed font-normal whitespace-pre-line">
                          {rev.body}
                        </p>

                        <div className="flex flex-wrap items-center gap-3 text-[10px] text-slate-500 pt-2 border-t border-white/5">
                          <span className={rev.profitableForReviewer ? 'text-emerald-400' : 'text-slate-500'}>
                            {rev.profitableForReviewer ? '✓ Profitable account' : '✗ Non-profitable'}
                          </span>
                          <span>•</span>
                          <span className={rev.wouldRecommend ? 'text-emerald-400' : 'text-slate-500'}>
                            {rev.wouldRecommend ? '✓ Highly Recommended' : '✗ Neutral/Avoid'}
                          </span>
                          {rev.isScam && (
                            <span className="bg-rose-500/10 border border-rose-500/20 text-rose-400 px-1.5 rounded uppercase font-bold text-[8px] animate-pulse">
                              Scam warning logged
                            </span>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>

              </div>
            )}

          </div>

        </div>

        {/* Right Column: Platform summary catalog widgets (1 / 3 col) */}
        <div className="space-y-6">
          
          {/* Main Specifications properties card */}
          <div className="bg-[#0a0a10] border border-white/5 p-5 rounded-2xl space-y-4">
            <h3 className="text-sm font-extrabold text-white uppercase tracking-wider">Specifications properties</h3>

            <div className="space-y-3 font-mono text-xs text-slate-400">
              <div className="flex justify-between py-1.5 border-b border-white/5">
                <span>Indicator Author</span>
                <span className="text-slate-200 font-bold">{indicator.author}</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-white/5">
                <span>Trading System Platform</span>
                <span className="text-slate-200 font-bold">
                  {typeof indicator.platform === 'object' ? indicator.platform?.name : indicator.platform}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-white/5">
                <span>Timeframes Target</span>
                <span className="text-slate-200 font-bold max-w-[150px] truncate" title={indicator.timeframes?.join(', ')}>
                  {indicator.timeframes?.join(', ') || 'All'}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-white/5">
                <span>Volatility assets</span>
                <span className="text-slate-200 font-bold truncate max-w-[150px]" title={indicator.assetClass?.join(', ')}>
                  {indicator.assetClass?.join(', ') || 'Forex'}
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-white/5">
                <span>Rating</span>
                <div className="flex items-center space-x-1 text-slate-200 font-bold">
                  <span>{indicator.rating?.toFixed(1) || '0.0'}</span>
                  <StarRating rating={indicator.rating || 0} size={11} />
                </div>
              </div>
              <div className="flex justify-between py-1.5 border-b border-white/5">
                <span>Trust Score index</span>
                <span className="text-amber-500 font-extrabold">{indicator.trustScore}/100</span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-white/5">
                <span>Listing status</span>
                <Badge variant={indicator.status === 'Active' ? 'green' : 'gray'}>
                  {indicator.status || 'Active'}
                </Badge>
              </div>
            </div>

            {/* External Links */}
            <div className="pt-2 space-y-2">
              {indicator.externalUrl && (
                <a 
                  href={indicator.externalUrl} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="flex items-center justify-center space-x-2 bg-amber-500 hover:bg-amber-400 text-black py-2.5 rounded-xl font-bold text-xs"
                >
                  <span>Access Script Parameters</span>
                  <ExternalLink className="h-4 w-4" />
                </a>
              )}
            </div>
          </div>

          {/* Secure indicator sandbox widget info */}
          <div className="bg-gradient-to-br from-[#121008] to-[#0a0a14] border border-amber-500/10 p-5 rounded-2xl space-y-3">
            <h4 className="text-xs font-bold text-slate-100 flex items-center space-x-1">
              <CheckCircle className="h-4 w-4 text-amber-500" />
              <span>Falcon Audit Protection</span>
            </h4>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Every system parameters, backtest file logs, and customer ratings submitted to FalconSpido undergoes statistical filters, preventing review farms, scam scripts, or fictitious EA performance logs from manipulating the catalog scores.
            </p>
          </div>

        </div>

      </div>

    </div>
  );
};
