import asyncHandler from 'express-async-handler';
import Signal from '../models/Signal.js';
import Indicator from '../models/Indicator.js';

/**
 * @desc    Receive automation alerts from TradingView or EA scripts to publish live signals
 * @route   POST /api/v1/webhook/tradingview
 * @access  Public (Secured with dynamic passkey verification)
 */
export const handleTradingViewWebhook = asyncHandler(async (req, res) => {
  const {
    passkey,
    name,
    provider,
    indicatorSlug,
    asset,
    direction,
    entry,
    stopLoss,
    takeProfit1,
    takeProfit2,
    takeProfit3,
    timeframe,
    signalType,
    deliveryMethod
  } = req.body;

  // Enforce secure verification passkey to block spam alerts from invalid sources
  const requiredPasskey = process.env.ADMIN_SECRET || 'changeme123';
  if (passkey !== requiredPasskey) {
    res.status(403);
    throw new Error('Access denied. Invalid or missing webhook execution passkey.');
  }

  // Validate required fields explicitly
  if (!name || !provider || !asset || !direction || !entry || !stopLoss || !takeProfit1 || !timeframe) {
    res.status(400);
    throw new Error('Invalid alert payload. Missing vital trigger parameters (name, provider, asset, direction, entry, stopLoss, takeProfit1, timeframe).');
  }

  // Verify associated indicator inside database if slug is provided
  let indicatorRef = undefined;
  if (indicatorSlug) {
    const originalId = await Indicator.findOne({ slug: indicatorSlug });
    if (originalId) {
      indicatorRef = originalId._id;
    }
  }

  // Instantiate live Signal
  const signal = await Signal.create({
    name,
    provider,
    indicatorRef,
    asset: asset.toUpperCase(),
    direction: direction.charAt(0).toUpperCase() + direction.slice(1).toLowerCase(), // Normalize e.g. "buy" -> "Buy"
    entry: parseFloat(entry),
    stopLoss: parseFloat(stopLoss),
    takeProfit1: parseFloat(takeProfit1),
    takeProfit2: takeProfit2 ? parseFloat(takeProfit2) : undefined,
    takeProfit3: takeProfit3 ? parseFloat(takeProfit3) : undefined,
    timeframe,
    signalType: signalType || 'Technical',
    deliveryMethod: deliveryMethod || 'Telegram',
    isActive: true,
    price: 0
  });

  // Update associated indicator's metrics dynamically if connected
  if (indicatorRef) {
    await Indicator.findByIdAndUpdate(indicatorRef, {
      $inc: { trendingScore: 3, totalViews: 1 }
    });
  }

  res.status(201).json({
    success: true,
    message: 'TradingView webhook system processed successfully.',
    signalId: signal._id,
    timestamp: new Date()
  });
});
