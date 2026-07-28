import express from 'express';
import { getLivePrices, getSymbolCandles } from '../controllers/marketDataController.js';
import { getMarketScreener } from '../controllers/screenerController.js';
import { getMarketNews, getSingleNews, createNewsStory, runAiNewsIngestion } from '../controllers/newsController.js';
import { handleTradingViewWebhook } from '../controllers/webhookController.js';
import { getIndicatorPresets, submitPreset, votePreset } from '../controllers/presetController.js';
import { getBacktestReports, submitBacktestReport } from '../controllers/backtestReportController.js';
import { getMacroCalendar, createMacroEvent } from '../controllers/macroController.js';
import { calculatePositionSize, calculateDcaGrid } from '../controllers/calculatorController.js';
import {
  getIndicators,
  getTrending,
  getNewest,
  getFeatured,
  getTopRated,
  getFreeTools,
  getByListingType,
  getByAsset,
  getByPlatform,
  getByStrategy,
  getSimilar,
  getOne as getIndicatorBySlug,
  createIndicator,
  updateIndicator,
  incrementView,
  toggleLike,
  flagScam,
  compareIndicators,
  getStats
} from '../controllers/indicatorController.js';

import {
  getReviewsByIndicator,
  createReview,
  markHelpful,
  markNotHelpful
} from '../controllers/reviewController.js';

import {
  getAll as getCategories,
  getOne as getCategory,
  getIndicatorsByCategory
} from '../controllers/categoryController.js';

import {
  getAll as getPlatforms,
  getOne as getPlatform,
  getIndicatorsByPlatform
} from '../controllers/platformController.js';

import {
  getAll as getSignals,
  getOne as getSignal,
  create as createSignal
} from '../controllers/signalController.js';

import {
  getAll as getBrokers,
  getFeatured as getFeaturedBrokers,
  getOne as getBroker
} from '../controllers/brokerController.js';

import {
  submitListing,
  getSubmissions,
  extractDetails,
  getPendingListings,
  approveListing,
  rejectListing,
  runAiDiscovery
} from '../controllers/submitController.js';

import {
  registerUser,
  authUser,
  getUserProfile
} from '../controllers/authController.js';

import { protect, admin } from '../middleware/authMiddleware.js';
import { getSocialInsights, runSocialScraping } from '../controllers/socialScraperController.js';

import {
  getAll as getBlogPosts,
  getFeatured as getFeaturedBlogPosts,
  getOne as getBlogPost,
  create as createBlogPost,
  runAiBlogIngestion
} from '../controllers/blogController.js';

import validateFields from '../middleware/validate.js';

const router = express.Router();

// ━━━━━━━━━━━━━━━━━━━━━━━━
// 1. INDICATORS ROUTES
// ━━━━━━━━━━━━━━━━━━━━━━━━
router.get('/indicators/trending', getTrending);
router.get('/indicators/new', getNewest);
router.get('/indicators/featured', getFeatured);
router.get('/indicators/top-rated', getTopRated);
router.get('/indicators/free', getFreeTools);
router.get('/indicators/compare', compareIndicators);
router.get('/indicators/stats', getStats);
router.get('/indicators/type/:listingType', getByListingType);
router.get('/indicators/asset/:assetClass', getByAsset);
router.get('/indicators/platform/:platformSlug', getByPlatform);
router.get('/indicators/strategy/:strategyType', getByStrategy);
router.get('/indicators/:slug/similar', getSimilar);
router.get('/indicators/:slug', getIndicatorBySlug);

router.get('/indicators', getIndicators);
router.post('/indicators', validateFields(['name', 'listingType', 'category', 'platform', 'description', 'longDescription', 'author', 'submittedBy']), createIndicator);
router.put('/indicators/:id', updateIndicator);

router.patch('/indicators/:id/view', incrementView);
router.patch('/indicators/:id/like', toggleLike);
router.patch('/indicators/:id/flag-scam', flagScam);

// ━━━━━━━━━━━━━━━━━━━━━━━━
// 2. REVIEWS ROUTES
// ━━━━━━━━━━━━━━━━━━━━━━━━
router.get('/reviews/indicator/:indicatorId', getReviewsByIndicator);
router.post('/reviews', validateFields(['indicatorId', 'reviewerName', 'rating', 'title', 'body']), createReview);
router.patch('/reviews/:id/helpful', markHelpful);
router.patch('/reviews/:id/not-helpful', markNotHelpful);

// ━━━━━━━━━━━━━━━━━━━━━━━━
// 3. CATEGORIES ROUTES
// ━━━━━━━━━━━━━━━━━━━━━━━━
router.get('/categories', getCategories);
router.get('/categories/:slug', getCategory);
router.get('/categories/:slug/indicators', getIndicatorsByCategory);

// ━━━━━━━━━━━━━━━━━━━━━━━━
// 4. PLATFORMS ROUTES
// ━━━━━━━━━━━━━━━━━━━━━━━━
router.get('/platforms', getPlatforms);
router.get('/platforms/:slug', getPlatform);
router.get('/platforms/:slug/indicators', getIndicatorsByPlatform);

// ━━━━━━━━━━━━━━━━━━━━━━━━
// 5. SIGNALS ROUTES
// ━━━━━━━━━━━━━━━━━━━━━━━━
router.get('/signals', getSignals);
router.get('/signals/:id', getSignal);
router.post('/signals', validateFields(['name', 'provider', 'asset', 'direction', 'entry', 'stopLoss', 'takeProfit1', 'timeframe']), createSignal);

// ━━━━━━━━━━━━━━━━━━━━━━━━
// 6. BROKERS ROUTES
// ━━━━━━━━━━━━━━━━━━━━━━━━
router.get('/brokers/featured', getFeaturedBrokers);
router.get('/brokers', getBrokers);
router.get('/brokers/:slug', getBroker);

// ━━━━━━━━━━━━━━━━━━━━━━━━
// 7. MERCHANT SUBMISSION ROUTES
// ━━━━━━━━━━━━━━━━━━━━━━━━
router.post('/submit', validateFields(['submitterName', 'submitterEmail', 'toolName', 'toolUrl', 'listingType', 'platform', 'description']), submitListing);
router.get('/submit/all', getSubmissions);

// AI Scraper metadata extraction
router.post('/ai/extract', extractDetails);

// User Authentication API endpoints
router.post('/auth/register', validateFields(['name', 'email', 'password']), registerUser);
router.post('/auth/login', validateFields(['email', 'password']), authUser);
router.get('/auth/profile', protect, getUserProfile);

// Admin listings moderation decks with JWT identity guard
router.get('/admin/submissions', protect, admin, getPendingListings);
router.put('/admin/submissions/:id/approve', protect, admin, approveListing);
router.put('/admin/submissions/:id/reject', protect, admin, rejectListing);
router.post('/admin/automation/discover', protect, admin, runAiDiscovery);
router.post('/admin/automation/generate-news', protect, admin, runAiNewsIngestion);
router.post('/admin/automation/generate-blog', protect, admin, runAiBlogIngestion);
router.post('/admin/automation/social-ingest', protect, admin, runSocialScraping);
router.get('/social-insights', getSocialInsights);

// ━━━━━━━━━━━━━━━━━━━━━━━━
// 8. BLOG POSTS ROUTES
// ━━━━━━━━━━━━━━━━━━━━━━━━
router.get('/blog/featured', getFeaturedBlogPosts);
router.get('/blog', getBlogPosts);
router.get('/blog/:slug', getBlogPost);
router.post('/blog', validateFields(['title', 'excerpt', 'content', 'category']), createBlogPost);

// ━━━━━━━━━━━━━━━━━━━━━━━━
// 9. MARKET DATA ROUTES
// ━━━━━━━━━━━━━━━━━━━━━━━━
router.get('/market-data/prices', getLivePrices);
router.get('/market-data/candles/:symbol', getSymbolCandles);

// ━━━━━━━━━━━━━━━━━━━━━━━━
// 10. TECHNICAL SCREENER ROUTES
// ━━━━━━━━━━━━━━━━━━━━━━━━
router.get('/screener', getMarketScreener);

// ━━━━━━━━━━━━━━━━━━━━━━━━
// 11. GLOBAL MARKET NEWS ROUTES
// ━━━━━━━━━━━━━━━━━━━━━━━━
router.get('/news', getMarketNews);
router.get('/news/:slug', getSingleNews);
router.post('/news', validateFields(['title', 'summary', 'content']), createNewsStory);

// ━━━━━━━━━━━━━━━━━━━━━━━━
// 12. AUTOMATION WEBHOOK ROUTES
// ━━━━━━━━━━━━━━━━━━━━━━━━
router.post('/webhook/tradingview', handleTradingViewWebhook);

// ━━━━━━━━━━━━━━━━━━━━━━━━
// 13. OPTIMIZATION PRESET ROUTES
// ━━━━━━━━━━━━━━━━━━━━━━━━
router.get('/presets/indicator/:indicatorId', getIndicatorPresets);
router.post('/presets', validateFields(['indicatorId', 'title', 'assetClass', 'symbol', 'timeframe', 'parameters']), submitPreset);
router.patch('/presets/:id/vote', votePreset);

// ━━━━━━━━━━━━━━━━━━━━━━━━
// 14. COMMUNITY BACKTEST AUDIT ROUTES
// ━━━━━━━━━━━━━━━━━━━━━━━━
router.get('/backtest-reports/indicator/:indicatorId', getBacktestReports);
router.post('/backtest-reports', validateFields(['indicatorId', 'testerName', 'timeframe', 'marketSymbol', 'testPeriod', 'metrics', 'dataSource']), submitBacktestReport);

// ━━━━━━━━━━━━━━━━━━━━━━━━
// 15. MACRO ECONOMIC CALENDAR ROUTES
// ━━━━━━━━━━━━━━━━━━━━━━━━
router.get('/macro-calendar', getMacroCalendar);
router.post('/macro-calendar', validateFields(['title', 'impact', 'currencyAffected', 'eventTime']), createMacroEvent);

// ━━━━━━━━━━━━━━━━━━━━━━━━
// 16. ADVANCED MATHEMATICAL RISK CALCULATORS
// ━━━━━━━━━━━━━━━━━━━━━━━━
router.post('/calculator/position-size', calculatePositionSize);
router.post('/calculator/dca-presets', calculateDcaGrid);

export default router;
