import asyncHandler from 'express-async-handler';
import { BrokerAffiliate } from '../models/index.js';

/**
 * @desc    Get all brokers with query parameters (asset, deposit ceilings, featured)
 * @route   GET /api/v1/brokers
 * @access  Public
 */
export const getAll = asyncHandler(async (req, res) => {
  const { assetsCovered, minDepositMax, isFeatured, sort } = req.query;
  const filter = {};

  if (assetsCovered) {
    filter.assetsCovered = assetsCovered;
  }

  if (minDepositMax) {
    filter.minDeposit = { $lte: parseFloat(minDepositMax) };
  }

  if (isFeatured === 'true') {
    filter.isFeatured = true;
  }

  // Sorting
  let sortBy = { isRecommended: -1, rating: -1 };
  if (sort) {
    if (sort === 'rating') {
      sortBy = { rating: -1 };
    } else if (sort === 'commission') {
      sortBy = { cpaCommission: -1, revenueShare: -1 };
    } else if (sort === 'deposit_low') {
      sortBy = { minDeposit: 1 };
    }
  }

  const items = await BrokerAffiliate.find(filter).sort(sortBy);

  res.status(200).json({ success: true, data: items });
});

/**
 * @desc    Get broker by slug
 * @route   GET /api/v1/brokers/:slug
 * @access  Public
 */
export const getOne = asyncHandler(async (req, res) => {
  const brokerObj = await BrokerAffiliate.findOne({ slug: req.params.slug });
  if (!brokerObj) {
    return res.status(404).json({ success: false, error: 'Broker not found' });
  }

  res.status(200).json({ success: true, data: brokerObj });
});

/**
 * @desc    Get featured brokers to place on panels
 * @route   GET /api/v1/brokers/featured
 * @access  Public
 */
export const getFeatured = asyncHandler(async (req, res) => {
  const items = await BrokerAffiliate.find({ isFeatured: true }).sort({ rating: -1 });
  res.status(200).json({ success: true, data: items });
});
