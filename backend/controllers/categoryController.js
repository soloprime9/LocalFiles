import asyncHandler from 'express-async-handler';
import { Category, Indicator } from '../models/index.js';

/**
 * @desc    Get all active categories with dynamically integrated item counts
 * @route   GET /api/v1/categories
 * @access  Public
 */
export const getAll = asyncHandler(async (req, res) => {
  const categories = await Category.find({ isActive: true }).sort({ sortOrder: 1 });

  // Dynamically calculate actual active item count in directory for each category
  const hydratedCategories = await Promise.all(
    categories.map(async (cat) => {
      const liveCount = await Indicator.countDocuments({ category: cat._id, status: 'active', isScamFlagged: { $ne: true } });
      const plainCat = cat.toObject();
      plainCat.itemCount = liveCount;
      return plainCat;
    })
  );

  res.status(200).json({ success: true, data: hydratedCategories });
});

/**
 * @desc    Get single category by slug
 * @route   GET /api/v1/categories/:slug
 * @access  Public
 */
export const getOne = asyncHandler(async (req, res) => {
  const catObj = await Category.findOne({ slug: req.params.slug });
  if (!catObj) {
    return res.status(404).json({ success: false, error: 'Category not found' });
  }

  const liveCount = await Indicator.countDocuments({ category: catObj._id, status: 'active', isScamFlagged: { $ne: true } });
  const categoryWithCount = catObj.toObject();
  categoryWithCount.itemCount = liveCount;

  res.status(200).json({ success: true, data: categoryWithCount });
});

/**
 * @desc    Get indicators mapped to this category (paginated)
 * @route   GET /api/v1/categories/:slug/indicators
 * @access  Public
 */
export const getIndicatorsByCategory = asyncHandler(async (req, res) => {
  const catObj = await Category.findOne({ slug: req.params.slug });
  if (!catObj) {
    return res.status(404).json({ success: false, error: 'Category not found' });
  }

  const { page = 1, limit = 12 } = req.query;
  const skip = (parseInt(page) - 1) * parseInt(limit);

  const query = { category: catObj._id, status: 'active', isScamFlagged: { $ne: true } };

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
