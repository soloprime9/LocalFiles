import asyncHandler from 'express-async-handler';
import ConfigPreset from '../models/ConfigPreset.js';

/**
 * @desc    Get indicator-specific custom presets (Shared setting layouts)
 * @route   GET /api/v1/presets/indicator/:indicatorId
 * @access  Public
 */
export const getIndicatorPresets = asyncHandler(async (req, res) => {
  const { indicatorId } = req.params;
  const { symbol, timeframe, sort } = req.query;

  const query = { indicatorId };
  if (symbol) query.symbol = symbol.toUpperCase();
  if (timeframe) query.timeframe = timeframe;

  let sortCriteria = { 'votes.upvotes': -1 };
  if (sort === 'newest') {
    sortCriteria = { createdAt: -1 };
  }

  const presets = await ConfigPreset.find(query).sort(sortCriteria);

  res.status(200).json({
    success: true,
    count: presets.length,
    data: presets
  });
});

/**
 * @desc    Create/Submit a custom indicator preset configuration layout
 * @route   POST /api/v1/presets
 * @access  Public
 */
export const submitPreset = asyncHandler(async (req, res) => {
  const {
    indicatorId,
    title,
    description,
    assetClass,
    symbol,
    timeframe,
    parameters,
    backtestResults,
    author
  } = req.body;

  if (!indicatorId || !title || !assetClass || !symbol || !timeframe || !parameters) {
    res.status(400);
    throw new Error('Please fill in vital preset requirements (indicatorId, title, assetClass, symbol, timeframe, parameters)');
  }

  const preset = await ConfigPreset.create({
    indicatorId,
    title,
    description,
    assetClass,
    symbol: symbol.toUpperCase(),
    timeframe,
    parameters,
    backtestResults,
    author: author || 'Retail Quant'
  });

  res.status(201).json({
    success: true,
    message: 'Indicator settings preset optimization profile submitted successfully',
    data: preset
  });
});

/**
 * @desc    Upvote/Downvote an indicator config preset
 * @route   PATCH /api/v1/presets/:id/vote
 * @access  Public
 */
export const votePreset = asyncHandler(async (req, res) => {
  const { id } = req.params;
  const { direction } = req.body; // 'up' or 'down'

  if (direction !== 'up' && direction !== 'down') {
    res.status(400);
    throw new Error("Invalid voting direction. Must be either 'up' or 'down'.");
  }

  const incField = direction === 'up' ? { 'votes.upvotes': 1 } : { 'votes.downvotes': 1 };
  const updatedPreset = await ConfigPreset.findByIdAndUpdate(id, { $inc: incField }, { new: true });

  if (!updatedPreset) {
    res.status(404);
    throw new Error('Settings preset profile not found');
  }

  res.status(200).json({
    success: true,
    data: updatedPreset
  });
});
