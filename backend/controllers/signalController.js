import asyncHandler from 'express-async-handler';
import { Signal } from '../models/index.js';

/**
 * @desc    Get all active signal feeds with query filters (asset, direction, type, channel)
 * @route   GET /api/v1/signals
 * @access  Public
 */
export const getAll = asyncHandler(async (req, res) => {
  const { asset, direction, signalType, isActive, deliveryMethod } = req.query;
  const filter = {};

  if (asset) filter.asset = asset.toUpperCase();
  if (direction) filter.direction = direction;
  if (signalType) filter.signalType = signalType;
  if (deliveryMethod) filter.deliveryMethod = deliveryMethod;
  
  if (isActive === 'true') filter.isActive = true;
  else if (isActive === 'false') filter.isActive = false;

  const items = await Signal.find(filter)
    .populate('indicatorRef', 'name slug imageUrl rating')
    .sort({ createdAt: -1 });

  res.status(200).json({ success: true, data: items });
});

/**
 * @desc    Get single signal detail
 * @route   GET /api/v1/signals/:id
 * @access  Public
 */
export const getOne = asyncHandler(async (req, res) => {
  const signalObj = await Signal.findById(req.params.id).populate('indicatorRef', 'name slug');
  if (!signalObj) {
    return res.status(404).json({ success: false, error: 'Signal not found' });
  }

  res.status(200).json({ success: true, data: signalObj });
});

/**
 * @desc    Post/broadcast a new signal alert
 * @route   POST /api/v1/signals
 * @access  Public
 */
export const create = asyncHandler(async (req, res) => {
  const newSignal = await Signal.create(req.body);
  res.status(201).json({ success: true, data: newSignal });
});
