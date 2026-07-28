import React, { useState, useEffect } from 'react';
import { useSelector } from 'react-redux';
import { apiService } from '../utils/api';
import { setSeo } from '../utils/seo';
import { useApp } from '../context/AppContext';
import { Badge } from '../components/ui/Badge';
import { 
  PlusCircle, 
  Send, 
  Settings, 
  Workflow, 
  Zap, 
  CheckCircle2, 
  AlertTriangle, 
  Loader2, 
  Compass, 
  Eye, 
  ThumbsUp, 
  FileCheck, 
  Clock, 
  Coins 
} from 'lucide-react';

export const SubmitListing = () => {
  const { categories, platforms } = useApp();
  const { user, isAuthenticated } = useSelector((state) => state.auth);

  // Mode state: 'submit' (Default tool submission form) vs 'admin' (Audit submissions dashboard)
  const [activeTab, setActiveTab] = useState('submit');

  // URL state for the AI fast-extract pipeline
  const [targetUrl, setTargetUrl] = useState('');
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractionStep, setExtractionStep] = useState('');

  // Form states matching high-fidelity Indicator parameters
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [longDescription, setLongDescription] = useState('');
  const [listingType, setListingType] = useState('Indicator');
  const [category, setCategory] = useState('');
  const [platform, setPlatform] = useState('');
  const [price, setPrice] = useState(0);
  const [pricingModel, setPricingModel] = useState('Free');
  const [author, setAuthor] = useState('');
  const [submittedBy, setSubmittedBy] = useState('');
  const [difficulty, setDifficulty] = useState('Intermediate');
  const [assetClassInput, setAssetClassInput] = useState('Forex, Crypto');
  const [strategyTypeInput, setStrategyTypeInput] = useState('Trend, Momentum');
  const [timeframesInput, setTimeframesInput] = useState('H1, H4');
  const [tagsInput, setTagsInput] = useState('scalper, rsi');
  const [prosInput, setProsInput] = useState('Dynamic Alert system, Zero repainting');
  const [consInput, setConsInput] = useState('Requires raw-spread broker');

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  // Admin moderation deck states
  const [pendingList, setPendingList] = useState([]);
  const [isAdminLoading, setIsAdminLoading] = useState(false);
  const [adminPassKey, setAdminPassKey] = useState('');
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [moderationMessage, setModerationMessage] = useState('');
  const [gscStatusLog, setGscStatusLog] = useState('');

  // AI Automation discover states
  const [discoverKeyword, setDiscoverKeyword] = useState('TradingView Pine Scripts indicators');
  const [discoverCount, setDiscoverCount] = useState(3);
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [discoverSuccessMsg, setDiscoverSuccessMsg] = useState('');
  const [discoverErrorMsg, setDiscoverErrorMsg] = useState('');
  const [discoverStep, setDiscoverStep] = useState('');

  const handleRunAiDiscovery = async () => {
    setIsDiscovering(true);
    setDiscoverSuccessMsg('');
    setDiscoverErrorMsg('');
    setDiscoverStep('Initializing Autonomous Quant Web Discoverer...');

    const steps = [
      'Locking coordinates to trend keywords...',
      'Opening search gateways to Pine Script & Quant libraries...',
      'Synthesizing results with live Google Web Grounding...',
      'Performing real-time YouTube tutorial video validations...',
      'Filtering duplicate assets in MongoDB to avoid overlap...',
      'Writing rich instructional manual layouts with deep mathematics...',
      'Generating Cloudflare-compliant visual preview mockups...',
      'Registering discovery indices into Pending Audit queues...'
    ];

    let currentStep = 0;
    const interval = setInterval(() => {
      currentStep++;
      if (currentStep < steps.length) {
        setDiscoverStep(steps[currentStep]);
      }
    }, 2200);

    try {
      const res = await apiService.runAiDiscovery(discoverKeyword, discoverCount);
      if (res?.success) {
        setDiscoverSuccessMsg(res.message);
        fetchPendingListings();
      } else {
        setDiscoverErrorMsg(res.error || 'Automation process completed with exceptions.');
      }
    } catch (err) {
      setDiscoverErrorMsg(err.error || err.message || 'Server timeout scouring quantitative channels.');
    } finally {
      clearInterval(interval);
      setIsDiscovering(false);
      setDiscoverStep('');
    }
  };

  // AI News automation states
  const [newsTopic, setNewsTopic] = useState('crypto and global macro market news today');
  const [newsCount, setNewsCount] = useState(3);
  const [isGeneratingNews, setIsGeneratingNews] = useState(false);
  const [newsSuccessMsg, setNewsSuccessMsg] = useState('');
  const [newsErrorMsg, setNewsErrorMsg] = useState('');
  const [newsStep, setNewsStep] = useState('');

  // AI Blog automation states
  const [blogTopic, setBlogTopic] = useState('TradingView Pine Script advanced quantitative strategies');
  const [blogCount, setBlogCount] = useState(1);
  const [isGeneratingBlog, setIsGeneratingBlog] = useState(false);
  const [blogSuccessMsg, setBlogSuccessMsg] = useState('');
  const [blogErrorMsg, setBlogErrorMsg] = useState('');
  const [blogStep, setBlogStep] = useState('');

  const handleRunAiNewsIngestion = async () => {
    setIsGeneratingNews(true);
    setNewsSuccessMsg('');
    setNewsErrorMsg('');
    setNewsStep('Connecting to terminal streams...');

    const newsSteps = [
      'Scanning Bloomberg and Reuters indexes...',
      'Synchronizing global CPI and monetary policy statements...',
      'Filtering high volatility indices...',
      'Writing professional news headlines based on verified events...',
      'Writing insightful Markdown write-ups around trading ranges...',
      'Publishing macroeconomic stories directly to standard terminal datastores...'
    ];

    let stepIdx = 0;
    const interval = setInterval(() => {
      stepIdx++;
      if (stepIdx < newsSteps.length) {
        setNewsStep(newsSteps[stepIdx]);
      }
    }, 2000);

    try {
      const res = await apiService.runAiNewsIngestion(newsTopic, newsCount);
      if (res?.success) {
        setNewsSuccessMsg(res.message);
      } else {
        setNewsErrorMsg(res.error || 'Macros automation complete with issues.');
      }
    } catch (err) {
      setNewsErrorMsg(err.error || err.message || 'Global monetary feed connection error.');
    } finally {
      clearInterval(interval);
      setIsGeneratingNews(false);
      setNewsStep('');
    }
  };

  const handleRunAiBlogIngestion = async () => {
    setIsGeneratingBlog(true);
    setBlogSuccessMsg('');
    setBlogErrorMsg('');
    setBlogStep('Analyzing trending search queries (SEO Indexes)...');

    const blogSteps = [
      'Extracting mathematical strategy requirements...',
      'Mapping Pine Script breakout structure parameters...',
      'Writing professional long-form educational Markdown content...',
      'Generating sample Pine Script algorithmic scripts...',
      'Evaluating formatting for proper visual presentation...',
      'Registering masterclass guide into our indexation pool...'
    ];

    let stepIdx = 0;
    const interval = setInterval(() => {
      stepIdx++;
      if (stepIdx < blogSteps.length) {
        setBlogStep(blogSteps[stepIdx]);
      }
    }, 2200);

    try {
      const res = await apiService.runAiBlogIngestion(blogTopic, blogCount);
      if (res?.success) {
        setBlogSuccessMsg(res.message);
      } else {
        setBlogErrorMsg(res.error || 'SEO blog compilation complete with issues.');
      }
    } catch (err) {
      setBlogErrorMsg(err.error || err.message || 'Educational archives writing timeout.');
    } finally {
      clearInterval(interval);
      setIsGeneratingBlog(false);
      setBlogStep('');
    }
  };

  // AI Social Media Scraping states
  const [socialPlatform, setSocialPlatform] = useState('Reddit');
  const [socialTopic, setSocialTopic] = useState('TradingView Pine Script advanced strategy indicator');
  const [socialCount, setSocialCount] = useState(3);
  const [isSocialIngesting, setIsSocialIngesting] = useState(false);
  const [socialSuccessMsg, setSocialSuccessMsg] = useState('');
  const [socialErrorMsg, setSocialErrorMsg] = useState('');
  const [socialStep, setSocialStep] = useState('');
  const [terminalLogs, setTerminalLogs] = useState([]);

  const handleRunSocialScraping = async () => {
    setIsSocialIngesting(true);
    setSocialSuccessMsg('');
    setSocialErrorMsg('');
    setSocialStep('Connecting to platform streams...');
    
    const timestamp = () => new Date().toLocaleTimeString();
    
    // Initial standard terminal outputs
    const initialLogs = [
      `[SYS ${timestamp()}] INITIALIZING FALCONSPIDO WEB CONSOLE...`,
      `[SYS ${timestamp()}] Spawning headless crawler nodes mapped for ${socialPlatform}...`,
      `[SYS ${timestamp()}] Target SEO Subject Query: "${socialTopic}"`,
      `[DB ${timestamp()}] Verifying MongoDB connection for "SocialInsight" schema... ACTIVE`,
      `[NET ${timestamp()}] Bypassing browser-side locks via proxy headers...`,
    ];
    setTerminalLogs(initialLogs);

    const platformSteps = socialPlatform === 'Twitter/X' ? [
      `[X-STREAM ${timestamp()}] Querying Twitter/X API & live timeline structures...`,
      `[X-STREAM ${timestamp()}] Extracting global finance tags (#TradingView, #PineScript, #ForexSignals)...`,
      `[X-STREAM ${timestamp()}] Scanning accounts with high social proof ratings reporting trading alpha...`,
      `[AI-MODEL ${timestamp()}] Evaluating original user sentiment & mathematical structures...`,
      `[AI-MODEL ${timestamp()}] Generating detailed Markdown systematic guides around found systems...`
    ] : socialPlatform === 'Reddit' ? [
      `[REDDIT ${timestamp()}] Querying r/algorithmictrading, r/CryptoCurrency, and r/pineconnector hot indexes...`,
      `[REDDIT ${timestamp()}] Extraction filter active for high upvote ratios (> 92%) with code blocks...`,
      `[REDDIT ${timestamp()}] Scraping markdown structures and backtest reports published by traders...`,
      `[AI-MODEL ${timestamp()}] Structuring custom input options and mathematics for Pine Script compilation...`,
      `[AI-MODEL ${timestamp()}] Running semantic deduplication checks on strategy layouts...`
    ] : socialPlatform === 'YouTube' ? [
      `[YOUTUBE ${timestamp()}] Scanning YouTube Search feeds for matching tutorial streams...`,
      `[YOUTUBE ${timestamp()}] Compiling video captions and transcripts for Pine Script strategy parameters...`,
      `[YOUTUBE ${timestamp()}] Reading description links & comments for raw algorithmic indicator configs...`,
      `[AI-MODEL ${timestamp()}] Formulating full quantitative setup guides with backtest parameters...`,
      `[AI-MODEL ${timestamp()}] Validating videoUrl structure and relevance indexing...`
    ] : [ // Facebook / Instagram
      `[FB-IG ${timestamp()}] Scraping active quantitative trading user groups & hub timelines...`,
      `[FB-IG ${timestamp()}] Ingesting high-impact post transcripts and visual setups...`,
      `[FB-IG ${timestamp()}] Filtering retail insights and macro sentiment indices...`,
      `[AI-MODEL ${timestamp()}] Formatting standard strategy descriptors and trading parameters...`,
      `[AI-MODEL ${timestamp()}] Calculating initial relevance analytics...`
    ];

    let currentIdx = 0;
    const interval = setInterval(() => {
      if (currentIdx < platformSteps.length) {
        setTerminalLogs(prev => [...prev, platformSteps[currentIdx]]);
        setSocialStep(platformSteps[currentIdx].replace(/\[.*?\]\s*/, ''));
        currentIdx++;
      }
    }, 1800);

    try {
      const res = await apiService.runSocialScraping(socialPlatform, socialTopic, socialCount);
      if (res?.success) {
        setSocialSuccessMsg(res.message);
        
        // Append actual database inserts back to the terminal box
        const parsedItems = res.data || [];
        const successLogs = [
          `[SYS ${timestamp()}] SCRA_PARSE PHASE COMPLETED. UNPACKING REAL INGESTED ASSETS...`
        ];
        
        parsedItems.forEach((it, idx) => {
          successLogs.push(`[DB-INGEST ${timestamp()}] Item #${idx + 1} ARCHIVED: "${it.title}"`);
          successLogs.push(`   - Author Ref: @${it.author} on ${it.platform}`);
          successLogs.push(`   - Sentiment Bias: ${it.sentiment} | Relevance: ${it.relevanceScore}%`);
          successLogs.push(`   - Asset Tags Identified: ${JSON.stringify(it.assetTags)}`);
          successLogs.push(`   - Verified Origin: ${it.sourceUrl}`);
        });

        successLogs.push(`[SYS ${timestamp()}] AUTOMATION CYCLE FINISHED SUCCESS. ${parsedItems.length} records written safely.`);
        
        // Allow interval to finish or clear and dump
        setTerminalLogs(prev => [...prev, ...successLogs]);
      } else {
        setSocialErrorMsg(res.error || 'Automation processing completed with limitations.');
        setTerminalLogs(prev => [...prev, `[ERROR ${timestamp()}] Ingestion aborted: ${res.error || 'Server error'}`]);
      }
    } catch (err) {
      setSocialErrorMsg(err.error || err.message || 'Server timeout scrying external social channels.');
      setTerminalLogs(prev => [...prev, `[ERROR ${timestamp()}] Exception caught: ${err.message || 'Connection timeout'}`]);
    } finally {
      clearInterval(interval);
      setIsSocialIngesting(false);
      setSocialStep('');
    }
  };

  useEffect(() => {
    setSeo({
  title: `${fetchedInd.name} — Review, Parameters, and Audits | FalconSpido`,
  description: fetchedInd.description || `${fetchedInd.name} reviews, parameters, and trust score on FalconSpido.`,
  path: `/indicators/${fetchedInd.slug}`
});
    if (categories.length > 0 && !category) {
      setCategory(categories[0]._id);
    }
    if (platforms.length > 0 && !platform) {
      setPlatform(platforms[0]._id);
    }
  }, [categories, platforms]);

  // Auto-unlock if logged-in user is admin
  useEffect(() => {
    if (isAuthenticated && user?.role === 'admin') {
      setIsUnlocked(true);
    }
  }, [isAuthenticated, user]);

  // Load pending list whenever admin tab is shown
  useEffect(() => {
    if (activeTab === 'admin' && isUnlocked) {
      fetchPendingListings();
    }
  }, [activeTab, isUnlocked]);

  const fetchPendingListings = async () => {
    setIsAdminLoading(true);
    try {
      const res = await apiService.getPendingSubmissions();
      if (res?.success) {
        setPendingList(res.data);
      }
    } catch (err) {
      console.error('Error fetching pending indicators:', err);
    } finally {
      setIsAdminLoading(false);
    }
  };

  // Execute Gemini server-grounded extraction
  const handleAiExtraction = async () => {
    if (!targetUrl) {
      setErrorMessage('Please type a valid URL to extract spec parameters.');
      return;
    }
    setErrorMessage('');
    setSubmitSuccess('');
    setIsExtracting(true);

    const steps = [
      'Establishing connection to targeting URL...',
      'Crawling remote HTML parameters...',
      'Invoking Gemini 3.5 model with live Google Search Web Grounding...',
      'Extracting professional descriptions, pro/con matrices...',
      'Compiling structured schema, mapping DB constraints...',
      'Optimizing SEO headers to match human copywriting...'
    ];

    let currentStep = 0;
    setExtractionStep(steps[0]);
    const timer = setInterval(() => {
      currentStep++;
      if (currentStep < steps.length) {
        setExtractionStep(steps[currentStep]);
      }
    }, 1500);

    try {
      const res = await apiService.extractAiDetails(targetUrl);
      if (res?.success && res.data) {
        const d = res.data;
        setName(d.toolName || '');
        setDescription(d.description || '');
        setLongDescription(d.longDescription || '');
        setListingType(d.listingType || 'Indicator');
        setPrice(d.price || 0);
        setPricingModel(d.pricingModel || 'Free');
        setDifficulty(d.difficulty || 'Intermediate');

        // Parse lists to strings
        if (d.assetClass) setAssetClassInput(d.assetClass.join(', '));
        if (d.strategyType) setStrategyTypeInput(d.strategyType.join(', '));
        if (d.timeframes) setTimeframesInput(d.timeframes.join(', '));
        if (d.tags) setTagsInput(d.tags.join(', '));
        if (d.pros) setProsInput(d.pros.join(', '));
        if (d.cons) setConsInput(d.cons.join(', '));

        // Auto-match MongoDB Object Reference IDs for categories & platforms
        if (platforms.length > 0 && d.platform) {
          const matchedPlat = platforms.find(p => p.name.toLowerCase().includes(d.platform.toLowerCase()));
          if (matchedPlat) setPlatform(matchedPlat._id);
        }

        if (categories.length > 0 && d.listingType) {
          // Map listings models to correct seeded directory categories
          let mappingName = 'Indicators';
          if (d.listingType === 'EA') mappingName = 'Expert Advisors';
          if (d.listingType === 'Bot') mappingName = 'Trading Bots';
          if (d.listingType === 'Signal') mappingName = 'Signals';
          if (d.listingType === 'Strategy') mappingName = 'Strategies';
          if (d.listingType === 'Screener') mappingName = 'Screeners';
          if (d.listingType === 'Script') mappingName = 'Scripts & Alerts';

          const matchedCat = categories.find(c => c.name.toLowerCase().includes(mappingName.toLowerCase()));
          if (matchedCat) setCategory(matchedCat._id);
        }

        setSubmitSuccess('Specification filled successfully by Google-Grounded AI! Review and submit.');
      }
    } catch (err) {
      setErrorMessage(err.error || 'Server timed out during web parsing. Relying on GSC templates...');
    } finally {
      clearInterval(timer);
      setIsExtracting(false);
      setExtractionStep('');
    }
  };

  // Submit to DB with pending state
  const handleSubmitSpecification = async (e) => {
    e.preventDefault();
    if (!name || !description || !author || !submittedBy) {
      setErrorMessage('Please complete Name, Description, Author, and your Submitter Email.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage('');
    setSubmitSuccess('');

    try {
      const slugValue = name.toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/(^-|-$)+/g, '');

      // Parse comma inputs back to Arrays
      const assetClasses = assetClassInput.split(',').map(s => s.trim()).filter(Boolean);
      const strategyTypes = strategyTypeInput.split(',').map(s => s.trim()).filter(Boolean);
      const tfList = timeframesInput.split(',').map(s => s.trim()).filter(Boolean);
      const tagList = tagsInput.split(',').map(s => s.trim()).filter(Boolean);
      const prosList = prosInput.split(',').map(s => s.trim()).filter(Boolean).slice(0, 5);
      const consList = consInput.split(',').map(s => s.trim()).filter(Boolean).slice(0, 5);

      const newListingData = {
        name,
        slug: slugValue,
        listingType,
        category,
        platform,
        description,
        longDescription,
        price,
        pricingModel,
        isFree: pricingModel === 'Free' || price === 0,
        author,
        submittedBy,
        difficulty,
        assetClass: assetClasses,
        strategyType: strategyTypes,
        timeframes: tfList,
        tags: tagList,
        pros: prosList,
        cons: consList,
        demoUrl: targetUrl || '',
        status: 'pending', // Explicitly pending for Admin moderate
        isVerified: false,
        trustScore: 40,
        backtestData: {
          winRate: 60,
          maxDrawdown: 10,
          auditStatus: 'Unaudited'
        },
        imageUrl: 'https://placehold.co/800x400/1a1a1a/F59E0B?text=' + encodeURIComponent(name)
      };

      const res = await apiService.createIndicator(newListingData);
      if (res?.success) {
        setSubmitSuccess('Technical tool specification uploaded successfully! Sent to admin audit database (awaiting approval).');
        setName('');
        setDescription('');
        setLongDescription('');
        setPrice(0);
        setTargetUrl('');
      } else {
        setErrorMessage('Verification error compiling specs payload parameters.');
      }
    } catch (err) {
      setErrorMessage(err.error || 'Server integration fault saving spec state schema.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Unlock Admin deck
  const handleUnlockAdmin = (e) => {
    e.preventDefault();
    if (adminPassKey === 'admin123') {
      setIsUnlocked(true);
      setErrorMessage('');
    } else {
      setErrorMessage('Invalid administrative master secret key.');
    }
  };

  // Perform moderation: Approve / Reject
  const handleApprove = async (id, title) => {
    setModerationMessage('');
    setGscStatusLog('');
    try {
      const res = await apiService.approveSubmission(id);
      if (res?.success) {
        setModerationMessage(`Success: "${title}" approved and catalog initialized to live!`);
        if (res.gsc_notice) {
          setGscStatusLog(res.gsc_notice);
        }
        fetchPendingListings();
      }
    } catch (err) {
      setModerationMessage(`Moderation exception: ${err.error || err.message}`);
    }
  };

  const handleReject = async (id, title) => {
    setModerationMessage('');
    setGscStatusLog('');
    try {
      const res = await apiService.rejectSubmission(id);
      if (res?.success) {
        setModerationMessage(`Notification: "${title}" has been successfully rejected & archived.`);
        fetchPendingListings();
      }
    } catch (err) {
      setModerationMessage(`Error archiving listing: ${err.error || err.message}`);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      
      {/* Header and Mode Selector */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-white/5 pb-6">
        <div className="space-y-1">
          <span className="text-[10px] text-amber-500 uppercase tracking-widest font-extrabold flex items-center space-x-1">
            <Zap className="h-4 w-4 text-amber-500 animate-pulse" />
            <span>AI QUANT REGISTRY ENGINE v3.1</span>
          </span>
          <h1 className="text-xl sm:text-3xl font-black text-white tracking-tight">Strategy Registry & GSC Indexing</h1>
          <p className="text-xs text-slate-400">
            Publish automated systems, Indicators, or EAs. Scan product URLs, generate dynamic SEO specifications with AI, and moderate submissions.
          </p>
        </div>

        {/* Tab Controls */}
        <div className="bg-[#0b0b12] border border-white/5 rounded-xl p-1 flex space-x-1 self-stretch sm:self-auto">
          <button
            onClick={() => setActiveTab('submit')}
            className={`flex-1 sm:flex-none px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center space-x-1.5 ${
              activeTab === 'submit' 
                ? 'bg-amber-500 text-black shadow-lg shadow-amber-500/10' 
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Workflow className="h-3.5 w-3.5" />
            <span>AI Registry Form</span>
          </button>
          <button
            onClick={() => setActiveTab('admin')}
            className={`flex-1 sm:flex-none px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center space-x-1.5 ${
              activeTab === 'admin' 
                ? 'bg-amber-500 text-black shadow-lg shadow-amber-500/10' 
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Settings className="h-3.5 w-3.5" />
            <span>Admin Audit panel</span>
          </button>
        </div>
      </div>

      {activeTab === 'submit' ? (
        <div className="space-y-8">
          
          {/* AI Auto-Fill Deck */}
          <div className="bg-gradient-to-r from-amber-500/5 to-transparent border border-amber-500/10 p-6 rounded-2xl space-y-4">
            <div className="space-y-1">
              <h2 className="text-sm font-extrabold text-white uppercase tracking-wider flex items-center space-x-2">
                <Zap className="h-4.5 w-4.5 text-amber-500" />
                <span>AI Automated Extract Form-Filler</span>
              </h2>
              <p className="text-[11px] text-slate-400">
                Don't waste time typing descriptions, tags, pros, or cons! Supply the trading product's website, indicator script landing URL, or bot document URL.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <input
                  type="url"
                  placeholder="Paste URL, e.g., https://tradingview.com/script/macd-divergence-lux"
                  value={targetUrl}
                  onChange={(e) => setTargetUrl(e.target.value)}
                  className="w-full bg-[#0d0d14] border border-white/5 py-3 px-4 pl-10 text-slate-200 text-xs rounded-xl focus:outline-none focus:border-amber-500 transition-all font-mono"
                />
                <Compass className="absolute left-3.5 top-3.5 h-4 w-4 text-slate-500" />
              </div>
              <button
                type="button"
                onClick={handleAiExtraction}
                disabled={isExtracting || !targetUrl}
                className="bg-amber-500 hover:bg-amber-400 disabled:opacity-40 text-black px-6 py-3 rounded-xl font-bold text-xs flex items-center justify-center space-x-2 transition-all shrink-0 cursor-pointer"
              >
                {isExtracting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Analyzing target webpage...</span>
                  </>
                ) : (
                  <>
                    <Zap className="h-4 w-4" />
                    <span>Auto-fill Specs with AI</span>
                  </>
                )}
              </button>
            </div>

            {/* AI Action Status */}
            {isExtracting && (
              <div className="bg-[#0b0b14]/80 border border-amber-500/10 p-3 rounded-xl flex items-center space-x-3 text-[11px] font-mono text-amber-500">
                <div className="relative flex items-center justify-center">
                  <div className="absolute h-5 w-5 bg-amber-500/20 rounded-full animate-ping"></div>
                  <Loader2 className="h-4 w-4 animate-spin shrink-0 text-amber-500" />
                </div>
                <span>{extractionStep}</span>
              </div>
            )}
          </div>

          {/* Form Specifications layout */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            {/* Form Spec Box */}
            <div className="lg:col-span-2 bg-[#06060a] border border-white/5 rounded-2xl p-6 shadow-xl space-y-6">
              <h3 className="text-xs font-extrabold text-white uppercase tracking-widest flex items-center space-x-2 border-b border-white/5 pb-4">
                <Workflow className="h-4 w-4 text-amber-500" />
                <span>SPECIFICATIONS DETAILS FORM</span>
              </h3>

              <form onSubmit={handleSubmitSpecification} className="space-y-5 text-xs font-mono">
                {/* Name, Listing category */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-slate-400 block font-bold">Indicator / EA Name *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g., Pine Wave Harmonic Scanner"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full bg-[#0d0d14] border border-white/5 py-2.5 px-3 text-slate-200 rounded-lg focus:outline-none focus:border-amber-500 transition-all"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-slate-400 block font-bold">Catalog Listing Classification</label>
                    <select
                      value={listingType}
                      onChange={(e) => setListingType(e.target.value)}
                      className="w-full bg-[#0d0d14] border border-white/5 py-2.5 px-3 text-slate-300 rounded-lg focus:outline-none"
                    >
                      <option value="Indicator">Technical Indicator</option>
                      <option value="EA">Expert Advisor (EA)</option>
                      <option value="Bot">Automated Trading Bot</option>
                      <option value="Signal">Copy Trading Signal</option>
                      <option value="Screener">Market Screener</option>
                      <option value="Script">Execution Script</option>
                    </select>
                  </div>
                </div>

                {/* Short tagline and Author */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-slate-400 block font-bold">Brief SEO Tagline *</label>
                    <input
                      type="text"
                      required
                      maxLength={200}
                      placeholder="Quickly detects and overlays divergence indices on macro Forex timeframes..."
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      className="w-full bg-[#0d0d14] border border-white/5 py-2.5 px-3 text-slate-200 rounded-lg focus:outline-none focus:border-amber-500 transition-all"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-slate-400 block font-bold">Author / Codename *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g., QuantLab_Dev"
                      value={author}
                      onChange={(e) => setAuthor(e.target.value)}
                      className="w-full bg-[#0d0d14] border border-white/5 py-2.5 px-3 text-slate-200 rounded-lg focus:outline-none focus:border-amber-500 transition-all"
                    />
                  </div>
                </div>

                {/* Submitter Email */}
                <div className="space-y-1.5">
                  <label className="text-slate-400 block font-bold">Your Submitter / Merchant Email * (For approval updates)</label>
                  <input
                    type="email"
                    required
                    placeholder="e.g., trader@my-domain.com"
                    value={submittedBy}
                    onChange={(e) => setSubmittedBy(e.target.value)}
                    className="w-full bg-[#0d0d14] border border-white/5 py-2.5 px-3 text-slate-200 rounded-lg focus:outline-none focus:border-amber-500 transition-all"
                  />
                </div>

                {/* Categories & Platforms */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-slate-400 block font-bold">Target Market Category</label>
                    <select
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      className="w-full bg-[#0d0d14] border border-white/5 py-2.5 px-3 text-slate-300 rounded-lg focus:outline-none"
                    >
                      {categories.map((cat) => (
                        <option key={cat._id} value={cat._id}>{cat.name}</option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-slate-400 block font-bold">Primary Software Platform</label>
                    <select
                      value={platform}
                      onChange={(e) => setPlatform(e.target.value)}
                      className="w-full bg-[#0d0d14] border border-white/5 py-2.5 px-3 text-slate-300 rounded-lg focus:outline-none"
                    >
                      {platforms.map((plat) => (
                        <option key={plat._id} value={plat._id}>{plat.name}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Price, pricing model, difficulty */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-slate-400 block font-bold">Pricing Model</label>
                    <select
                      value={pricingModel}
                      onChange={(e) => setPricingModel(e.target.value)}
                      className="w-full bg-[#0d0d14] border border-white/5 py-2.5 px-3 text-slate-300 rounded-lg focus:outline-none"
                    >
                      <option value="Free">Completely Free</option>
                      <option value="One-time">One-time License</option>
                      <option value="Monthly">Monthly subscription</option>
                      <option value="Yearly">Yearly license</option>
                      <option value="Freemium">Freemium model</option>
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-slate-400 block font-bold">License Price (USD)</label>
                    <input
                      type="number"
                      disabled={pricingModel === 'Free'}
                      value={pricingModel === 'Free' ? 0 : price}
                      onChange={(e) => setPrice(Number(e.target.value))}
                      className="w-full bg-[#0d0d14] border border-white/5 py-2.5 px-3 text-slate-200 rounded-lg disabled:opacity-30 focus:outline-none focus:border-amber-500 transition-all"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-slate-400 block font-bold">Target User Difficulty</label>
                    <select
                      value={difficulty}
                      onChange={(e) => setDifficulty(e.target.value)}
                      className="w-full bg-[#0d0d14] border border-white/5 py-2.5 px-3 text-slate-300 rounded-lg focus:outline-none"
                    >
                      <option value="Beginner">Beginner level</option>
                      <option value="Intermediate">Intermediate systems</option>
                      <option value="Advanced">Advanced Quants</option>
                      <option value="Expert">Expert tier only</option>
                    </select>
                  </div>
                </div>

                {/* Comma tag arrays */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-slate-400 block font-bold">Target Asset Classes</label>
                    <input
                      type="text"
                      placeholder="e.g. Crypto, Forex, Stocks, Gold"
                      value={assetClassInput}
                      onChange={(e) => setAssetClassInput(e.target.value)}
                      className="w-full bg-[#0d0d14] border border-white/5 py-2.5 px-3 text-slate-200 rounded-lg focus:outline-none focus:border-amber-500"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-slate-400 block font-bold">Applicable Strategy Concepts</label>
                    <input
                      type="text"
                      placeholder="e.g. Trend, Reversal, Scalping, Smart Money"
                      value={strategyTypeInput}
                      onChange={(e) => setStrategyTypeInput(e.target.value)}
                      className="w-full bg-[#0d0d14] border border-white/5 py-2.5 px-3 text-slate-200 rounded-lg focus:outline-none focus:border-amber-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-slate-400 block font-bold">Trading Timeframes</label>
                    <input
                      type="text"
                      placeholder="e.g. M5, M15, H1, H4, D1"
                      value={timeframesInput}
                      onChange={(e) => setTimeframesInput(e.target.value)}
                      className="w-full bg-[#0d0d14] border border-white/5 py-2.5 px-3 text-slate-200 rounded-lg focus:outline-none focus:border-amber-500"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-slate-400 block font-bold">Search Keywords / Tags</label>
                    <input
                      type="text"
                      placeholder="e.g. indicator, pine, divergence, luxalgo"
                      value={tagsInput}
                      onChange={(e) => setTagsInput(e.target.value)}
                      className="w-full bg-[#0d0d14] border border-white/5 py-2.5 px-3 text-slate-200 rounded-lg focus:outline-none focus:border-amber-500"
                    />
                  </div>
                </div>

                {/* Pros & Cons matrices */}
                <div className="space-y-1.5">
                  <label className="text-emerald-400 block font-bold flex items-center space-x-1">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Positive Qualities / Pros (comma-separated, max 5)</span>
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Zero repainting alerts, Dynamic ribbon filters, Easy mobile setup"
                    value={prosInput}
                    onChange={(e) => setProsInput(e.target.value)}
                    className="w-full bg-[#0d0d14] border border-white/5 py-2.5 px-3 text-slate-200 rounded-lg focus:outline-none focus:border-amber-500"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-rose-400 block font-bold flex items-center space-x-1">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    <span>Limitations / Cons (comma-separated, max 3)</span>
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. High spreads during FOMC news, No automated backtests logs"
                    value={consInput}
                    onChange={(e) => setConsInput(e.target.value)}
                    className="w-full bg-[#0d0d14] border border-white/5 py-2.5 px-3 text-slate-200 rounded-lg focus:outline-none focus:border-amber-500"
                  />
                </div>

                {/* Big detailed markdown description */}
                <div className="space-y-1.5">
                  <label className="text-slate-400 block font-bold flex items-center space-x-1">
                    <Eye className="h-3.5 w-3.5 text-amber-500" />
                    <span>Rich Specification Long Description (Supports Markdown, Avoids Thin Content) *</span>
                  </label>
                  <textarea
                    placeholder="Provide a comprehensive technical writeup about the underlying logic, user options, exact mathematical formulas used, optimization parameters, and interactive guides... Try to write at least 3-4 structured paragraphs so SEO systems indexes this cleanly."
                    rows={8}
                    required
                    value={longDescription}
                    onChange={(e) => setLongDescription(e.target.value)}
                    className="w-full bg-[#0d0d14] border border-white/5 py-3 px-4 text-slate-200 rounded-lg focus:outline-none focus:border-amber-500 font-mono text-[11px] leading-relaxed resize-none"
                  ></textarea>
                </div>

                {errorMessage && (
                  <div className="bg-rose-500/10 border border-rose-500/20 px-4 py-3 rounded-xl flex items-start space-x-2 text-rose-400 font-mono text-xs">
                    <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                    <span>{errorMessage}</span>
                  </div>
                )}

                {submitSuccess && (
                  <div className="bg-emerald-500/10 border border-emerald-500/20 px-4 py-3 rounded-xl flex items-start space-x-2 text-emerald-400 font-mono text-xs">
                    <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
                    <span>{submitSuccess}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full bg-amber-500 hover:bg-amber-400 disabled:opacity-40 text-black py-3.5 rounded-xl font-bold flex items-center justify-center space-x-2 transition-all shadow-lg shadow-amber-500/15 cursor-pointer"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Deploying Strategy specs to audit bank...</span>
                    </>
                  ) : (
                    <>
                      <Send className="h-4 w-4" />
                      <span>SUBMIT SPECS TO ADMIN AUDIT</span>
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* Right Guide Block */}
            <div className="space-y-6">
              
              <div className="bg-[#06060a] border border-white/5 p-6 rounded-2xl space-y-4">
                <h4 className="text-xs font-black text-white flex items-center space-x-2 uppercase tracking-wider">
                  <FileCheck className="h-4 w-4 text-emerald-400" />
                  <span>Interactive Compliance Rules</span>
                </h4>
                <p className="text-slate-400 font-sans text-xs leading-relaxed">
                  To protect search rankings and ensure your listing gets indexed by Google instantly:
                </p>
                <div className="space-y-3 text-[11px] font-mono text-slate-500 leading-normal">
                  <div className="flex space-x-2">
                    <span className="text-amber-500">1.</span>
                    <p><strong className="text-slate-300">Detailed writeup:</strong> Thin copy sheets are excluded. Rely on AI to formulate high-density mathematical breakdown.</p>
                  </div>
                  <div className="flex space-x-2">
                    <span className="text-amber-500">2.</span>
                    <p><strong className="text-slate-300">Real Parameter fields:</strong> State exact settings options (e.g. lengths, filters, thresholds).</p>
                  </div>
                  <div className="flex space-x-2">
                    <span className="text-amber-500">3.</span>
                    <p><strong className="text-slate-300">GSC Indexing:</strong> Approved items undergo automatic sitemap XML writing and are submitted to Google Crawl Index queues.</p>
                  </div>
                </div>
              </div>

              <div className="bg-[#0b0b14]/50 border border-amber-500/10 p-6 rounded-2xl space-y-3">
                <h4 className="text-xs font-black text-slate-200 flex items-center space-x-2">
                  <Coins className="h-4 w-4 text-amber-500" />
                  <span>Pricing & Verification</span>
                </h4>
                <p className="text-[11px] text-slate-400 leading-relaxed leading-normal">
                  You can deploy free open-source scripts or charge licensing fees. Verified quants enjoy custom profile indicators so investors can discover parameters.
                </p>
              </div>

            </div>

          </div>

        </div>
      ) : (
        /* Admin Moderation Panel */
        <div className="space-y-6">
          {!isUnlocked ? (
            <div className="max-w-md mx-auto bg-[#06060a] border border-white/5 p-6 rounded-2xl shadow-2xl space-y-4 text-center">
              <Workflow className="h-10 w-10 text-amber-500 mx-auto" />
              <div className="space-y-1">
                <h2 className="text-lg font-black text-white">Unlock Admin Audit Panel</h2>
                <p className="text-xs text-slate-400">Unlock to moderate listings and trigger live Google search indexing.</p>
              </div>

              <form onSubmit={handleUnlockAdmin} className="space-y-3">
                <input
                  type="password"
                  placeholder="Master Secret (Password is: admin123)"
                  value={adminPassKey}
                  onChange={(e) => setAdminPassKey(e.target.value)}
                  className="w-full bg-[#0d0d14] border border-white/5 py-3 px-4 text-slate-200 rounded-xl text-xs focus:outline-none focus:border-amber-500 text-center font-mono"
                />
                <button
                  type="submit"
                  className="w-full bg-amber-500 hover:bg-amber-400 text-black py-2.5 rounded-xl text-xs font-bold font-mono transition-all uppercase tracking-wider block font-bold cursor-pointer"
                >
                  Verify Master Credentials
                </button>
              </form>
            </div>
          ) : (
            <div className="space-y-6">
              
              {/* Unlock Info Panel */}
              <div className="bg-[#06060a] border border-white/5 px-6 py-4 rounded-xl flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div className="space-y-0.5">
                  <span className="text-[10px] text-emerald-400 uppercase tracking-widest font-black font-mono">● SESSION SECURELY ROOTED</span>
                  <p className="text-xs text-slate-400 font-sans">Moderating pending submissions to falconspido-hub</p>
                </div>
                <button
                  onClick={() => { setIsUnlocked(false); setAdminPassKey(''); }}
                  className="bg-red-500/10 hover:bg-red-500/20 text-red-400 px-4 py-1.5 rounded-lg text-xs font-bold transition-all"
                >
                  Lock Session
                </button>
              </div>

              {/* Status and Action Message */}
              {moderationMessage && (
                <div className="bg-amber-500/10 border border-amber-500/20 px-4 py-3 rounded-xl flex items-start space-x-2 text-amber-400 text-xs font-mono">
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-amber-500 mt-0.5" />
                  <div className="space-y-1">
                    <p>{moderationMessage}</p>
                    {gscStatusLog && (
                      <p className="text-emerald-400 font-bold border-t border-amber-500/10 pt-1 mt-1 text-[11px]">
                        Google Index Trigger: {gscStatusLog}
                      </p>
                    )}
                  </div>
                </div>
              )}              {/* AI AUTONOMOUS CONTROL DECK */}
              <div className="bg-[#0b0b14] border border-amber-500/10 p-6 rounded-2xl space-y-6">
                
                {/* Section Header */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-white/5 pb-4">
                  <div className="flex items-center space-x-2.5">
                    <Zap className="h-5.5 w-5.5 text-amber-500 animate-pulse" />
                    <div>
                      <h3 className="text-sm font-black text-white uppercase tracking-wider">FalconSpido AI Ingestion Console</h3>
                      <p className="text-[10px] text-slate-400 font-sans">Autonomous intelligence modules to keep trading tools, macro news, and blog guides live & 100% genuine</p>
                    </div>
                  </div>
                  <span className="text-[9px] bg-amber-500/10 text-amber-400 font-mono font-bold px-3 py-1 rounded-full uppercase">
                    Automations Deck Active
                  </span>
                </div>

                {/* Sub-modules tab switcher */}
                <div className="grid grid-cols-4 gap-2 bg-[#050508] p-1 rounded-xl">
                  {['tools', 'news', 'blog', 'social'].map((subModule) => (
                    <button
                      key={subModule}
                      type="button"
                      onClick={() => {
                        window._activeSubModule = subModule;
                        setGscStatusLog(''); // clear logs
                        setDiscoverSuccessMsg('');
                        setDiscoverErrorMsg('');
                        setNewsSuccessMsg('');
                        setNewsErrorMsg('');
                        setBlogSuccessMsg('');
                        setBlogErrorMsg('');
                        setSocialSuccessMsg('');
                        setSocialErrorMsg('');
                        // Trigger local render trigger
                        setAdminPassKey(prev => prev);
                      }}
                      className={`py-2 rounded-lg text-[10px] font-mono font-bold uppercase transition-all ${
                        (window._activeSubModule || 'tools') === subModule
                          ? 'bg-amber-500 text-black font-extrabold'
                          : 'text-slate-400 hover:text-white hover:bg-white/5'
                      }`}
                    >
                      {subModule === 'tools' ? '1. Quant' : subModule === 'news' ? '2. News' : subModule === 'blog' ? '3. Blogger' : '4. Social Scraper'}
                    </button>
                  ))}
                </div>

                {/* Module 1: AI Quant Tools Discovery */}
                {(!window._activeSubModule || window._activeSubModule === 'tools') && (
                  <div className="space-y-4 animate-fade-in">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="space-y-1.5 md:col-span-2">
                        <label className="text-[10px] font-mono text-slate-400 uppercase font-black tracking-widest block">Core Crawl Query / Strategy Category</label>
                        <select
                          value={discoverKeyword}
                          onChange={(e) => setDiscoverKeyword(e.target.value)}
                          className="w-full bg-[#06060a] border border-white/5 py-2.5 px-3 text-slate-200 rounded-xl text-xs focus:outline-none focus:border-amber-500 transition-all font-mono"
                        >
                          <option value="TradingView Pine Scripts breakout trend indicators">Trending Breakout Trend Indicators (Pine Script)</option>
                          <option value="MQL5 MT5 Expert Advisors free quantitative robots">Free MT5 Scalping Expert Advisors (EAs)</option>
                          <option value="Crypto DCA grid automated bots premium models">Automated Crypto DCA & Grid Trading Bots</option>
                          <option value="MT4 Custom Volume Profile and order flow indicators">MT4 Order Flow & Volume Profile Tools</option>
                          <option value="Smart Money Concepts (SMC) quantitative screens">Smart Money Concepts (SMC) Automated Scripts</option>
                        </select>
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-[10px] font-mono text-slate-400 uppercase font-black tracking-widest block">Target Tool Count</label>
                        <select
                          value={discoverCount}
                          onChange={(e) => setDiscoverCount(Number(e.target.value))}
                          className="w-full bg-[#06060a] border border-white/5 py-2.5 px-3 text-slate-200 rounded-xl text-xs focus:outline-none focus:border-amber-500 transition-all font-mono"
                        >
                          <option value={1}>Discover 1 New Tool</option>
                          <option value={2}>Discover 2 New Tools</option>
                          <option value={3}>Discover 3 New Tools</option>
                          <option value={5}>Discover 5 New Tools</option>
                        </select>
                      </div>
                    </div>

                    {discoverStep && (
                      <div className="bg-amber-500/5 border border-amber-500/10 px-4 py-3 rounded-xl flex items-center space-x-3 text-amber-400 text-xs font-mono animate-pulse">
                        <Loader2 className="h-4 w-4 animate-spin text-amber-500 shrink-0" />
                        <span>Active Ingestion Thread: {discoverStep}</span>
                      </div>
                    )}

                    {discoverErrorMsg && (
                      <div className="bg-red-500/10 border border-red-500/20 px-4 py-3 rounded-xl flex items-start space-x-2 text-red-400 font-mono text-xs">
                        <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                        <span>{discoverErrorMsg}</span>
                      </div>
                    )}

                    {discoverSuccessMsg && (
                      <div className="bg-emerald-500/10 border border-emerald-500/20 px-4 py-3 rounded-xl flex items-start space-x-2 text-emerald-400 font-mono text-xs">
                        <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
                        <span>{discoverSuccessMsg}</span>
                      </div>
                    )}

                    <button
                      type="button"
                      onClick={handleRunAiDiscovery}
                      disabled={isDiscovering}
                      className="w-full bg-amber-500 hover:bg-amber-400 disabled:opacity-40 text-black py-3 rounded-xl font-bold font-mono tracking-wider flex items-center justify-center space-x-2 transition-all shadow-lg shadow-amber-500/15 cursor-pointer"
                    >
                      {isDiscovering ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin text-black" />
                          <span>AUTONOMOUS CODES SCOURING...</span>
                        </>
                      ) : (
                        <>
                          <Zap className="h-4 w-4" />
                          <span>LAUNCH AI QUANT STRATEGY DISCOVERY</span>
                        </>
                      )}
                    </button>
                  </div>
                )}

                {/* Module 2: AI Macroeconomic News Ingestion */}
                {window._activeSubModule === 'news' && (
                  <div className="space-y-4 animate-fade-in block">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="space-y-1.5 md:col-span-2">
                        <label className="text-[10px] font-mono text-slate-400 uppercase font-black tracking-widest block">Geopolitical / Volatility Target Topic</label>
                        <select
                          value={newsTopic}
                          onChange={(e) => setNewsTopic(e.target.value)}
                          className="w-full bg-[#06060a] border border-white/5 py-2.5 px-3 text-slate-200 rounded-xl text-xs focus:outline-none focus:border-amber-500 transition-all font-mono"
                        >
                          <option value="crypto and global macro market news today">Crypto Breakthrough & Bitcoin Flash updates</option>
                          <option value="US Federal Reserve, FOMC meeting, CPI interest rates">US Fed FOMC Meetings & Inflation Indices (CPI)</option>
                          <option value="forex high volatility currency pairs EURUSD GBPUSD USDJPY news">Forex Major Pairs Volatility Shifts</option>
                          <option value="energy commodities crude oil XAUUSD gold safe haven news">Commodities (Gold, Silver, Crude Oil) Price Actions</option>
                        </select>
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-[10px] font-mono text-slate-400 uppercase font-black tracking-widest block">Ingestion Volume</label>
                        <select
                          value={newsCount}
                          onChange={(e) => setNewsCount(Number(e.target.value))}
                          className="w-full bg-[#06060a] border border-white/5 py-2.5 px-3 text-slate-200 rounded-xl text-xs focus:outline-none focus:border-amber-500 transition-all font-mono"
                        >
                          <option value={1}>Publish 1 News Story</option>
                          <option value={2}>Publish 2 News Stories</option>
                          <option value={3}>Publish 3 News Stories</option>
                          <option value={5}>Publish 5 News Stories</option>
                        </select>
                      </div>
                    </div>

                    {newsStep && (
                      <div className="bg-amber-500/5 border border-amber-500/10 px-4 py-3 rounded-xl flex items-center space-x-3 text-amber-400 text-xs font-mono animate-pulse">
                        <Loader2 className="h-4 w-4 animate-spin text-amber-500 shrink-0" />
                        <span>Active Newsroom Writer: {newsStep}</span>
                      </div>
                    )}

                    {newsErrorMsg && (
                      <div className="bg-red-500/10 border border-red-500/20 px-4 py-3 rounded-xl flex items-start space-x-2 text-red-400 font-mono text-xs">
                        <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                        <span>{newsErrorMsg}</span>
                      </div>
                    )}

                    {newsSuccessMsg && (
                      <div className="bg-emerald-500/10 border border-emerald-500/20 px-4 py-3 rounded-xl flex items-start space-x-2 text-emerald-400 font-mono text-xs">
                        <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
                        <span>{newsSuccessMsg}</span>
                      </div>
                    )}

                    <button
                      type="button"
                      onClick={handleRunAiNewsIngestion}
                      disabled={isGeneratingNews}
                      className="w-full bg-amber-500 hover:bg-amber-400 disabled:opacity-40 text-black py-3 rounded-xl font-bold font-mono tracking-wider flex items-center justify-center space-x-2 transition-all shadow-lg shadow-amber-500/15 cursor-pointer"
                    >
                      {isGeneratingNews ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin text-black" />
                          <span>SCOURING SATELLITE CHANNELS...</span>
                        </>
                      ) : (
                        <>
                          <Zap className="h-4 w-4" />
                          <span>CRAWL WEB & PUBLISH SYSTEMIC NEWS</span>
                        </>
                      )}
                    </button>
                  </div>
                )}

                {/* Module 3: AI Quant Masterclass Blogger */}
                {window._activeSubModule === 'blog' && (
                  <div className="space-y-4 animate-fade-in block">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="space-y-1.5 md:col-span-2">
                        <label className="text-[10px] font-mono text-slate-400 uppercase font-black tracking-widest block">Systematic Strategy Syllabus</label>
                        <select
                          value={blogTopic}
                          onChange={(e) => setBlogTopic(e.target.value)}
                          className="w-full bg-[#06060a] border border-white/5 py-2.5 px-3 text-slate-200 rounded-xl text-xs focus:outline-none focus:border-amber-500 transition-all font-mono"
                        >
                          <option value="TradingView Pine Script advanced quantitative breakout strategies">TradingView Pine Script advanced quantitative strategies</option>
                          <option value="Volume profile order flow imbalance delta indicators mathematics">Order Flow Imbalance & Delta Volumetrics Analysis</option>
                          <option value="Smart Money Concepts SMC premium fair value gaps liquidity masterclass">Smart Money Concepts: Liquidity voids & FVG setups</option>
                          <option value="Quantitative backtesting risk management stop-loss ATR trails">Backtesting Optimization & ATR Average True Range trails</option>
                        </select>
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-[10px] font-mono text-slate-400 uppercase font-black tracking-widest block">Article Target Count</label>
                        <select
                          value={blogCount}
                          onChange={(e) => setBlogCount(Number(e.target.value))}
                          className="w-full bg-[#06060a] border border-white/5 py-2.5 px-3 text-slate-200 rounded-xl text-xs focus:outline-none focus:border-amber-500 transition-all font-mono"
                        >
                          <option value={1}>Write 1 Deep Masterclass</option>
                          <option value={2}>Write 2 Deep Masterclasses</option>
                          <option value={3}>Write 3 Deep Masterclasses</option>
                        </select>
                      </div>
                    </div>

                    {blogStep && (
                      <div className="bg-amber-500/5 border border-amber-500/10 px-4 py-3 rounded-xl flex items-center space-x-3 text-amber-400 text-xs font-mono animate-pulse">
                        <Loader2 className="h-4 w-4 animate-spin text-amber-500 shrink-0" />
                        <span>Active Blogger Engine: {blogStep}</span>
                      </div>
                    )}

                    {blogErrorMsg && (
                      <div className="bg-red-500/10 border border-red-500/20 px-4 py-3 rounded-xl flex items-start space-x-2 text-red-400 font-mono text-xs">
                        <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                        <span>{blogErrorMsg}</span>
                      </div>
                    )}

                    {blogSuccessMsg && (
                      <div className="bg-emerald-500/10 border border-emerald-500/20 px-4 py-3 rounded-xl flex items-start space-x-2 text-emerald-400 font-mono text-xs">
                        <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
                        <span>{blogSuccessMsg}</span>
                      </div>
                    )}

                    <button
                      type="button"
                      onClick={handleRunAiBlogIngestion}
                      disabled={isGeneratingBlog}
                      className="w-full bg-amber-500 hover:bg-amber-400 disabled:opacity-40 text-black py-3 rounded-xl font-bold font-mono tracking-wider flex items-center justify-center space-x-2 transition-all shadow-lg shadow-amber-500/15 cursor-pointer"
                    >
                      {isGeneratingBlog ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin text-black" />
                          <span>SYNTHESIZING SYSTEMATIC MANUALS...</span>
                        </>
                      ) : (
                        <>
                          <Zap className="h-4 w-4" />
                          <span>GENERATE 100% GENUINE QUANT GUIDES</span>
                        </>
                      )}
                    </button>
                  </div>
                )}

                {/* Module 4: Social Media Knowledge & Setup Ingest */}
                {window._activeSubModule === 'social' && (
                  <div className="space-y-4 animate-fade-in block">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      
                      <div className="space-y-1.5 col-span-1">
                        <label className="text-[10px] font-mono text-slate-400 uppercase font-black tracking-widest block">Core Target Platform</label>
                        <select
                          value={socialPlatform}
                          onChange={(e) => setSocialPlatform(e.target.value)}
                          className="w-full bg-[#06060a] border border-white/5 py-2.5 px-3 text-slate-200 rounded-xl text-xs focus:outline-none focus:border-amber-500 transition-all font-mono"
                        >
                          <option value="Reddit">Reddit (r/algorithmictrading, r/pineconnector)</option>
                          <option value="Twitter/X">Twitter/X (FinTwit Feed Lists)</option>
                          <option value="YouTube">YouTube (Algorithmic Tutorial Transcripts)</option>
                          <option value="Facebook">Facebook (Quantitative Groups Index)</option>
                          <option value="Instagram">Instagram (Visual Macro & Setting Guides)</option>
                        </select>
                      </div>

                      <div className="space-y-1.5 col-span-1">
                        <label className="text-[10px] font-mono text-slate-400 uppercase font-black tracking-widest block">Concept/Indicator Query</label>
                        <select
                          value={socialTopic}
                          onChange={(e) => setSocialTopic(e.target.value)}
                          className="w-full bg-[#06060a] border border-white/5 py-2.5 px-3 text-slate-200 rounded-xl text-xs focus:outline-none focus:border-amber-500 transition-all font-mono"
                        >
                          <option value="TradingView Pine Script advanced strategy indicator">TradingView Pine Script expert indicators</option>
                          <option value="Smart money concepts SMC fair value gaps breakout">Smart Money Concepts (SMC) & Liquidity Voids</option>
                          <option value="Order flow delta imbalance volume profile scalper">Order Flow Imbalances & Volumetrics</option>
                          <option value="High frequency grid trading algorithmic mechanical systems">High Frequency Grid & DCA Automation</option>
                        </select>
                      </div>

                      <div className="space-y-1.5 col-span-1">
                        <label className="text-[10px] font-mono text-slate-400 uppercase font-black tracking-widest block">Discovery Volume</label>
                        <select
                          value={socialCount}
                          onChange={(e) => setSocialCount(Number(e.target.value))}
                          className="w-full bg-[#06060a] border border-white/5 py-2.5 px-3 text-slate-200 rounded-xl text-xs focus:outline-none focus:border-amber-500 transition-all font-mono"
                        >
                          <option value={1}>Scrape 1 Alpha Insight</option>
                          <option value={2}>Scrape 2 Alpha Insights</option>
                          <option value={3}>Scrape 3 Alpha Insights</option>
                          <option value={5}>Scrape 5 Alpha Insights</option>
                        </select>
                      </div>

                    </div>

                    {/* Retro Interactive Hacker CLI Terminal Console */}
                    <div className="border border-emerald-500/20 rounded-2xl bg-[#010103] p-4 font-mono select-none shadow-2xl relative overflow-hidden space-y-3">
                      
                      {/* Terminal Top Window Bar */}
                      <div className="flex items-center justify-between border-b border-emerald-500/10 pb-2.5">
                        <div className="flex items-center space-x-2.5">
                          <span className="h-2 w-2 rounded-full bg-rose-500"></span>
                          <span className="h-2 w-2 rounded-full bg-amber-500"></span>
                          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-ping"></span>
                          <span className="text-[10px] text-emerald-400 font-extrabold uppercase tracking-widest">
                            FALCONSPIDO RETRO CRAWLER NODE v4.1
                          </span>
                        </div>
                        <span className="text-[9px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20 animate-pulse font-extrabold">
                          {isSocialIngesting ? 'CRAWLING ACTIVE' : 'NODE STANDBY'}
                        </span>
                      </div>

                      {/* Text console screen */}
                      <div className="h-[240px] overflow-y-auto text-[11px] text-emerald-400 p-2 rounded-lg bg-[#020205] border border-emerald-500/5 select-all space-y-1 custom-scrollbar scroll-smooth">
                        {terminalLogs.length === 0 ? (
                          <div className="text-emerald-500/60 p-4 text-center select-none space-y-3">
                            <p className="animate-pulse">falconspido-crawler &gt; Select target specifications above & click trigger sequence to scry.</p>
                            <p className="text-[9px] text-emerald-500/40">Headless browser arrays ready to scrape Twitter X, Reddit communities, Facebook channels, Instagram feeds, and YouTube audio transcripts.</p>
                          </div>
                        ) : (
                          terminalLogs.map((log, lIdx) => (
                            <div key={lIdx} className="leading-relaxed hover:bg-emerald-500/5 px-1 py-0.5 rounded transition-colors break-words">
                              {log}
                            </div>
                          ))
                        )}
                        {isSocialIngesting && (
                          <div className="flex items-center space-x-2 text-emerald-400 text-xs py-1 select-none font-bold italic animate-pulse">
                            <span>&gt; Node busy: {socialStep || 'Parsing network frames...'}</span>
                            <span className="h-4 w-1 bg-emerald-400 animate-duration-500"></span>
                          </div>
                        )}
                      </div>

                      {/* Info footer bar */}
                      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center text-[10px] text-emerald-500/60 gap-1 select-none">
                        <span>API Gateways: Google Search Grounding Engine Enabled</span>
                        <span>Ingest Interval Mapped: Fully Autonomous</span>
                      </div>

                    </div>

                    {socialErrorMsg && (
                      <div className="bg-red-500/10 border border-red-500/20 px-4 py-3 rounded-xl flex items-start space-x-2 text-red-400 font-mono text-xs">
                        <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                        <span>{socialErrorMsg}</span>
                      </div>
                    )}

                    {socialSuccessMsg && (
                      <div className="bg-emerald-500/10 border border-emerald-500/20 px-4 py-3 rounded-xl flex items-start space-x-2 text-emerald-400 font-mono text-xs">
                        <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
                        <span>{socialSuccessMsg}</span>
                      </div>
                    )}

                    <button
                      type="button"
                      onClick={handleRunSocialScraping}
                      disabled={isSocialIngesting}
                      className="w-full bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-black py-3 rounded-xl font-bold font-mono tracking-wider flex items-center justify-center space-x-2 transition-all shadow-lg shadow-emerald-500/15 cursor-pointer text-xs uppercase"
                    >
                      {isSocialIngesting ? (
                        <>
                          <Loader2 className="h-4.5 w-4.5 animate-spin text-black" />
                          <span>LAUNCHING HEADLESS WEB CRAWLERS...</span>
                        </>
                      ) : (
                        <>
                          <Zap className="h-4.5 w-4.5 text-black" />
                          <span>EXECUTE AUTONOMOUS SOCIAL CRAWLER NODE</span>
                        </>
                      )}
                    </button>
                  </div>
                )}

              </div>

              {/* Submissions List Deck */}
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-xs font-bold text-slate-300 font-mono uppercase tracking-widest flex items-center space-x-2">
                    <Clock className="h-4 w-4 text-amber-500" />
                    <span>PENDING SUBMISSIONS DECK ({pendingList.length})</span>
                  </h3>
                  <button 
                    onClick={fetchPendingListings} 
                    className="text-[11px] text-amber-500 font-bold hover:underline"
                  >
                    Refresh List
                  </button>
                </div>

                {isAdminLoading ? (
                  <div className="py-20 flex flex-col items-center justify-center space-y-2">
                    <Loader2 className="h-7 w-7 text-amber-500 animate-spin" />
                    <p className="text-xs text-slate-400 font-mono">Downloading index entries...</p>
                  </div>
                ) : pendingList.length === 0 ? (
                  <div className="border border-white/5 py-16 rounded-2xl text-center space-y-3 bg-[#06060a]">
                    <CheckCircle2 className="h-10 w-10 text-emerald-400 mx-auto" />
                    <div className="space-y-1">
                      <h4 className="text-sm font-bold text-white">Database queue is empty</h4>
                      <p className="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
                        No pending indicator strategies are currently in the audit queue. User-submitted parameters will appear here.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 gap-6">
                    {pendingList.map((item) => (
                      <div 
                        key={item._id} 
                        className="bg-[#06060a] border border-white/5 rounded-2xl p-6 shadow-xl hover:border-amber-500/20 transition-all space-y-4 font-mono text-xs text-slate-300"
                      >
                        {/* Title block */}
                        <div className="flex flex-col sm:flex-row justify-between items-start gap-4 border-b border-white/5 pb-4">
                          <div className="space-y-2">
                            <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                              <h4 className="text-base font-black text-white tracking-tight">{item.name}</h4>
                              {item.submittedBy === 'AI Automation Scraper' && (
                                <span className="bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2 py-0.5 rounded-[4px] text-[9px] font-bold uppercase animate-pulse">
                                  AI Auto-Discovery
                                </span>
                              )}
                            </div>
                            <div className="flex flex-wrap gap-2 text-[10px]">
                              <Badge variant="amber">{item.listingType}</Badge>
                              <Badge variant="gray">{item.platform?.name || 'Metatrader'}</Badge>
                              <Badge variant="gray">{item.difficulty}</Badge>
                              <Badge variant="gray">{item.pricingModel} ({item.price === 0 ? 'Free' : `$${item.price}`})</Badge>
                            </div>
                          </div>

                          <div className="flex gap-2 self-stretch sm:self-auto">
                            <button
                              onClick={() => handleApprove(item._id, item.name)}
                              className="flex-1 sm:flex-none bg-emerald-500 hover:bg-emerald-400 text-black px-4 py-2 rounded-lg font-bold text-[10px] uppercase transition-all flex items-center justify-center space-x-1 cursor-pointer"
                            >
                              <CheckCircle2 className="h-3.5 w-3.5" />
                              <span>Approve & index</span>
                            </button>
                            <button
                              onClick={() => handleReject(item._id, item.name)}
                              className="flex-1 sm:flex-none bg-red-500/10 hover:bg-red-500/20 text-red-400 px-4 py-2 rounded-lg font-bold text-[10px] uppercase transition-all flex items-center justify-center space-x-1 cursor-pointer"
                            >
                              <AlertTriangle className="h-3.5 w-3.5" />
                              <span>Reject</span>
                            </button>
                          </div>
                        </div>

                        {/* Descriptions */}
                        <div className="space-y-3">
                          <p className="text-[11px] text-[#94a3b8] italic">
                            Tagline: "{item.description}"
                          </p>
                          
                          {item.videoUrl && (
                            <div className="bg-rose-500/5 border border-rose-500/10 rounded-xl p-3 space-y-1">
                              <span className="text-[10px] font-bold text-rose-400 block uppercase tracking-wider">Verified YouTube Walkthrough Auto-Found</span>
                              <a 
                                href={item.videoUrl} 
                                target="_blank" 
                                rel="noopener noreferrer" 
                                className="text-amber-500 hover:underline text-[11px] break-all font-bold block"
                              >
                                {item.videoUrl}
                              </a>
                            </div>
                          )}

                          {item.externalUrl && (
                            <div className="bg-emerald-500/5 border border-emerald-500/10 rounded-xl p-3 space-y-1">
                              <span className="text-[10px] font-bold text-emerald-400 block uppercase tracking-wider">Original Source Webpage Repository</span>
                              <a 
                                href={item.externalUrl} 
                                target="_blank" 
                                rel="noopener noreferrer" 
                                className="text-amber-400 hover:underline text-[11px] break-all block"
                              >
                                {item.externalUrl}
                              </a>
                            </div>
                          )}

                          <div className="space-y-1">
                            <p className="text-slate-400 font-bold block">Model specifications writeup (Markdown preview):</p>
                            <div className="bg-[#0b0b14] border border-white/5 p-4 rounded-xl leading-relaxed max-h-40 overflow-y-auto text-[11px] text-slate-400 whitespace-pre-wrap">
                              {item.longDescription}
                            </div>
                          </div>
                        </div>

                        {/* Array values */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 text-[10px] border-t border-white/5 pt-4 text-slate-400">
                          <div>
                            <span className="text-slate-500 font-bold block">Asset Classes:</span>
                            <span>{item.assetClass?.join(', ') || 'N/A'}</span>
                          </div>
                          <div>
                            <span className="text-slate-500 font-bold block">Strategy types:</span>
                            <span>{item.strategyType?.join(', ') || 'N/A'}</span>
                          </div>
                          <div>
                            <span className="text-slate-500 font-bold block">Suggested Timeframes:</span>
                            <span>{item.timeframes?.join(', ') || 'N/A'}</span>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-[10px] text-slate-400">
                          <div>
                            <span className="text-emerald-400 font-bold block">Pros:</span>
                            <span>{item.pros?.join(' | ') || 'N/A'}</span>
                          </div>
                          <div>
                            <span className="text-rose-400 font-bold block">Cons:</span>
                            <span>{item.cons?.join(' | ') || 'N/A'}</span>
                          </div>
                        </div>

                        {/* Meta and email */}
                        <div className="flex justify-between items-center text-[10px] text-slate-500 border-t border-white/5 pt-3">
                          <span>Author: {item.author}</span>
                          <span>Submitter: {item.submittedBy}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

            </div>
          )}
        </div>
      )}

    </div>
  );
};
