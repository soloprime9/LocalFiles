import asyncHandler from 'express-async-handler';
import { Platform, Indicator } from '../models/index.js';

/**
 * @desc    Get all active platforms sorted by priority
 * @route   GET /api/v1/platforms
 * @access  Public
 */
export const getAll = asyncHandler(async (req, res) => {
  const platforms = await Platform.find({ isActive: true }).sort({ priority: 1, name: 1 });

  // dynamically integrate live directory item counts
  const hydratedPlatforms = await Promise.all(
    platforms.map(async (plat) => {
      const liveCount = await Indicator.countDocuments({ platform: plat._id, status: 'active', isScamFlagged: { $ne: true } });
      const plainPlat = plat.toObject();
      plainPlat.itemCount = liveCount;
      return plainPlat;
    })
  );

  res.status(200).json({ success: true, data: hydratedPlatforms });
});

/**
 * @desc    Get platform by slug
 * @route   GET /api/v1/platforms/:slug
 * @access  Public
 */
export const getOne = asyncHandler(async (req, res) => {
  const platObj = await Platform.findOne({ slug: req.params.slug });
  if (!platObj) {
    return res.status(404).json({ success: false, error: 'Platform not found' });
  }

  const liveCount = await Indicator.countDocuments({ platform: platObj._id, status: 'active', isScamFlagged: { $ne: true } });
  const platformWithCount = platObj.toObject();
  platformWithCount.itemCount = liveCount;

  res.status(200).json({ success: true, data: platformWithCount });
});

/**
 * @desc    Get indicator listings for a platform (paginated)
 * @route   GET /api/v1/platforms/:slug/indicators
 * @access  Public
 */
export const getIndicatorsByPlatform = asyncHandler(async (req, res) => {
  const platObj = await Platform.findOne({ slug: req.params.slug });
  if (!platObj) {
    return res.status(404).json({ success: false, error: 'Platform not found' });
  }

  const { page = 1, limit = 12 } = req.query;
  const skip = (parseInt(page) - 1) * parseInt(limit);

  const query = { platform: platObj._id, status: 'active', isScamFlagged: { $ne: true } };

  const total = await Indicator.countDocuments(query);
  const items = await Indicator.find(query)
    .populate('category', 'name icon color')
    .populate('platform', 'name logo')
    .sort({ isFeatured: -1, trendingScore: -1 })
    .skip(skip)
    .limit(parseInt(limit));

  res.status(200).json({
    success: true,
    data: items,
    total,
    page: parseInt(page),
    pages: Math.ceil(total / parseInt(limit))
  });
});
