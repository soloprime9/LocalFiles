import asyncHandler from 'express-async-handler';
import { Indicator, Category, Platform, Review } from '../models/index.js';

// Calculate trending score dynamically based on weekly views, likes, and total community feedback reviews.
const calculateTrendingScore = (ind) => {
  const viewsWeight = (ind.weeklyViews || 0) * 0.4;
  const likesWeight = (ind.weeklyLikes || 0) * 0.4;
  const reviewsWeight = (ind.totalReviews || 0) * 0.2;
  const score = viewsWeight + likesWeight + reviewsWeight;
  // Normalize score between 0 and 100
  return Math.min(100, Math.max(0, Math.round(score)));
};

/**
 * @desc    Get all indicators with advanced filtering, full text search, sorting, and pagination
 * @route   GET /api/v1/indicators
 * @access  Public
 */
export const getIndicators = asyncHandler(async (req, res) => {
  const {
    platform,
    category,
    listingType,
    assetClass,
    strategyType,
    timeframe,
    difficulty,
    isFree,
    minRating,
    minWinRate,
    search,
    sort,
    page = 1,
    limit = 12,
    isVerified,
    isFeatured,
    excludeScam = 'true'
  } = req.query;

  const query = {};

  // Default filter to ignore pending/rejected items
  query.status = 'active';

  // Exclude scam flagged items by default
  if (excludeScam === 'true') {
    query.isScamFlagged = { $ne: true };
  }

  // Exact matches
  if (platform) query.platform = platform;
  if (category) query.category = category;
  if (listingType) query.listingType = listingType;
  if (difficulty) query.difficulty = difficulty;
  
  if (isVerified === 'true') query.isVerified = true;
  if (isFeatured === 'true') query.isFeatured = true;

  // Boolean toggling
  if (isFree === 'true') {
    query.price = 0;
  }

  // Multi-select matches (asset classes or strategy types via comma separation)
  if (assetClass) {
    const assets = assetClass.split(',');
    query.assetClass = { $in: assets };
  }

  if (strategyType) {
    const strategies = strategyType.split(',');
    query.strategyType = { $in: strategies };
  }

  if (timeframe) {
    query.timeframes = timeframe;
  }

  // Logical operators & ranges
  if (minRating) {
    query.rating = { $gte: parseFloat(minRating) };
  }

  if (minWinRate) {
    query['backtestData.winRate'] = { $gte: parseFloat(minWinRate) };
  }

  // Text search on Index
  if (search) {
    query.$text = { $search: search };
  }

  // Sorting mechanism
  let sortBy = { isFeatured: -1, trendingScore: -1 }; // default sorting
  if (sort) {
    switch (sort) {
      case 'newest':
        sortBy = { createdAt: -1 };
        break;
      case 'top_rated':
        sortBy = { rating: -1, totalReviews: -1 };
        break;
      case 'most_reviewed':
        sortBy = { totalReviews: -1 };
        break;
      case 'price_asc':
        sortBy = { price: 1 };
        break;
      case 'price_desc':
        sortBy = { price: -1 };
        break;
      case 'trust_score':
        sortBy = { trustScore: -1 };
        break;
      case 'trending':
      default:
        sortBy = { trendingScore: -1 };
        break;
    }
  }

  // Pagination details
  const skip = (parseInt(page) - 1) * parseInt(limit);

  // Executing database call
  const total = await Indicator.countDocuments(query);
  const items = await Indicator.find(query)
    .populate('category', 'name icon color')
    .populate('platform', 'name logo affiliateUrl')
    .sort(sortBy)
    .skip(skip)
    .limit(parseInt(limit));

  res.status(200).json({
    success: true,
    data: items,
    total,
    page: parseInt(page),
    pages: Math.ceil(total / parseInt(limit)),
    filters_applied: Object.keys(query).filter(k => k !== 'status' && k !== 'isScamFlagged')
  });
});

/**
 * @desc    Get top 10 trending items this week
 * @route   GET /api/v1/indicators/trending
 * @access  Public
 */
export const getTrending = asyncHandler(async (req, res) => {
  const items = await Indicator.find({ status: 'active', isScamFlagged: { $ne: true } })
    .populate('category', 'name icon color')
    .populate('platform', 'name logo')
    .sort({ trendingScore: -1 })
    .limit(10);

  res.status(200).json({ success: true, data: items });
});

/**
 * @desc    Get top 12 newest active listings
 * @route   GET /api/v1/indicators/new
 * @access  Public
 */
export const getNewest = asyncHandler(async (req, res) => {
  const items = await Indicator.find({ status: 'active', isScamFlagged: { $ne: true } })
    .populate('category', 'name icon color')
    .populate('platform', 'name logo')
    .sort({ createdAt: -1 })
    .limit(12);

  res.status(200).json({ success: true, data: items });
});

/**
 * @desc    Get all featured listings sorted by trending prominence
 * @route   GET /api/v1/indicators/featured
 * @access  Public
 */
export const getFeatured = asyncHandler(async (req, res) => {
  const items = await Indicator.find({ isFeatured: true, status: 'active', isScamFlagged: { $ne: true } })
    .populate('category', 'name icon color')
    .populate('platform', 'name logo')
    .sort({ trendingScore: -1 });

  res.status(200).json({ success: true, data: items });
});

/**
 * @desc    Get top rated items (must have at least 3 reviews to qualify)
 * @route   GET /api/v1/indicators/top-rated
 * @access  Public
 */
export const getTopRated = asyncHandler(async (req, res) => {
  const items = await Indicator.find({
    status: 'active',
    isScamFlagged: { $ne: true },
    totalReviews: { $gte: 3 }
  })
    .populate('category', 'name icon color')
    .populate('platform', 'name logo')
    .sort({ rating: -1, totalReviews: -1 })
    .limit(12);

  res.status(200).json({ success: true, data: items });
});

/**
 * @desc    Get free indicators & tools
 * @route   GET /api/v1/indicators/free
 * @access  Public
 */
export const getFreeTools = asyncHandler(async (req, res) => {
  const items = await Indicator.find({ price: 0, status: 'active', isScamFlagged: { $ne: true } })
    .populate('category', 'name icon color')
    .populate('platform', 'name logo')
    .sort({ rating: -1, trendingScore: -1 })
    .limit(12);

  res.status(200).json({ success: true, data: items });
});

/**
 * @desc    Filter tools by listing type
 * @route   GET /api/v1/indicators/type/:listingType
 * @access  Public
 */
export const getByListingType = asyncHandler(async (req, res) => {
  const { listingType } = req.params;
  const items = await Indicator.find({ listingType, status: 'active', isScamFlagged: { $ne: true } })
    .populate('category', 'name icon color')
    .populate('platform', 'name logo')
    .sort({ trendingScore: -1 });

  res.status(200).json({ success: true, data: items });
});

/**
 * @desc    Filter by asset class (Crypto, Gold, Forex, etc.)
 * @route   GET /api/v1/indicators/asset/:assetClass
 * @access  Public
 */
export const getByAsset = asyncHandler(async (req, res) => {
  const { assetClass } = req.params;
  // Proper capitalization match
  const normalizedAsset = assetClass.charAt(0).toUpperCase() + assetClass.slice(1).toLowerCase();

  const items = await Indicator.find({ assetClass: normalizedAsset, status: 'active', isScamFlagged: { $ne: true } })
    .populate('category', 'name icon color')
    .populate('platform', 'name logo')
    .sort({ trendingScore: -1 });

  res.status(200).json({ success: true, data: items, asset: normalizedAsset });
});

/**
 * @desc    Get indicators by platform slug
 * @route   GET /api/v1/indicators/platform/:platformSlug
 * @access  Public
 */
export const getByPlatform = asyncHandler(async (req, res) => {
  const { platformSlug } = req.params;
  
  const platformObj = await Platform.findOne({ slug: platformSlug });
  if (!platformObj) {
    return res.status(404).json({ success: false, error: 'Platform not found' });
  }

  const items = await Indicator.find({ platform: platformObj._id, status: 'active', isScamFlagged: { $ne: true } })
    .populate('category', 'name icon color')
    .populate('platform', 'name logo')
    .sort({ trendingScore: -1 });

  res.status(200).json({ success: true, data: items, platform: platformObj });
});

/**
 * @desc    Get indicators by strategy type
 * @route   GET /api/v1/indicators/strategy/:strategyType
 * @access  Public
 */
export const getByStrategy = asyncHandler(async (req, res) => {
  const { strategyType } = req.params;
  const normalizedStrategy = strategyType.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');

  const items = await Indicator.find({ strategyType: normalizedStrategy, status: 'active', isScamFlagged: { $ne: true } })
    .populate('category', 'name icon color')
    .populate('platform', 'name logo')
    .sort({ trendingScore: -1 });

  res.status(200).json({ success: true, data: items, strategy: normalizedStrategy });
});

/**
 * @desc    Retrieve similar indicators (same category, matching asset overlays)
 * @route   GET /api/v1/indicators/:slug/similar
 * @access  Public
 */
export const getSimilar = asyncHandler(async (req, res) => {
  const { slug } = req.params;
  const current = await Indicator.findOne({ slug });
  if (!current) {
    return res.status(404).json({ success: false, error: 'Indicator not found' });
  }

  const items = await Indicator.find({
    _id: { $ne: current._id },
    category: current.category,
    assetClass: { $in: current.assetClass },
    status: 'active',
    isScamFlagged: { $ne: true }
  })
    .populate('category', 'name icon color')
    .populate('platform', 'name logo')
    .limit(6);

  res.status(200).json({ success: true, data: items });
});

/**
 * @desc    Get single indicator details (increments view count and fetches 5 helpful reviews)
 * @route   GET /api/v1/indicators/:slug
 * @access  Public
 */
export const getOne = asyncHandler(async (req, res) => {
  const { slug } = req.params;
  const item = await Indicator.findOne({ slug })
    .populate('category', 'name icon color description')
    .populate('platform', 'name logo description affiliateUrl indicatorLanguage');

  if (!item) {
    return res.status(404).json({ success: false, error: 'Trading tool not found' });
  }

  // Increment view telemetry asynchronously
  item.totalViews += 1;
  item.weeklyViews += 1;
  item.trendingScore = calculateTrendingScore(item);
  await item.save();

  // Load contextual top helpful reviews
  const reviews = await Review.find({ indicatorId: item._id })
    .sort({ helpful: -1, createdAt: -1 })
    .limit(5);

  res.status(200).json({
    success: true,
    data: item,
    reviews
  });
});

/**
 * @desc    Submit of indicator to database
 * @route   POST /api/v1/indicators
 * @access  Public (unprotected or admin validated depending on environment)
 */
export const createIndicator = asyncHandler(async (req, res) => {
  const newItem = await Indicator.create(req.body);
  res.status(201).json({ success: true, data: newItem });
});

/**
 * @desc    Modify specific listings
 * @route   PUT /api/v1/indicators/:id
 * @access  Public (admin)
 */
export const updateIndicator = asyncHandler(async (req, res) => {
  const updated = await Indicator.findByIdAndUpdate(req.params.id, req.body, {
    new: true,
    runValidators: true
  });

  if (!updated) {
    return res.status(404).json({ success: false, error: 'Indicator index not found' });
  }

  res.status(200).json({ success: true, data: updated });
});

/**
 * @desc    Increment listing views, recalculate dynamic analytics
 * @route   PATCH /api/v1/indicators/:id/view
 * @access  Public
 */
export const incrementView = asyncHandler(async (req, res) => {
  const item = await Indicator.findById(req.params.id);
  if (!item) {
    return res.status(404).json({ success: false, error: 'Indicator not found' });
  }

  item.totalViews += 1;
  item.weeklyViews += 1;
  item.trendingScore = calculateTrendingScore(item);
  await item.save();

  res.status(200).json({ success: true, totalViews: item.totalViews, trendingScore: item.trendingScore });
});

/**
 * @desc    Safeguard likes and increment trending weight
 * @route   PATCH /api/v1/indicators/:id/like
 * @access  Public
 */
export const toggleLike = asyncHandler(async (req, res) => {
  const item = await Indicator.findById(req.params.id);
  if (!item) {
    return res.status(404).json({ success: false, error: 'Indicator not found' });
  }

  item.totalLikes += 1;
  item.weeklyLikes += 1;
  item.trendingScore = calculateTrendingScore(item);
  await item.save();

  res.status(200).json({ success: true, totalLikes: item.totalLikes, trendingScore: item.trendingScore });
});

/**
 * @desc    Flag a listing as scam / curve-fitted
 * @route   PATCH /api/v1/indicators/:id/flag-scam
 * @access  Public (Community moderated)
 */
export const flagScam = asyncHandler(async (req, res) => {
  const { reason } = req.body;
  if (!reason) {
    return res.status(400).json({ success: false, error: 'Please explain the reason for flag report' });
  }

  const item = await Indicator.findById(req.params.id);
  if (!item) {
    return res.status(404).json({ success: false, error: 'Indicator not found' });
  }

  item.isScamFlagged = true;
  item.scamReason = reason;
  // Saving the document will re-trigger the pre('save') hook, reducing TrustScore instantly.
  await item.save();

  res.status(200).json({ success: true, message: 'Tool successfully flag-reported', trustScore: item.trustScore });
});

/**
 * @desc    Perform comprehensive compare mapping on up to 3 indicator items
 * @route   GET /api/v1/indicators/compare
 * @access  Public
 */
export const compareIndicators = asyncHandler(async (req, res) => {
  const { ids } = req.query;
  if (!ids) {
    return res.status(400).json({ success: false, error: 'Please supply indicator IDs to compare' });
  }

  const comparingIds = ids.split(',').slice(0, 3); // Capped at exactly 3
  const items = await Indicator.find({ _id: { $in: comparingIds } })
    .populate('category', 'name icon')
    .populate('platform', 'name logo');

  res.status(200).json({ success: true, data: items });
});

/**
 * @desc    Get high-level summary overview metrics for Directory Frontpage
 * @route   GET /api/v1/indicators/stats
 * @access  Public
 */
export const getStats = asyncHandler(async (req, res) => {
  const totalIndicators = await Indicator.countDocuments({ status: 'active' });
  const totalFree = await Indicator.countDocuments({ price: 0, status: 'active' });
  const totalPaid = await Indicator.countDocuments({ price: { $gt: 0 }, status: 'active' });
  const totalVerified = await Indicator.countDocuments({ isVerified: true, status: 'active' });

  // Metrics breakdowns
  const byPlatform = await Indicator.aggregate([
    { $match: { status: 'active' } },
    { $group: { _id: '$platform', count: { $sum: 1 } } }
  ]);

  const byCategory = await Indicator.aggregate([
    { $match: { status: 'active' } },
    { $group: { _id: '$category', count: { $sum: 1 } } }
  ]);

  const byListingType = await Indicator.aggregate([
    { $match: { status: 'active' } },
    { $group: { _id: '$listingType', count: { $sum: 1 } } }
  ]);

  const ratingAvg = await Indicator.aggregate([
    { $match: { status: 'active', totalReviews: { $gt: 0 } } },
    { $group: { _id: null, avg: { $avg: '$rating' } } }
  ]);

  res.status(200).json({
    success: true,
    totalIndicators,
    totalFree,
    totalPaid,
    totalVerified,
    byPlatform,
    byCategory,
    byListingType,
    avgRating: ratingAvg.length > 0 ? Math.round(ratingAvg[0].avg * 10) / 10 : 4.5
  });
});
